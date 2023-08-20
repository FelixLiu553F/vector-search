from adapters_db.db_adapter_interface import DbAdapterInterface, DbSearchResult
from adapters_vector.vector_factory import VectorFactory
from qdrant_client import models, QdrantClient
from os import environ
from dotenv import load_dotenv
from typing import List


load_dotenv()


class QdrantAdapter(DbAdapterInterface):
    QDRANT_ENDPOINT = environ.get("QDRANT_ENDPOINT")
    COLLECTION_NAME = environ.get("COLLECTION_NAME")
    VECTOR_NAME = environ.get("VECTOR_NAME")

    def __init__(self):
        self.qdrant = QdrantClient(QdrantAdapter.QDRANT_ENDPOINT)

        # 获取所有 collections
        collections = self.qdrant.get_collections()

        # 检查指定的 COLLECTION_NAME 是否已存在
        collection_exists = any(
            QdrantAdapter.COLLECTION_NAME == col.name
            for item in collections
            for col in item[1]
        )

        # 如果集合不存在，则创建集合
        if not collection_exists:
            self.qdrant.recreate_collection(
                collection_name=QdrantAdapter.COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=1024,  # Vector size is defined by used model
                    distance=models.Distance.COSINE,
                ),
            )

        self.vector = VectorFactory.create_adapter(QdrantAdapter.VECTOR_NAME)

    def delete(self, id: str = "") -> bool:
        self.qdrant.delete(collection_name=QdrantAdapter.COLLECTION_NAME, ids=[id])
        return True

    def upsert(
        self,
        id: str = "",
        title: str = "",
        description: str = "",
        scenarios: str = "",
        channelId: str = "",
    ) -> bool:
        xq = self.vector.generate_weighted_vector(title, description, scenarios)

        self.qdrant.upload_records(
            collection_name=QdrantAdapter.COLLECTION_NAME,
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
        return True

    def search(self, content: str, subscribedChannelIds: []) -> List[DbSearchResult]:
        xq = self.vector.convert_vector(content)

        hits = self.qdrant.search(
            collection_name=QdrantAdapter.COLLECTION_NAME,
            query_vector=xq,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="channelId", match=models.MatchAny(any=subscribedChannelIds)
                    ),
                ]
                if subscribedChannelIds
                else [],
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
