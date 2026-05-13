"""领域模型"""

from melodyi_web.domain.models.search_request import TimeRange, UnifiedSearchRequest
from melodyi_web.domain.models.search_result import SearchResultItem, UnifiedSearchResult, SearchError
from melodyi_web.domain.models.error import ErrorType, ERROR_GUIDANCE, create_error_with_guidance
from melodyi_web.domain.models.provider_config import ProviderConfig, PROVIDER_NAMES
from melodyi_web.domain.models.fetch_request import FetchRequest

__all__ = [
    "TimeRange",
    "UnifiedSearchRequest",
    "SearchResultItem",
    "UnifiedSearchResult",
    "SearchError",
    "ErrorType",
    "ERROR_GUIDANCE",
    "create_error_with_guidance",
    "ProviderConfig",
    "PROVIDER_NAMES",
    "FetchRequest",
]