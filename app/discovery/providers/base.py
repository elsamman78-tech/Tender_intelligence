from dataclasses import dataclass
from typing import Protocol

@dataclass
class SearchHit:
    url: str
    title: str = ''
    snippet: str = ''
    rank: int = 0

class SearchProvider(Protocol):
    name: str
    cost_class: str
    def available(self) -> bool: ...
    def search(self, query: str, limit: int = 10) -> list[SearchHit]: ...
