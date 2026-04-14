"""领域模型"""

from melodyi_search.domain.models.search_request import TimeRange, UnifiedSearchRequest
from melodyi_search.domain.models.search_result import SearchResultItem, UnifiedSearchResult, SearchError
from melodyi_search.domain.models.error import ErrorType, ERROR_GUIDANCE, create_error_with_guidance

__all__ = [
    "TimeRange",
    "UnifiedSearchRequest",
    "SearchResultItem",
    "UnifiedSearchResult",
    "SearchError",
    "ErrorType",
    "ERROR_GUIDANCE",
    "create_error_with_guidance",
]