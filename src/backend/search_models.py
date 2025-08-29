"""
Data models for web search system
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class SearchQuery:
    """Search query structure"""
    text: str
    query_type: Optional[str] = None
    max_results: int = 10
    language: str = "ru"
    filters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Search result"""
    title: str
    content: str
    url: str
    source: str  # "duckduckgo", "wikipedia", "rss"
    score: float = 0.0
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source": self.source,
            "score": self.score,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """Create from dictionary"""
        if data.get("timestamp"):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class SearchResponse:
    """Search system response"""
    query: SearchQuery
    results: List[SearchResult]
    total_results: int
    search_time: float
    cache_hit: bool = False
    sources_used: List[str] = field(default_factory=list)
    classification: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "query": {
                "text": self.query.text,
                "query_type": self.query.query_type,
                "max_results": self.query.max_results,
                "language": self.query.language
            },
            "results": [r.to_dict() for r in self.results],
            "total_results": self.total_results,
            "search_time": self.search_time,
            "cache_hit": self.cache_hit,
            "sources_used": self.sources_used,
            "classification": self.classification
        }