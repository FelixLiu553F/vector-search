from adapters_vector.embedding.embedding_adapter import RemoteEmbeddingAdapter
from adapters_vector.openai.openai_adapter import OpenaiAdapter
from typing import Type

from adapters_vector.vector_adapter_interface import VectorAdapterInterface


class VectorFactory:
    ADAPTER_CLASSES = {
        "openai": OpenaiAdapter,
        "embedding": RemoteEmbeddingAdapter,
    }

    @classmethod
    def create_adapter(cls, adapter_type="openai") -> Type[VectorAdapterInterface]:
        adapter_class = cls.ADAPTER_CLASSES.get(adapter_type, OpenaiAdapter)
        return adapter_class()
