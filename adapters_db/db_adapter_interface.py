from abc import ABC, abstractmethod
from typing import TypedDict, List


class Metadata(TypedDict):
    channelId: str
    description: str
    scenarios: str
    title: str


class DbSearchResult(TypedDict):
    id: int
    score: int
    metadata: Metadata


class DbAdapterInterface(ABC):
    @abstractmethod
    def delete(self, id: str = "") -> bool:
        pass

    @abstractmethod
    def upsert(
        self,
        id: str = "",
        title: str = "",
        description: str = "",
        scenarios: str = "",
        channelId: str = "",
    ) -> bool:
        pass

    @abstractmethod
    def search(self, content: str, subscribedChannelIds: []) -> List[DbSearchResult]:
        pass
