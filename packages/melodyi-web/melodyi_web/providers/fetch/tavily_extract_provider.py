"""Tavily Extract Provider 实现

Tavily Extract API:
- 端点: https://api.tavily.com/extract
- 认证: API Key (tvly-xxx)
- 输出: 结构化文本
"""

import time
from typing import Optional
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.fetch.base_fetch_provider import (
    BaseFetchProvider,
    ProviderFetchRequest,
    ProviderFetchResult,
)


class TavilyExtractProvider(BaseFetchProvider):
    """Tavily Extract 供应商

    使用 Tavily Extract API 进行网页内容提取。
    需要 API Key，复用 search 的 TAVILY_API_KEY。

    API 文档: https://docs.tavily.com/api-reference/extract
    """

    DEFAULT_API_URL = "https://api.tavily.com/extract"
    DEFAULT_TIMEOUT_MS = 15000

    def __init__(
        self,
        api_key: str,
        api_url: Optional[str] = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        extract_depth: str = "basic",
    ):
        """初始化 Tavily Extract 供应商

        Args:
            api_key: Tavily API 密钥
            api_url: API 地址，默认为官方地址
            timeout_ms: 请求超时时间（毫秒）
            extract_depth: 提取深度，basic 或 advanced
        """
        self.api_key = api_key
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout_ms = timeout_ms
        self.extract_depth = extract_depth

    @property
    def name(self) -> str:
        """供应商标识符"""
        return "tavily-extract"

    def supports_js_render(self) -> bool:
        """是否支持 JS 渲染

        Tavily Extract 支持 JS 渲染。
        """
        return True

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
            "api_key": self.api_key,
            "urls": [request.url],
            "extract_depth": self.extract_depth,
        }

        try:
            with HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers={"Content-Type": "application/json"},
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
                        error="无提取结果",
                    )

                # 获取第一个结果
                first_result = results[0]
                content = first_result.get("raw_content", "")
                if not content:
                    content = first_result.get("extracted_content", "")

                title = None
                # 尝试从内容中提取标题
                lines = content.split("\n")
                for line in lines[:5]:
                    line = line.strip()
                    if line and len(line) < 100 and not title:
                        # 第一行非空短文本可能是标题
                        title = line
                        break

                return ProviderFetchResult(
                    provider=self.name,
                    url=request.url,
                    title=title,
                    content=content,
                    response_time_ms=elapsed_ms,
                    metadata={
                        "source": "tavily-extract",
                        "format": "raw",
                        "extract_depth": self.extract_depth,
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