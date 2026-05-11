"""参数适配器

将 UnifiedSearchRequest 转换为 ProviderSearchRequest。
"""

from typing import Optional
from melodyi_web.domain.models.search_request import UnifiedSearchRequest
from melodyi_web.providers.search.base_provider import BaseProvider, ProviderSearchRequest


class ParameterAdapter:
    """参数适配器

    将统一搜索请求转换为提供商特定的搜索请求。
    主要职责：
    - 传递查询参数
    - 限制 max_results 不超过提供商限制
    - 传递时间范围和域名过滤参数
    """

    @staticmethod
    def adapt(unified: UnifiedSearchRequest, provider: BaseProvider) -> ProviderSearchRequest:
        """将统一请求转换为提供商请求

        Args:
            unified: 统一搜索请求
            provider: 目标提供商

        Returns:
            ProviderSearchRequest: 适配后的提供商请求
        """
        # 获取提供商的最大结果数限制
        max_limit = provider.get_max_results_limit()

        # 限制 max_results 不超过提供商限制
        effective_max_results = min(unified.max_results, max_limit)

        return ProviderSearchRequest(
            query=unified.query,
            max_results=effective_max_results,
            time_range=unified.time_range,
            include_domains=unified.include_domains,
            exclude_domains=unified.exclude_domains,
            language=unified.language,
            native_params=None,
            modified_query=None,
        )