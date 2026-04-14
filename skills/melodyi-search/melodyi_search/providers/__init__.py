"""提供商实现"""

from melodyi_search.providers.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
from melodyi_search.providers.minimax_cn_provider import MiniMaxCNProvider
from melodyi_search.providers.tavily_provider import TavilyProvider

__all__ = [
    "BaseProvider",
    "ProviderSearchRequest",
    "ProviderSearchResult",
    "MiniMaxCNProvider",
    "TavilyProvider",
]