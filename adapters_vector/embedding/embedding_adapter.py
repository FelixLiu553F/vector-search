import requests
from os import environ
from dotenv import load_dotenv
from sanic.log import logger

from adapters_vector.vector_adapter_interface import VectorAdapterInterface

load_dotenv()


class RemoteEmbeddingAdapter(VectorAdapterInterface):
    EMBEDDING_URL = environ.get("EMBEDDING_URL")

    @staticmethod
    def _handle_request(content: str):
        try:
            response = requests.post(
                RemoteEmbeddingAdapter.EMBEDDING_URL, json={"text": content}
            )
            response.raise_for_status()
            return response.json().get("embedding", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error converting vector: {e}")
        return [0.0] * 1024

    def convert_vector(self, content: str):
        return self._handle_request(content)

    def generate_weighted_vector(
        self,
        title: str = "",
        description: str = "",
        scenarios: str = "",
        scenarios_weight: float = 2.0,
    ):
        title_vector = self._handle_request(title)
        description_vector = self._handle_request(description)
        scenarios_vector = self._handle_request(scenarios)

        weighted_scenarios_vector = [v * scenarios_weight for v in scenarios_vector]

        final_vector = [
            title_v + description_v + scenario_v
            for title_v, description_v, scenario_v in zip(
                title_vector, description_vector, weighted_scenarios_vector
            )
        ]

        return final_vector
