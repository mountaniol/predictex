"""
Mock providers for new search source types
These are placeholder implementations that can be replaced with real APIs later
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
from .search_providers import SearchProvider
from .search_models import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class StatisticsProvider(SearchProvider):
    """Mock provider for statistical databases"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "statistics"
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Mock search returning statistical data"""
        logger.info(f"📊 [STATISTICS] Mock search for: {query.text}")
        
        # Mock results - in production, this would call real statistics APIs
        results = [
            SearchResult(
                title=f"Industry Statistics: {query.text}",
                content=f"Statistical analysis shows that industry average for similar metrics is 15-20% annual growth. "
                       f"Market data indicates median performance of 72% efficiency in this sector. "
                       f"Based on aggregated data from 500+ companies in similar markets.",
                url="https://statistics.example.com/industry-report",
                source="statistics",
                score=0.9,
                timestamp=datetime.now()
            ),
            SearchResult(
                title=f"Regional Market Data",
                content=f"Regional statistics for the specified area show: "
                       f"Average business failure rate: 8% annually. "
                       f"Growth rate for tech sector: 12% YoY. "
                       f"Employment trends: +5% quarterly.",
                url="https://statistics.example.com/regional",
                source="statistics",
                score=0.85,
                timestamp=datetime.now()
            )
        ]
        
        return results[:query.max_results]
    
    async def is_available(self) -> bool:
        """Check if provider is available"""
        return True
    
    def get_supported_query_types(self) -> List[str]:
        """Get supported query types"""
        return ["factual", "statistical", "quantitative"]


class IndustryReportsProvider(SearchProvider):
    """Mock provider for industry reports and market research"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "industry_reports"
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Mock search returning industry reports"""
        logger.info(f"📈 [INDUSTRY_REPORTS] Mock search for: {query.text}")
        
        results = [
            SearchResult(
                title=f"Industry Report 2024: {query.text}",
                content=f"Latest industry analysis reveals key trends: Digital transformation accelerating, "
                       f"with 68% of companies investing in AI/ML solutions. "
                       f"Market consolidation expected to continue through 2025. "
                       f"Regulatory changes impacting compliance costs by average 12%.",
                url="https://industryreports.example.com/2024-analysis",
                source="industry_reports",
                score=0.95,
                timestamp=datetime.now()
            ),
            SearchResult(
                title="Competitive Landscape Analysis",
                content=f"Market competition analysis shows: "
                       f"Top 5 players control 45% market share. "
                       f"New entrants increasing by 20% annually. "
                       f"Customer acquisition costs rising 8% YoY.",
                url="https://industryreports.example.com/competition",
                source="industry_reports",
                score=0.88,
                timestamp=datetime.now()
            )
        ]
        
        return results[:query.max_results]
    
    async def is_available(self) -> bool:
        return True
    
    def get_supported_query_types(self) -> List[str]:
        return ["industry", "market", "trends", "analysis"]


class GovernmentDataProvider(SearchProvider):
    """Mock provider for government data and regulatory information"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "government_data"
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Mock search returning government data"""
        logger.info(f"🏛️ [GOVERNMENT_DATA] Mock search for: {query.text}")
        
        results = [
            SearchResult(
                title=f"Regulatory Compliance Requirements",
                content=f"Government regulations for this sector include: "
                       f"Annual reporting requirements under Section 404. "
                       f"Data privacy compliance (GDPR/CCPA applicable). "
                       f"Industry-specific licensing requirements. "
                       f"Tax obligations: Corporate rate 21%, state varies 4-9%.",
                url="https://gov.example.com/regulations",
                source="government_data",
                score=0.92,
                timestamp=datetime.now()
            ),
            SearchResult(
                title="Government Economic Data",
                content=f"Official economic indicators: "
                       f"GDP growth: 2.8% (latest quarter). "
                       f"Unemployment rate: 3.7%. "
                       f"Business formation rate: +12% YoY. "
                       f"Small business confidence index: 98.4.",
                url="https://gov.example.com/economic-data",
                source="government_data",
                score=0.87,
                timestamp=datetime.now()
            )
        ]
        
        return results[:query.max_results]
    
    async def is_available(self) -> bool:
        return True
    
    def get_supported_query_types(self) -> List[str]:
        return ["regulatory", "compliance", "government", "legal"]


class AcademicProvider(SearchProvider):
    """Mock provider for academic sources and research papers"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "academic"
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Mock search returning academic research"""
        logger.info(f"🎓 [ACADEMIC] Mock search for: {query.text}")
        
        results = [
            SearchResult(
                title=f"Research Study: Business Risk Factors Analysis",
                content=f"Academic research (Smith et al., 2024) indicates that "
                       f"primary risk factors include market volatility (32%), "
                       f"operational inefficiencies (28%), and regulatory changes (21%). "
                       f"Study based on analysis of 1,000+ business cases.",
                url="https://academic.example.com/research-2024",
                source="academic",
                score=0.91,
                timestamp=datetime.now()
            ),
            SearchResult(
                title="Meta-Analysis: Industry Performance Metrics",
                content=f"Comprehensive meta-analysis shows: "
                       f"Average ROI across sectors: 12-15%. "
                       f"Failure predictors: Cash flow issues (45%), "
                       f"market timing (30%), management issues (25%).",
                url="https://academic.example.com/meta-analysis",
                source="academic",
                score=0.86,
                timestamp=datetime.now()
            )
        ]
        
        return results[:query.max_results]
    
    async def is_available(self) -> bool:
        return True
    
    def get_supported_query_types(self) -> List[str]:
        return ["research", "academic", "study", "analysis"]


class LocalBusinessProvider(SearchProvider):
    """Mock provider for local business directories and regional data"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "local_business"
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Mock search returning local business data"""
        logger.info(f"📍 [LOCAL_BUSINESS] Mock search for: {query.text}")
        
        results = [
            SearchResult(
                title=f"Local Business Environment Analysis",
                content=f"Local market conditions show: "
                       f"Business density: 45 per 1,000 residents. "
                       f"Average business lifespan: 8.5 years. "
                       f"Local competition index: Moderate (6.2/10). "
                       f"Regional economic health: Strong (B+ rating).",
                url="https://localbusiness.example.com/analysis",
                source="local_business",
                score=0.88,
                timestamp=datetime.now()
            ),
            SearchResult(
                title="Regional Business Directory Insights",
                content=f"Directory analysis reveals: "
                       f"Total registered businesses: 12,450 in region. "
                       f"New business registrations: +8% this year. "
                       f"Primary sectors: Tech (22%), Services (35%), Retail (18%).",
                url="https://localbusiness.example.com/directory",
                source="local_business",
                score=0.82,
                timestamp=datetime.now()
            )
        ]
        
        return results[:query.max_results]
    
    async def is_available(self) -> bool:
        return True
    
    def get_supported_query_types(self) -> List[str]:
        return ["local", "regional", "business_directory", "geographic"]


# Provider registry for easy access
MOCK_PROVIDERS = {
    'statistics': StatisticsProvider,
    'industry_reports': IndustryReportsProvider,
    'government_data': GovernmentDataProvider,
    'academic': AcademicProvider,
    'local_business': LocalBusinessProvider
}


def get_mock_provider(provider_type: str, config: Dict[str, Any]) -> SearchProvider:
    """
    Get a mock provider instance by type
    
    Args:
        provider_type: Type of provider
        config: Provider configuration
        
    Returns:
        SearchProvider instance
    """
    provider_class = MOCK_PROVIDERS.get(provider_type)
    if provider_class:
        return provider_class(config)
    else:
        raise ValueError(f"Unknown mock provider type: {provider_type}")