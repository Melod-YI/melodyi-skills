"""Jina Reader Provider 实现

Jina Reader API:
- 端点: https://r.jina.ai/{url}
- 认证: 无需（可选 Bearer Token 提升速率）
- 输出: Markdown（默认）

支持的 extra_params:
- engine: browser/direct (渲染引擎，默认 browser)
- with_summary: true/false (生成摘要)
- with_links: true/false (保留链接)
- remove_selector: CSS selector (移除元素)
- include_selector: CSS selector (包含元素)
"""

import time
from typing import Optional, Dict
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
        extra_params: Optional[Dict] = None,
    ):
        """初始化 Jina Reader 供应商

        Args:
            api_key: API 密钥（可选，提升速率）
            api_url: API 地址，默认为官方地址
            timeout_ms: 请求超时时间（毫秒）
            extra_params: 额外参数配置
                - engine: browser/direct
                - with_summary: true/false
                - with_links: true/false
                - remove_selector: CSS selector
                - include_selector: CSS selector
        """
        self.api_key = api_key
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout_ms = timeout_ms
        self.extra_params = extra_params or {}

    @property
    def name(self) -> str:
        """供应商标识符"""
        return "jina"

    def supports_js_render(self) -> bool:
        """是否支持 JS 渲染

        Jina Reader 使用无头浏览器渲染动态内容。
        """
        # 根据 engine 参数判断
        engine = self.extra_params.get("engine", "browser")
        return engine == "browser"

    def get_output_format(self) -> str:
        """输出格式"""
        return "markdown"

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头部

        包括认证和 Jina 特定参数。
        """
        headers = {"Accept": "text/plain"}

        # 认证
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Jina 特定参数（通过 HTTP 头传递）
        engine = self.extra_params.get("engine")
        if engine:
            headers["X-Engine"] = engine

        with_summary = self.extra_params.get("with_summary")
        if with_summary:
            headers["X-With-Generated-Summary"] = "true"

        with_links = self.extra_params.get("with_links")
        if with_links:
            headers["X-With-Links"] = "true"

        remove_selector = self.extra_params.get("remove_selector")
        if remove_selector:
            headers["X-Remove-Selector"] = remove_selector

        include_selector = self.extra_params.get("include_selector")
        if include_selector:
            headers["X-Include-Selector"] = include_selector

        return headers

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
            headers = self._build_headers()

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

                # 构建元数据
                metadata = {
                    "source": "jina",
                    "format": "markdown",
                    "engine": self.extra_params.get("engine", "browser"),
                }
                if self.extra_params.get("with_summary"):
                    metadata["with_summary"] = True

                return ProviderFetchResult(
                    provider=self.name,
                    url=request.url,
                    title=title,
                    content=content,
                    response_time_ms=elapsed_ms,
                    metadata=metadata,
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