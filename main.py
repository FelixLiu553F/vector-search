import json
import threading
from os import environ
from dotenv import load_dotenv
from redis import StrictRedis
from sanic import Request, Sanic, response
from sanic.log import logger

from adapters_db.db_factory import DbFactory

load_dotenv()

REDIS_HOST = environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = environ.get("REDIS_PASSWORD")
REDIS_QUEUE_NAME = environ.get("REDIS_QUEUE_NAME", "IMEAN_TESTING:VECTOR_SEARCH_QUEUE")

SOLAR_APP_VERSION = environ.get("SOLAR_APP_VERSION", "dev")

DB_NAME = environ.get("DB_NAME")


redis = StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    charset="utf-8",
    decode_responses=True,
)

vectorDb = DbFactory.create_adapter(DB_NAME)


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
                vectorDb.upsert(
                    msg["id"],
                    msg["title"],
                    msg.get("description", ""),
                    msg.get("scenarios", ""),
                    msg.get("channelId", ""),
                )

        else:
            logger.info("No message in queue")


app = Sanic("imean-vector-search")


@app.get("/")
async def health():
    return response.text("version: " + SOLAR_APP_VERSION)


@app.post("/api/upsert")
async def upsert(request: Request):
    logger.info("Upserting...", request.json)
    data = request.json
    redis.rpush(REDIS_QUEUE_NAME, json.dumps(data))
    return response.text("OK")


@app.post("/api/delete")
async def delete(request: Request):
    logger.info("Deleting...", request.json)
    id = request.json["id"]
    vectorDb.delete(id)
    return response.text("OK")


@app.post("/api/search")
async def search(request: Request):
    logger.info("Searching...", request.json)
    content = request.json["content"]
    subscribedChannelIds = request.json.get("subscribedChannelIds", None)  # [id1, id2]
    result = vectorDb.search(content, subscribedChannelIds)
    logger.info("Search result", result)
    return response.json(result)


if __name__ == "__main__":
    print("Starting background task")
    task = threading.Thread(target=subscribe_recording, name="RecordingQueueConsumer")
    task.start()
    app.run(host="0.0.0.0")
