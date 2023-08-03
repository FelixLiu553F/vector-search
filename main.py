import json
import threading

from os import environ
from dotenv import load_dotenv
from redis import StrictRedis
from sanic import Request, Sanic, response
from sanic.log import logger
from qdrant_client import models, QdrantClient
from sentence_transformers import SentenceTransformer

load_dotenv()

REDIS_HOST = environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = environ.get("REDIS_PASSWORD")
REDIS_QUEUE_NAME = environ.get("REDIS_QUEUE_NAME", "IMEAN_TESTING:VECTOR_SEARCH_QUEUE")

PINECONE_API_KEY = environ.get("PINECONE_API_KEY")
PINECONE_ENV = environ.get("PINECONE_ENV")
SOLAR_APP_VERSION = environ.get("SOLAR_APP_VERSION", "dev")
QDRANT_ENDPOINT = environ.get("QDRANT_ENDPOINT")
COLLECTION_NAME = environ.get("COLLECTION_NAME")


encoder = SentenceTransformer("all-MiniLM-L6-v2")

redis = StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    charset="utf-8",
    decode_responses=True,
)

# 连接到 Qdrant 服务器
qdrant = QdrantClient(QDRANT_ENDPOINT)

if any(item.name == "test" for item in qdrant.get_collections()):
    # 创建 collection
    qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=encoder.get_sentence_embedding_dimension(),  # Vector size is defined by used model
            distance=models.Distance.COSINE,
        ),
    )


# 生成加权向量
def generate_weighted_vector(
    title: str = "",
    description: str = "",
    scenarios: str = "",
    scenarios_weight: float = 2.0,
):
    title_vector = openai.Embedding.create(input=title, engine=MODEL)["data"][0][
        "embedding"
    ]
    description_vector = openai.Embedding.create(input=description, engine=MODEL)[
        "data"
    ][0]["embedding"]

    scenarios_vector = openai.Embedding.create(input=scenarios, engine=MODEL)["data"][
        0
    ]["embedding"]

    # 将 scenarios_vector 加权
    weighted_scenarios_vector = [v * scenarios_weight for v in scenarios_vector]

    # 整合向量
    final_vector = [
        title_v + description_v + scenario_v
        for title_v, description_v, scenario_v in zip(
            title_vector, description_vector, weighted_scenarios_vector
        )
    ]

    return final_vector


# 将数据插入到 collection
def process_recording(
    id: str = "",
    title: str = "",
    description: str = "",
    scenarios: str = "",
    channelId: str = "",
):
    xq = generate_weighted_vector(title, description, scenarios)
    qdrant.upload_records(
        collection_name=COLLECTION_NAME,
        records=[
            models.Record(
                id=id,
                vector=xq,
                payload={
                    "id": id,
                    "title": title,
                    "description": description,
                    "scenarios": scenarios,
                    "channelId": channelId,
                },
            )
        ],
    )


def subscribe_recording():
    if redis.ping():
        logger.info("Starting background task")
    while True:
        item = redis.blpop(REDIS_QUEUE_NAME, 2)
        if item != None:
            (_, msg) = item
            if msg != None:
                print(msg)
                msg = json.loads(msg)
                process_recording(
                    msg["id"],
                    msg["title"],
                    msg.get("description", ""),
                    msg.get("scenarios", ""),
                    msg.get("channelId", ""),
                )
        else:
            print("no recording found")


app = Sanic("imean-vector-search")


@app.get("/")
async def health(request: Request):
    return response.text("version: " + SOLAR_APP_VERSION)


@app.post("/api/upsert")
async def upsert(request: Request):
    data = request.json
    redis.rpush(REDIS_QUEUE_NAME, json.dumps(data))
    return response.text("OK")


@app.post("/api/delete")
async def delete(request: Request):
    id = request.json["id"]
    qdrant.delete(collection_name=COLLECTION_NAME, ids=[id])
    return response.text("OK")


@app.post("/api/search")
async def search(request: Request):
    content = request.json["content"]
    subscribedChannelIds = request.json.get("subscribedChannelIds", None)  # [id1, id2]

    xq = openai.Embedding.create(input=content, engine=MODEL)["data"][0]["embedding"]

    hits = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=xq,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="channelId", match=models.MatchAny(any=subscribedChannelIds)
                ),
            ]
        ),
        limit=10,
    )

    result = [
        {
            "id": hit.payload["id"],
            "score": hit.score,
            "metadata": {
                "channelId": hit.payload.get("channelId", ""),
                "description": hit.payload.get("description", ""),
                "scenarios": hit.payload.get("scenarios", ""),
                "title": hit.payload.get("title", ""),
            },
        }
        for hit in hits
    ]

    return result


if __name__ == "__main__":
    print("Starting background task")
    task = threading.Thread(target=subscribe_recording, name="RecordingQueueConsumer")
    task.start()
    app.run(host="0.0.0.0")
