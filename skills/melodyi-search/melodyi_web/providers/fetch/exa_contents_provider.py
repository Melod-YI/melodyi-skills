"""Exa Contents Provider 实现

Exa Contents API:
- 端点: https://api.exa.ai/contents
- 认证: API Key (x-api-key header)
- 输出: 文本
"""

import time
from typing import Optional
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.fetch.base_fetch_provider import (
    BaseFetchProvider,
    ProviderFetchRequest,
    ProviderFetchResult,
)


class ExaContentsProvider(BaseFetchProvider):
    """Exa Contents 供应商

    使用 Exa Contents API 进行网页内容获取。
    需要 API Key，复用 search 的 EXA_API_KEY。

    API 文档: https://docs.exa.ai/api-reference/contents
    """

    DEFAULT_API_URL = "https://api.exa.ai/contents"
    DEFAULT_TIMEOUT_MS = 30000  # Exa API 较慢

    def __init__(
        self,
        api_key: str,
        api_url: Optional[str] = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ):
        """初始化 Exa Contents 供应商

        Args:
            api_key: Exa API 密钥
            api_url: API 地址，默认为官方地址
            timeout_ms: 请求超时时间（毫秒）
        """
        self.api_key = api_key
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout_ms = timeout_ms

    @property
    def name(self) -> str:
        """供应商标识符"""
        return "exa-contents"

    def supports_js_render(self) -> bool:
        """是否支持 JS 渲染

        Exa Contents 不明确支持 JS 渲染。
        """
        return False

    def get_output_format(self) -> str:
        """输出格式"""
        return "raw"

    def fetch(self, request: ProviderFetchRequest) -> ProviderFetchResult:
        """执行抓取"""
        start_time = time.time()

        if not self.api_key:
            return ProviderFetchResult(
                provider=self.name,
                url=request.url,
                content="",
                response_time_ms=0,
                error="缺少 API Key",
            )

        # 构建请求参数
        payload = {
            "ids": [request.url],
            "text": True,
        }

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
                    return ProviderFetchResult(
                        provider=self.name,
                        url=request.url,
                        content="",
                        response_time_ms=elapsed_ms,
                        error=error_msg,
                    )

                response_data = response.json()
                results = response_data.get("results", [])

                if not results:
                    return ProviderFetchResult(
                        provider=self.name,
                        url=request.url,
                        content="",
                        response_time_ms=elapsed_ms,
                        error="无内容结果",
                    )

                # 获取第一个结果
                first_result = results[0]
                content = first_result.get("text", "")
                title = first_result.get("title", "")

                return ProviderFetchResult(
                    provider=self.name,
                    url=request.url,
                    title=title if title else None,
                    content=content,
                    response_time_ms=elapsed_ms,
                    metadata={
                        "source": "exa-contents",
                        "format": "raw",
                    },
                    raw_response=response_data,
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