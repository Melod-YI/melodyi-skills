"""Tavily 提供商实现

Tavily 是一个专为 AI 设计的搜索 API，支持：
- 原生时间过滤 (time_range: day/week/month/year)
- 原生域名过滤 (include_domains/exclude_domains)
- 搜索深度 (search_depth: basic/advanced)
"""

import time
from typing import List, Optional
from datetime import datetime

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)


class TavilyProvider(BaseProvider):
    """Tavily 提供商

    使用 Tavily Search API 进行网络搜索。
    支持原生时间过滤和域名过滤。

    API 文档: https://docs.tavily.com/
    """

    DEFAULT_API_URL = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str,
        api_url: Optional[str] = None,
        timeout_ms: int = 10000,
        search_depth: str = "basic",
    ):
        """初始化 Tavily 提供商

        Args:
            api_key: Tavily API 密钥
            api_url: API 地址，默认为官方地址
            timeout_ms: 请求超时时间（毫秒）
            search_depth: 搜索深度，basic 或 advanced
        """
        self.api_key = api_key
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout_ms = timeout_ms
        self.default_depth = search_depth

    @property
    def name(self) -> str:
        """提供商标识符"""
        return "tavily"

    def supports_time_filter(self) -> bool:
        """是否支持原生时间过滤

        Tavily 原生支持 time_range 参数。
        """
        return True

    def supports_domain_filter(self) -> bool:
        """是否支持原生域名过滤

        Tavily 原生支持 include_domains 和 exclude_domains 参数。
        """
        return True

    def get_max_results_limit(self) -> int:
        """最大结果数限制

        Tavily 默认最大返回 20 个结果。
        """
        return 20

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        """执行搜索（同步版本）

        Args:
            request: 搜索请求

        Returns:
            搜索结果
        """
        start_time = time.time()

        # 构建请求参数
        payload = self._build_request_params(request)

        try:
            with HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers={
                    "Content-Type": "application/json",
                },
            ) as client:
                response = client.post(self.api_url, json=payload)

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

    def _build_request_params(self, request: ProviderSearchRequest) -> dict:
        """构建请求参数

        Args:
            request: 搜索请求

        Returns:
            Tavily API 请求参数
        """
        params = {
            "api_key": self.api_key,
            "query": request.query,
            "search_depth": self.default_depth,
            "max_results": min(request.max_results, self.get_max_results_limit()),
        }

        # 添加时间范围参数
        if request.time_range and request.time_range.range_type:
            params["time_range"] = request.time_range.range_type

        # 添加域名过滤参数
        if request.include_domains:
            params["include_domains"] = request.include_domains

        if request.exclude_domains:
            params["exclude_domains"] = request.exclude_domains

        return params

    def _parse_response(self, response: dict) -> List[SearchResultItem]:
        """解析 API 响应

        Args:
            response: API 响应数据

        Returns:
            搜索结果列表
        """
        results: List[SearchResultItem] = []

        raw_results = response.get("results", [])
        if not raw_results:
            return results

        for item in raw_results:
            try:
                # 提取基本信息
                title = item.get("title", "")
                url = item.get("url", "")
                content = item.get("content", "")

                # 跳过无效项
                if not title or not url:
                    continue

                # 解析发布日期
                published_date = None
                if item.get("published_date"):
                    try:
                        date_str = item["published_date"]
                        # 尝试解析 ISO 格式日期
                        if "T" in date_str:
                            published_date = datetime.fromisoformat(
                                date_str.replace("Z", "+00:00")
                            )
                        else:
                            published_date = datetime.fromisoformat(date_str)
                    except Exception:
                        pass

                # 提取原始数据中的额外信息
                provider_extra = None
                extra_keys = ["score", "raw_content"]
                extra_data = {k: item[k] for k in extra_keys if k in item}
                if extra_data:
                    provider_extra = extra_data

                results.append(
                    SearchResultItem(
                        title=title,
                        url=url,
                        description=content,
                        published_date=published_date,
                        source_domain="",  # 让 model 自动从 URL 提取
                        provider_extra=provider_extra,
                    )
                )
            except Exception:
                # 跳过解析失败的项
                continue

        return results