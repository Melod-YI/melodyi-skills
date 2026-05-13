"""Jina Reader Provider 实现

Jina Reader API:
- 端点: https://r.jina.ai/{url}
- 认证: 无需（可选 Bearer Token 提升速率）
- 输出: Markdown（默认）
"""

import time
from typing import Optional
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.fetch.base_fetch_provider import (
    BaseFetchProvider,
    ProviderFetchRequest,
    ProviderFetchResult,
)


class JinaReaderProvider(BaseFetchProvider):
    """Jina Reader 供应商

    使用 Jina Reader API 进行网页抓取。
    无需 API Key，直接通过 URL 前缀访问。

    API 文档: https://jina.ai/reader/
    """

    DEFAULT_API_URL = "https://r.jina.ai/"
    DEFAULT_TIMEOUT_MS = 15000

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ):
        """初始化 Jina Reader 供应商

        Args:
            api_key: API 密钥（可选，提升速率）
            api_url: API 地址，默认为官方地址
            timeout_ms: 请求超时时间（毫秒）
        """
        self.api_key = api_key
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout_ms = timeout_ms

    @property
    def name(self) -> str:
        """供应商标识符"""
        return "jina-reader"

    def supports_js_render(self) -> bool:
        """是否支持 JS 渲染

        Jina Reader 使用无头浏览器渲染动态内容。
        """
        return True

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

        # 构建 URL: https://r.jina.ai/{target_url}
        fetch_url = f"{self.api_url}{request.url}"

        try:
            headers = {"Accept": "text/plain"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

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

                # Jina Reader 直接返回 Markdown 文本
                content = response.text

                # 尝试从内容中提取标题
                # 格式1: "Title: xxx" (Jina Reader 格式)
                # 格式2: "# xxx" (Markdown 标题)
                title = None
                lines = content.split("\n")
                for line in lines[:10]:  # 检查前 10 行
                    line = line.strip()
                    # Jina Reader 格式: "Title: xxx"
                    if line.startswith("Title: ") and not title:
                        title = line[7:].strip()
                        break
                    # Markdown 格式: "# xxx"
                    if line.startswith("# ") and not title:
                        title = line[2:].strip()
                        break

                return ProviderFetchResult(
                    provider=self.name,
                    url=request.url,
                    title=title,
                    content=content,
                    response_time_ms=elapsed_ms,
                    metadata={"source": "jina-reader", "format": "markdown"},
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