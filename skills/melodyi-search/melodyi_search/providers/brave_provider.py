"""Brave 提供商实现

Brave Search API 是一个注重隐私的搜索引擎 API。
支持：
- 原生时间过滤 (freshness: pd/pw/pm/py)
- 不支持域名过滤（site: 操作符不可靠，不实现）

API 文档: https://brave.com/search/api/
"""

import time
from typing import List, Optional

from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.infrastructure.http.http_client import HttpClient
from melodyi_search.providers.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)


class BraveProvider(BaseProvider):
    """Brave 提供商

    使用 Brave Search API 进行网络搜索。
    支持原生时间过滤，不支持域名过滤。
    """

    DEFAULT_API_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(
        self,
        api_key: str,
        api_url: Optional[str] = None,
        timeout_ms: int = 10000,
    ):
        """初始化 Brave 提供商

        Args:
            api_key: Brave API 密钥
            api_url: API 地址，默认为官方地址
            timeout_ms: 请求超时时间（毫秒）
        """
        self.api_key = api_key
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout_ms = timeout_ms

    @property
    def name(self) -> str:
        """提供商标识符"""
        return "brave"

    def supports_time_filter(self) -> bool:
        """是否支持原生时间过滤

        Brave 原生支持 freshness 参数。
        """
        return True

    def supports_domain_filter(self) -> bool:
        """是否支持原生域名过滤

        Brave 不支持域名过滤。
        site: 操作符不可靠，搜索引擎不保证遵守，因此不实现。
        """
        return False

    def get_max_results_limit(self) -> int:
        """最大结果数限制

        Brave 默认最大返回 20 个结果。
        """
        return 20

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        """执行搜索（同步版本）

        注意：include_domains 和 exclude_domains 参数被忽略，
        因为 Brave 不支持可靠的域名过滤。

        Args:
            request: 搜索请求

        Returns:
            搜索结果
        """
        start_time = time.time()

        # Brave 不支持域名过滤，直接使用原始查询
        query = request.query

        # 构建请求参数
        params = self._build_request_params(query, request)

        try:
            with HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.api_key,
                },
            ) as client:
                response = client.get(self.api_url, params=params)

                elapsed_ms = int((time.time() - start_time) * 1000)

                if response.status_code != 200:
                    error_msg = f"API 请求失败: {response.status_code}"
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error_msg = f"{error_msg} - {error_data['error']}"
                        elif "message" in error_data:
                            error_msg = f"{error_msg} - {error_data['message']}"
                    except Exception:
                        pass
                    return ProviderSearchResult(
                        provider=self.name,
                        results=[],
                        response_time_ms=elapsed_ms,
                        error=error_msg,
                    )

                response_data = response.json()
                results = self._parse_response(response_data)

                return ProviderSearchResult(
                    provider=self.name,
                    results=results,
                    response_time_ms=elapsed_ms,
                    raw_response=response_data,
                )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return ProviderSearchResult(
                provider=self.name,
                results=[],
                response_time_ms=elapsed_ms,
                error=str(e),
            )

    def _build_request_params(
        self, query: str, request: ProviderSearchRequest
    ) -> dict:
        """构建请求参数

        Args:
            query: 搜索查询
            request: 原始搜索请求

        Returns:
            Brave API 请求参数
        """
        params = {
            "q": query,
            "count": min(request.max_results, self.get_max_results_limit()),
        }

        # 添加时间范围参数
        if request.time_range and request.time_range.range_type:
            freshness = self._build_freshness(request.time_range.range_type)
            if freshness:
                params["freshness"] = freshness

        return params

    def _build_freshness(self, range_type: str) -> Optional[str]:
        """将 TimeRange.range_type 映射到 Brave freshness 参数

        Args:
            range_type: 时间范围类型 (day/week/month/year)

        Returns:
            Brave freshness 参数 (pd/pw/pm/py)
        """
        freshness_mapping = {
            "day": "pd",
            "week": "pw",
            "month": "pm",
            "year": "py",
        }
        return freshness_mapping.get(range_type)

    def _parse_response(self, response: dict) -> List[SearchResultItem]:
        """解析 API 响应

        Args:
            response: API 响应数据

        Returns:
            搜索结果列表
        """
        results: List[SearchResultItem] = []

        # Brave 响应格式: {"web": {"results": [...}}
        web_data = response.get("web", {})
        raw_results = web_data.get("results", [])

        if not raw_results:
            return results

        for item in raw_results:
            try:
                # 提取基本信息
                title = item.get("title", "")
                url = item.get("url", "")
                description = item.get("description", "")

                # 跳过无效项
                if not title or not url:
                    continue

                # 提取原始数据中的额外信息
                provider_extra = None
                extra_keys = ["type", "subtype", "meta_url", "thumbnail"]
                extra_data = {k: item[k] for k in extra_keys if k in item}
                if extra_data:
                    provider_extra = extra_data

                results.append(
                    SearchResultItem(
                        title=title,
                        url=url,
                        description=description,
                        source_domain="",  # 让 model 自动从 URL 提取
                        provider_extra=provider_extra,
                    )
                )
            except Exception:
                # 跳过解析失败的项
                continue

        return results