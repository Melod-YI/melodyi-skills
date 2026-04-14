"""Exa 提供商实现

Exa 是一个神经网络搜索引擎，专为 AI 应用设计，支持：
- 原生时间过滤 (startPublishedDate: ISO 8601 格式)
- 原生域名过滤 (includeDomains/excludeDomains)
- 搜索类型 (type: neural/keyword/auto)
"""

import time
from typing import List, Optional
from datetime import datetime, timedelta

from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.infrastructure.http.http_client import HttpClient
from melodyi_search.providers.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)


class ExaProvider(BaseProvider):
    """Exa 提供商

    使用 Exa Search API 进行神经网络搜索。
    支持原生时间过滤和域名过滤。

    API 文档: https://docs.exa.ai/
    """

    DEFAULT_API_URL = "https://api.exa.ai/search"
    DEFAULT_TYPE = "auto"  # neural, keyword, auto

    def __init__(
        self,
        api_key: str,
        api_url: Optional[str] = None,
        timeout_ms: int = 30000,  # 神经网络搜索较慢
        search_type: str = "auto",
    ):
        """初始化 Exa 提供商

        Args:
            api_key: Exa API 密钥
            api_url: API 地址，默认为官方地址
            timeout_ms: 请求超时时间（毫秒），默认 30 秒
            search_type: 搜索类型，neural/keyword/auto
        """
        self.api_key = api_key
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout_ms = timeout_ms
        self.default_type = search_type

    @property
    def name(self) -> str:
        """提供商标识符"""
        return "exa"

    def supports_time_filter(self) -> bool:
        """是否支持原生时间过滤

        Exa 原生支持 startPublishedDate 参数。
        """
        return True

    def supports_domain_filter(self) -> bool:
        """是否支持原生域名过滤

        Exa 原生支持 includeDomains 和 excludeDomains 参数。
        """
        return True

    def get_max_results_limit(self) -> int:
        """最大结果数限制

        Exa 默认最大返回 10 个结果。
        """
        return 10

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
                    "x-api-key": self.api_key,
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

    def _build_start_date(self, time_range: Optional[TimeRange]) -> Optional[str]:
        """根据时间范围构建起始日期字符串

        Args:
            time_range: 时间范围

        Returns:
            ISO 8601 格式的日期字符串，或 None
        """
        if time_range is None or time_range.range_type is None:
            # 如果有精确的起始日期，直接使用
            if time_range and time_range.start_date:
                return time_range.start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            return None

        now = datetime.utcnow()

        # 根据时间范围类型计算起始日期
        delta_map = {
            "day": timedelta(days=1),
            "week": timedelta(weeks=1),
            "month": timedelta(days=30),
            "year": timedelta(days=365),
        }

        delta = delta_map.get(time_range.range_type)
        if delta is None:
            return None

        start_date = now - delta
        return start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _build_request_params(self, request: ProviderSearchRequest) -> dict:
        """构建请求参数

        Args:
            request: 搜索请求

        Returns:
            Exa API 请求参数
        """
        params = {
            "query": request.query,
            "numResults": min(request.max_results, self.get_max_results_limit()),
            "type": self.default_type,
            "contents": {"text": True},
        }

        # 添加时间范围参数
        start_date = self._build_start_date(request.time_range)
        if start_date:
            params["startPublishedDate"] = start_date

        # 添加域名过滤参数
        if request.include_domains:
            params["includeDomains"] = request.include_domains

        if request.exclude_domains:
            params["excludeDomains"] = request.exclude_domains

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
                text = item.get("text", "")  # Exa 使用 text 而非 content

                # 跳过无效项
                if not title or not url:
                    continue

                # 解析发布日期
                published_date = None
                if item.get("publishedDate"):
                    try:
                        date_str = item["publishedDate"]
                        # 尝试解析 ISO 格式日期
                        if "T" in date_str:
                            published_date = datetime.fromisoformat(
                                date_str.replace("Z", "+00:00")
                            )
                        else:
                            # Exa 可能返回 YYYY-MM-DD 格式
                            published_date = datetime.fromisoformat(date_str)
                    except Exception:
                        pass

                # 提取原始数据中的额外信息
                provider_extra = None
                extra_keys = ["score", "author", "id"]
                extra_data = {k: item[k] for k in extra_keys if k in item}
                if extra_data:
                    provider_extra = extra_data

                results.append(
                    SearchResultItem(
                        title=title,
                        url=url,
                        description=text,
                        published_date=published_date,
                        source_domain="",  # 让 model 自动从 URL 提取
                        provider_extra=provider_extra,
                    )
                )
            except Exception:
                # 跳过解析失败的项
                continue

        return results