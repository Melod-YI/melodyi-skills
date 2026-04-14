"""错误类型与 Agent 指导"""

from enum import Enum
from melodyi_search.domain.models.search_result import SearchError


class ErrorType(str, Enum):
    """错误类型枚举"""

    API_KEY_INVALID = "API_KEY_INVALID"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    INVALID_REQUEST = "INVALID_REQUEST"
    DOMAIN_FILTER_UNSUPPORTED = "DOMAIN_FILTER_UNSUPPORTED"
    TIME_FILTER_UNSUPPORTED = "TIME_FILTER_UNSUPPORTED"
    REGION_MISMATCH = "REGION_MISMATCH"


ERROR_GUIDANCE: dict = {
    ErrorType.API_KEY_INVALID: "此提供商的 API 密钥无效或缺失。操作：检查您的配置，确保 API 密钥设置正确。",

    ErrorType.RATE_LIMITED: "请求被此提供商限流。操作：请等待后重试，或系统将自动切换到另一个提供商。",

    ErrorType.QUOTA_EXCEEDED: "此提供商的 API 配额已耗尽。操作：系统将切换到另一个提供商。考虑升级此提供商的计划。",

    ErrorType.NETWORK_ERROR: "网络连接错误。操作：请检查网络连接后重试。",

    ErrorType.TIMEOUT: "请求超时。操作：系统将使用更长的超时时间重试，或切换提供商。",

    ErrorType.INVALID_REQUEST: "请求参数无效。操作：请检查请求参数是否符合要求。",

    ErrorType.DOMAIN_FILTER_UNSUPPORTED: "此提供商不支持原生域名过滤。操作：适配器将在查询中使用搜索操作符（site:）或后过滤结果。",

    ErrorType.TIME_FILTER_UNSUPPORTED: "此提供商不支持时间过滤。操作：适配器将在查询中注入时间关键词（如'最新'、'今天'）。",

    ErrorType.REGION_MISMATCH: "API 密钥与主机区域不匹配。操作：中国大陆密钥使用 api.minimaxi.com，全球密钥使用 api.minimax.io。",
}


def create_error_with_guidance(
    error_type: ErrorType,
    original_message: str = ""
) -> SearchError:
    """创建带预设指导的搜索错误"""
    guidance = ERROR_GUIDANCE.get(error_type, "未知错误，请检查日志")
    return SearchError(
        error_type=error_type.value,
        original_message=original_message,
        guidance=guidance
    )