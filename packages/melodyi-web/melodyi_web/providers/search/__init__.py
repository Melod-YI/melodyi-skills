"""搜索提供商实现"""

from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
from melodyi_web.providers.search.minimax_cn_provider import MiniMaxCNProvider
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.providers.search.exa_provider import ExaProvider
from melodyi_web.providers.search.searxng_provider import SearXNGProvider
from melodyi_web.providers.search.firecrawl_provider import FirecrawlProvider

__all__ = [
    "BaseProvider",
    "ProviderSearchRequest",
    "ProviderSearchResult",
    "MiniMaxCNProvider",
    "TavilyProvider",
    "BraveProvider",
    "ExaProvider",
    "SearXNGProvider",
    "FirecrawlProvider",
]