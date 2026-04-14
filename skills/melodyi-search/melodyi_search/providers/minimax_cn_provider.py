"""MiniMax-CN 提供商实现（中国大陆版）"""

import re
import time
from typing import List, Optional
from urllib.parse import urlparse

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

    使用 MiniMax 对话 API 模拟搜索功能。
    不支持原生时间过滤和域名过滤，通过以下方式实现：
    - 时间过滤：在查询中注入中文时间关键词
    - 域名过滤：检索后对结果进行后过滤
    """

    DEFAULT_API_HOST = "https://api.minimaxi.com"
    DEFAULT_MODEL = "abab6.5s-chat"

    def __init__(
        self,
        api_key: str,
        api_host: Optional[str] = None,
        timeout_ms: int = 10000,
        max_results: int = 10,
        model: Optional[str] = None,
    ):
        """初始化 MiniMax-CN 提供商

        Args:
            api_key: MiniMax API 密钥
            api_host: API 地址，默认为中国大陆地址
            timeout_ms: 请求超时时间（毫秒）
            max_results: 最大返回结果数
            model: 使用的模型名称
        """
        self.api_key = api_key
        self.api_host = api_host or self.DEFAULT_API_HOST
        self.timeout_ms = timeout_ms
        self.max_results = max_results
        self.model = model or self.DEFAULT_MODEL

    @property
    def name(self) -> str:
        """提供商标识符"""
        return "minimax-cn"

    def supports_time_filter(self) -> bool:
        """是否支持原生时间过滤

        MiniMax 不支持原生时间过滤，通过注入时间关键词实现。
        """
        return False

    def supports_domain_filter(self) -> bool:
        """是否支持原生域名过滤

        MiniMax 不支持原生域名过滤，通过后过滤实现。
        """
        return False

    def get_max_results_limit(self) -> int:
        """最大结果数限制"""
        return 10

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
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": f"请帮我搜索以下内容并提供相关网页链接：{query}"}
            ],
        }

        try:
            with HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            ) as client:
                response = client.post(
                    f"{self.api_host}/v1/chat/completions", json=payload
                )

                elapsed_ms = int((time.time() - start_time) * 1000)

                if response.status_code != 200:
                    error_msg = f"API 请求失败: {response.status_code}"
                    try:
                        error_data = response.json()
                        if "error" in error_data:
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

        由于 MiniMax 不支持原生时间过滤，通过在查询中添加中文时间关键词
        来引导模型返回更符合时间范围的结果。

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

        Args:
            response: API 响应数据
            include_domains: 包含域名列表
            exclude_domains: 排除域名列表

        Returns:
            搜索结果列表
        """
        results: List[SearchResultItem] = []

        # 提取响应内容
        content = self._extract_content(response)
        if not content:
            return results

        # 从内容中解析 URL 和标题
        items = self._extract_search_items(content)

        # 应用域名过滤
        for item in items:
            if self._passes_domain_filter(
                item.url, include_domains, exclude_domains
            ):
                results.append(item)

            # 限制结果数量
            if len(results) >= self.max_results:
                break

        return results

    def _extract_content(self, response: dict) -> str:
        """从 API 响应中提取内容

        Args:
            response: API 响应数据

        Returns:
            提取的文本内容
        """
        try:
            choices = response.get("choices", [])
            if not choices:
                return ""

            # MiniMax 响应格式
            choice = choices[0]

            # 尝试标准 OpenAI 格式
            if "message" in choice:
                return choice["message"].get("content", "")

            # 尝试 MiniMax 特殊格式
            if "messages" in choice:
                messages = choice["messages"]
                for msg in messages:
                    if msg.get("role") == "assistant":
                        return msg.get("content", "")

            return ""
        except Exception:
            return ""

    def _extract_search_items(self, content: str) -> List[SearchResultItem]:
        """从文本内容中提取搜索结果项

        支持多种格式：
        - Markdown 链接: [标题](URL)
        - 纯文本 URL: https://example.com
        - 带描述的 URL: 标题: https://example.com

        Args:
            content: 文本内容

        Returns:
            搜索结果列表
        """
        results: List[SearchResultItem] = []

        # 提取 Markdown 链接: [标题](URL)
        md_pattern = r'\[([^\]]+)\]\((https?://[^)]+)\)'
        md_matches = re.findall(md_pattern, content)

        for title, url in md_matches:
            results.append(
                SearchResultItem(
                    title=title.strip(),
                    url=url.strip(),
                    description="",
                )
            )

        # 提取纯文本 URL（排除已被 Markdown 格式匹配的）
        url_pattern = r'(?<!\()(https?://[^\s\)\]<>"]+)'
        url_matches = re.findall(url_pattern, content)

        existing_urls = {item.url for item in results}

        for url in url_matches:
            url = url.strip()
            if url not in existing_urls:
                # 尝试从 URL 提取简单标题
                parsed = urlparse(url)
                domain = parsed.netloc
                results.append(
                    SearchResultItem(
                        title=f"来自 {domain}",
                        url=url,
                        description="",
                    )
                )

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