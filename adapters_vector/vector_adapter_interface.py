from abc import ABC, abstractmethod


class VectorAdapterInterface(ABC):
    @abstractmethod
    def convert_vector(self, content: str):
        pass

    @abstractmethod
    def generate_weighted_vector(
        self,
        title: str = "",
        description: str = "",
        scenarios: str = "",
        scenarios_weight: float = 2.0,
    ):
        pass
