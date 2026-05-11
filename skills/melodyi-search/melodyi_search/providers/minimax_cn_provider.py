"""MiniMax-CN 提供商实现（中国大陆版）

使用 MiniMax Coding Plan Search API：
- URL: https://api.minimaxi.com/v1/coding_plan/search
- 方法: POST
- 请求体: {"q": query}
- 响应: {"organic": [...], "base_resp": {...}}
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


class MiniMaxCNProvider(BaseProvider):
    """MiniMax-CN 提供商（中国大陆版）

    使用 MiniMax Coding Plan Search API 进行网络搜索。
    该 API 返回类似搜索引擎的结果格式。

    特性：
    - 不支持原生时间过滤（需通过查询关键词实现）
    - 不支持原生域名过滤（需后过滤实现）
    - 最大结果数由 API 返回决定
    """

    DEFAULT_API_HOST = "https://api.minimaxi.com"
    SEARCH_ENDPOINT = "/v1/coding_plan/search"

    def __init__(
        self,
        api_key: str,
        api_host: Optional[str] = None,
        timeout_ms: int = 10000,
        max_results: int = 10,
    ):
        """初始化 MiniMax-CN 提供商

        Args:
            api_key: MiniMax API 密钥（Coding Plan Token）
            api_host: API 地址，默认为中国大陆地址
            timeout_ms: 请求超时时间（毫秒）
            max_results: 最大返回结果数（用于截断）
        """
        self.api_key = api_key
        self.api_host = api_host or self.DEFAULT_API_HOST
        self.timeout_ms = timeout_ms
        self.max_results = max_results

    @property
    def name(self) -> str:
        """提供商标识符"""
        return "minimax-cn"

    def supports_time_filter(self) -> bool:
        """是否支持原生时间过滤

        MiniMax Search API 不支持时间范围参数，
        需要在查询中添加时间关键词来实现。
        """
        return False

    def supports_domain_filter(self) -> bool:
        """是否支持原生域名过滤

        MiniMax Search API 不支持域名过滤参数，
        需要在结果返回后进行后过滤。
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

        # 处理查询（注入时间关键词）
        query = self._inject_time_keywords(request.query, request.time_range)

        # 构建请求
        payload = {"q": query}

        try:
            with HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            ) as client:
                url = f"{self.api_host}{self.SEARCH_ENDPOINT}"
                response = client.post(url, json=payload)

                elapsed_ms = int((time.time() - start_time) * 1000)

                if response.status_code != 200:
                    error_msg = f"API 请求失败: {response.status_code}"
                    try:
                        error_data = response.json()
                        if "base_resp" in error_data:
                            base_resp = error_data["base_resp"]
                            error_msg = f"{error_msg} - {base_resp.get('status_msg', '')}"
                        elif "error" in error_data:
                            error_msg = f"{error_msg} - {error_data['error']}"
                    except Exception:
                        pass
                    return ProviderSearchResult(
                        provider=self.name,
                        results=[],
                        response_time_ms=elapsed_ms,
                        error=error_msg,
                    )

                response_data = response.json()
                results = self._parse_response(
                    response_data,
                    request.include_domains,
                    request.exclude_domains,
                )

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

    def _inject_time_keywords(
        self, query: str, time_range: Optional[TimeRange]
    ) -> str:
        """在查询中注入时间关键词

        由于 MiniMax Search API 不支持原生时间过滤，
        通过在查询中添加中文时间关键词来引导搜索引擎。

        Args:
            query: 原始查询
            time_range: 时间范围

        Returns:
            注入时间关键词后的查询
        """
        if time_range is None or time_range.range_type is None:
            return query

        time_keywords = {
            "day": "今天 最新",
            "week": "本周 最新",
            "month": "本月 最新",
            "year": "今年 最新",
        }

        keyword = time_keywords.get(time_range.range_type)
        if keyword:
            return f"{query} {keyword}"

        return query

    def _parse_response(
        self,
        response: dict,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> List[SearchResultItem]:
        """解析 API 响应并应用域名过滤

        MiniMax Search API 返回格式：
        {
            "organic": [
                {
                    "title": "...",
                    "link": "...",
                    "snippet": "...",
                    "date": "..."
                }
            ],
            "base_resp": {
                "status_code": 0,
                "status_msg": "success"
            }
        }

        Args:
            response: API 响应数据
            include_domains: 包含域名列表
            exclude_domains: 排除域名列表

        Returns:
            搜索结果列表
        """
        results: List[SearchResultItem] = []

        # 检查 base_resp 状态
        base_resp = response.get("base_resp", {})
        status_code = base_resp.get("status_code", 0)
        if status_code != 0:
            # API 返回错误状态
            return results

        # 提取 organic 结果
        organic_results = response.get("organic", [])
        if not organic_results:
            return results

        for item in organic_results:
            try:
                url = item.get("link", "") or item.get("url", "")
                title = item.get("title", "")
                snippet = item.get("snippet", "") or item.get("content", "")
                date_str = item.get("date", "")

                if not url:
                    continue

                # 应用域名过滤
                if not self._passes_domain_filter(url, include_domains, exclude_domains):
                    continue

                # 解析发布日期（可选）
                published_date = None
                if date_str:
                    try:
                        # 尝试解析日期格式 "2026-04-01 16:21:30"
                        from datetime import datetime
                        published_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass

                result = SearchResultItem(
                    title=title,
                    url=url,
                    description=snippet,
                    published_date=published_date,
                    provider_extra=item,
                )
                results.append(result)

                # 限制结果数量
                if len(results) >= self.max_results:
                    break

            except Exception:
                continue

        return results

    def _passes_domain_filter(
        self,
        url: str,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> bool:
        """检查 URL 是否通过域名过滤

        Args:
            url: 要检查的 URL
            include_domains: 包含域名列表
            exclude_domains: 排除域名列表

        Returns:
            是否通过过滤
        """
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # 如果有包含域名列表，检查是否在其中
            if include_domains:
                domain_lower = [d.lower() for d in include_domains]
                if not any(d in domain for d in domain_lower):
                    return False

            # 如果有排除域名列表，检查是否不在其中
            if exclude_domains:
                domain_lower = [d.lower() for d in exclude_domains]
                if any(d in domain for d in domain_lower):
                    return False

            return True
        except Exception:
            return True