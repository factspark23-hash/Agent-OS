"""Abstract base classes for search backends and result types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum


class SearchProvider(str, Enum):
    """Available search providers."""
    GOOGLE = "google"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    AGENT_OS = "agent_os"
    HTTP = "http"


@dataclass
class SearchRequest:
    """A search request."""
    query: str
    max_results: int = 10
    provider: SearchProvider = SearchProvider.GOOGLE
    extract_content: bool = False
    timeout: float = 30.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResultItem:
    """A single search result."""
    title: str
    url: str
    snippet: str = ""
    content: str = ""
    relevance_score: float = 0.5
    source_type: str = "web"
    provider: str = ""
    rank: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class SearchBackend(ABC):
    """Abstract base class for search backends."""

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        """Execute a search query."""
        pass

    @abstractmethod
    async def extract_content(self, url: str) -> Optional[str]:
        """Extract content from a URL."""
        pass

    def is_available(self) -> bool:
        """Check if this backend is available and properly configured."""
        return True
