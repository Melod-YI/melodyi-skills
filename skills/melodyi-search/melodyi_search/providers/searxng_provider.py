"""SearXNG 提供商实现

SearXNG 是自托管搜索引擎：
- 需要配置 host (如 http://localhost:8888)
- 支持 time_range 参数: day/week/month/year
- 域名过滤使用 site: 操作符（非原生）
- GET 请求到 {host}/search
- 返回 JSON 格式
"""

import time
from typing import List, Optional
from datetime import datetime

from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.infrastructure.http.http_client import HttpClient
from melodyi_search.providers.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)


class SearXNGProvider(BaseProvider):
    """SearXNG 提供商

    使用自托管 SearXNG 实例进行搜索。
    支持原生时间过滤，域名过滤通过 site: 操作符实现。

    API 文档: https://docs.searxng.org/dev/search_api.html
    """

    DEFAULT_MAX_RESULTS = 10

    def __init__(
        self,
        host: str,
        timeout_ms: int = 10000,
        max_results: int = 10,
        api_key: Optional[str] = None,
    ):
        """初始化 SearXNG 提供商

        Args:
            host: SearXNG 实例地址 (如 http://localhost:8888)
            timeout_ms: 请求超时时间（毫秒）
            max_results: 最大返回结果数
            api_key: API 密钥（可选，部分实例需要）
        """
        self.host = host.rstrip("/")
        self.timeout_ms = timeout_ms
        self.max_results = max_results
        self.api_key = api_key

    @property
    def name(self) -> str:
        """提供商标识符"""
        return "searxng"

    def supports_time_filter(self) -> bool:
        """是否支持原生时间过滤

        SearXNG 原生支持 time_range 参数。
        """
        return True

    def supports_domain_filter(self) -> bool:
        """是否支持原生域名过滤

        SearXNG 不支持原生域名过滤参数，
        需要通过 site: 操作符在查询中实现。
        """
        return False

    def get_max_results_limit(self) -> int:
        """最大结果数限制"""
        return self.max_results

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        """执行搜索（同步版本）

        Args:
            request: 搜索请求

        Returns:
            搜索结果
        """
        start_time = time.time()

        # 构建请求参数
        params = self._build_request_params(request)

        # 构建请求 URL
        url = f"{self.host}/search"

        try:
            # 构建请求头
            headers = {
                "Accept": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            with HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers=headers,
            ) as client:
                response = client.get(url, params=params)

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

                # 截断到用户指定的 max_results
                results = results[:request.max_results]

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
            SearXNG API 请求参数
        """
        # 基础参数
        params = {
            "q": request.query,
            "format": "json",
            "pageno": 1,
        }

        # 添加结果数量限制
        # SearXNG 使用 engines 参数控制引擎，results_count 不是标准参数
        # 但我们可以通过 engines 参数指定搜索引擎
        params["engines"] = "google,bing,duckduckgo"

        # 添加时间范围参数
        if request.time_range and request.time_range.range_type:
            # SearXNG 支持: day, week, month, year
            params["time_range"] = request.time_range.range_type

        # 添加语言参数
        if request.language:
            params["language"] = request.language

        return params

    def _parse_response(self, response: dict) -> List[SearchResultItem]:
        """解析 API 响应

        Args:
            response: API 响应数据

        Returns:
            搜索结果列表
        """
        results: List[SearchResultItem] = []

        # SearXNG 返回格式: {"results": [...], "number_of_results": N}
        raw_results = response.get("results", [])
        if not raw_results:
            return results

        count = 0
        for item in raw_results:
            # 限制结果数量
            if count >= self.max_results:
                break

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
                # SearXNG 可能不返回发布日期

                # 提取原始数据中的额外信息
                provider_extra = None
                extra_keys = ["engine", "engines", "positions"]
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
                count += 1
            except Exception:
                # 跳过解析失败的项
                continue

        return results