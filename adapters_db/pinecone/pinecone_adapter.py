from os import environ
from dotenv import load_dotenv
import pinecone
from typing import List

from adapters_db.db_adapter_interface import DbAdapterInterface, DbSearchResult
from adapters_vector.vector_factory import VectorFactory


load_dotenv()


class PineconeAdapter(DbAdapterInterface):
    PINECONE_API_KEY = environ.get("PINECONE_API_KEY")
    PINECONE_ENV = environ.get("PINECONE_ENV")
    COLLECTION_NAME = environ.get("COLLECTION_NAME")
    VECTOR_NAME = environ.get("VECTOR_NAME")

    def __init__(self):
        pinecone.init(
            api_key=PineconeAdapter.PINECONE_API_KEY,
            environment=PineconeAdapter.PINECONE_ENV,
        )
        if PineconeAdapter.COLLECTION_NAME not in pinecone.list_indexes():
            pinecone.create_index(
                PineconeAdapter.COLLECTION_NAME, dimension=1536, metric="cosine"
            )

        self.recordings_index = pinecone.Index(PineconeAdapter.COLLECTION_NAME)
        self.vector = VectorFactory.create_adapter(PineconeAdapter.VECTOR_NAME)

    def delete(self, id: str):
        self.recordings_index.delete(ids=id)

    def upsert(
        self,
        id: str = "",
        title: str = "",
        description: str = "",
        scenarios: str = "",
        channelId: str = "",
    ) -> bool:
        xq = self.vector.generate_weighted_vector(title, description, scenarios, 2.0)

        self.recordings_index.upsert(
            vectors=[
                {
                    "id": id,
                    "values": xq,
                    "metadata": {
                        "title": title,
                        "description": description,
                        "scenarios": scenarios,
                        "channelId": channelId,
                    },
                }
            ]
        )

        return True

    def search(self, content: str, subscribedChannelIds: []) -> List[DbSearchResult]:
        xq = self.vector.convert_vector(content)

        results = self.recordings_index.query(
            top_k=10,
            include_metadata=True,
            include_values=False,
            vector=xq,
            filter=(
                {"channelId": {"$in": subscribedChannelIds}}
                if subscribedChannelIds
                else None
            ),
        )
        return results.to_dict()["matches"]
