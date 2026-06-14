from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImageResult:
    image_url: str
    thumbnail_url: str
    source_url: str
    title: str
    width: int
    height: int


class ImageSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int) -> list[ImageResult]: ...
