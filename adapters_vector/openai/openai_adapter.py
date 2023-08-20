import requests
from os import environ
from dotenv import load_dotenv
import openai
from sanic.log import logger

from adapters_vector.vector_adapter_interface import VectorAdapterInterface

load_dotenv()


class OpenaiAdapter(VectorAdapterInterface):
    DEFAULT_MODEL = environ.get("OPENAI_MODEL", "text-embedding-ada-002")

    def _handle_request(self, content: str):
        try:
            response = openai.Embedding.create(input=content, engine=self.DEFAULT_MODEL)
            response_data = response.get("data", [])
            if response_data:
                return response_data[0]["embedding"]
        except (requests.exceptions.RequestException, KeyError) as e:
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
