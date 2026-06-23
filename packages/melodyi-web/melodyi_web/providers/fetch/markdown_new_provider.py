"""Markdown.new Provider 实现

Markdown.new API:
- 端点: https://markdown.new/{url}
- 认证: 无需
- 输出: Markdown
"""

import time
from typing import Optional
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.fetch.base_fetch_provider import (
    BaseFetchProvider,
    ProviderFetchRequest,
    ProviderFetchResult,
)


class MarkdownNewProvider(BaseFetchProvider):
    """Markdown.new 供应商

    使用 Markdown.new API 进行网页抓取。
    无需 API Key，直接通过 URL 前缀访问。

    API 文档: https://markdown.new/
    """

    DEFAULT_API_URL = "https://markdown.new/"
    DEFAULT_TIMEOUT_MS = 15000

    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ):
        """初始化 Markdown.new 供应商

        Args:
            api_url: API 地址，默认为官方地址
            timeout_ms: 请求超时时间（毫秒）
        """
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout_ms = timeout_ms

    @property
    def name(self) -> str:
        """供应商标识符"""
        return "markdown-new"

    def supports_js_render(self) -> bool:
        """是否支持 JS 渲染

        Markdown.new 不明确支持 JS 渲染。
        """
        return False

    def get_output_format(self) -> str:
        """输出格式"""
        return "markdown"

    def fetch(self, request: ProviderFetchRequest) -> ProviderFetchResult:
        """执行抓取

        Args:
            request: 抓取请求

        Returns:
            抓取结果
        """
        start_time = time.time()

        # 构建 URL: https://markdown.new/{target_url}
        fetch_url = f"{self.api_url}{request.url}"

        try:
            # 添加浏览器 User-Agent 以避免被拒绝
            headers = {
                "Accept": "text/markdown, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            with HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers=headers,
            ) as client:
                response = client.get(fetch_url)

                elapsed_ms = int((time.time() - start_time) * 1000)

                if response.status_code != 200:
                    error_msg = f"API 请求失败: {response.status_code}"
                    return ProviderFetchResult(
                        provider=self.name,
                        url=request.url,
                        content="",
                        response_time_ms=elapsed_ms,
                        error=error_msg,
                    )

                # Markdown.new 直接返回 Markdown 文本
                content = response.text

                # 尝试从内容中提取标题
                title = None
                lines = content.split("\n")
                for line in lines[:5]:
                    line = line.strip()
                    if line.startswith("# ") and not title:
                        title = line[2:].strip()
                        break

                return ProviderFetchResult(
                    provider=self.name,
                    url=request.url,
                    title=title,
                    content=content,
                    response_time_ms=elapsed_ms,
                    metadata={"source": "markdown-new", "format": "markdown"},
                )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return ProviderFetchResult(
                provider=self.name,
                url=request.url,
                content="",
                response_time_ms=elapsed_ms,
                error=str(e),
            )