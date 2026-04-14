"""Firecrawl 提供商实现

Firecrawl 是搜索+抓取服务：
- 支持云服务 (api.firecrawl.dev) 和自托管
- api_key 必填
- host 可选（自托管地址）
- POST 请求到 {host}/v1/search
- 不支持时间过滤和域名过滤
- 返回格式包含 web、images、news 三种结果
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


class FirecrawlProvider(BaseProvider):
    """Firecrawl 提供商

    使用 Firecrawl Search API 进行网络搜索。
    不支持原生时间过滤和域名过滤。

    API 文档: https://docs.firecrawl.dev/
    """

    DEFAULT_API_URL = "https://api.firecrawl.dev/v1/search"
    DEFAULT_MAX_RESULTS = 10

    def __init__(
        self,
        api_key: str,
        api_url: Optional[str] = None,
        timeout_ms: int = 10000,
        max_results: int = 10,
    ):
        """初始化 Firecrawl 提供商

        Args:
            api_key: Firecrawl API 密钥（必填）
            api_url: API 地址，默认为官方云服务地址
                     自托管时设置为自托管地址
            timeout_ms: 请求超时时间（毫秒）
            max_results: 最大返回结果数
        """
        self.api_key = api_key
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout_ms = timeout_ms
        self.max_results = max_results

    @property
    def name(self) -> str:
        """提供商标识符"""
        return "firecrawl"

    def supports_time_filter(self) -> bool:
        """是否支持原生时间过滤

        Firecrawl 不支持原生时间过滤。
        """
        return False

    def supports_domain_filter(self) -> bool:
        """是否支持原生域名过滤

        Firecrawl 不支持原生域名过滤。
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
        payload = self._build_request_params(request)

        try:
            with HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
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
            Firecrawl API 请求参数
        """
        params = {
            "query": request.query,
            "limit": min(request.max_results, self.max_results),
        }

        return params

    def _parse_response(self, response: dict) -> List[SearchResultItem]:
        """解析 API 响应

        Firecrawl 返回格式:
        {
            "success": true,
            "data": {
                "web": [...],
                "images": [...],
                "news": [...]
            }
        }

        Args:
            response: API 响应数据

        Returns:
            搜索结果列表
        """
        results: List[SearchResultItem] = []

        # 检查响应是否成功
        if not response.get("success", False):
            return results

        data = response.get("data", {})
        if not data:
            return results

        # 解析 web 结果
        web_results = data.get("web", [])
        for item in web_results:
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
                extra_keys = ["position"]
                extra_data = {k: item[k] for k in extra_keys if k in item}
                if extra_data:
                    provider_extra = extra_data

                results.append(
                    SearchResultItem(
                        title=title,
                        url=url,
                        description=description,
                        published_date=None,
                        source_domain="",  # 让 model 自动从 URL 提取
                        provider_extra=provider_extra,
                    )
                )
            except Exception:
                # 跳过解析失败的项
                continue

        # 解析 news 结果（包含日期）
        news_results = data.get("news", [])
        for item in news_results:
            try:
                # 提取基本信息
                title = item.get("title", "")
                url = item.get("url", "")
                snippet = item.get("snippet", "")

                # 跳过无效项
                if not title or not url:
                    continue

                # 解析发布日期
                published_date = None
                date_str = item.get("date", "")
                if date_str:
                    try:
                        # 尝试解析 ISO 格式或其他常见格式
                        # Firecrawl news 结果的日期格式可能是多种形式
                        if "T" in date_str:
                            published_date = datetime.fromisoformat(
                                date_str.replace("Z", "+00:00")
                            )
                        else:
                            # 尝试解析 YYYY-MM-DD 格式
                            published_date = datetime.strptime(date_str, "%Y-%m-%d")
                    except Exception:
                        pass

                # 提取原始数据中的额外信息
                provider_extra = None
                extra_keys = ["position"]
                extra_data = {k: item[k] for k in extra_keys if k in item}
                if extra_data:
                    provider_extra = extra_data

                results.append(
                    SearchResultItem(
                        title=title,
                        url=url,
                        description=snippet,
                        published_date=published_date,
                        source_domain="",  # 让 model 自动从 URL 提取
                        provider_extra=provider_extra,
                    )
                )
            except Exception:
                # 跳过解析失败的项
                continue

        # 限制结果数量
        return results[:self.max_results]