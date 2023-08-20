from adapters_db.db_adapter_interface import DbAdapterInterface
from adapters_db.pinecone.pinecone_adapter import PineconeAdapter
from adapters_db.qdrant.qdrant_adapter import QdrantAdapter
from typing import Type


class DbFactory:
    ADAPTER_CLASSES = {
        "pinecone": PineconeAdapter,
        "qdrant": QdrantAdapter,
    }

    @classmethod
    def create_adapter(cls, adapter_type="pinecone") -> Type[DbAdapterInterface]:
        adapter_class = cls.ADAPTER_CLASSES.get(adapter_type, QdrantAdapter)
        return adapter_class()