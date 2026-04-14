"""HTTP 客户端抽象"""

import httpx
from typing import Optional, Dict, Any


class HttpClient:
    """异步 HTTP 客户端"""

    def __init__(
        self,
        timeout_ms: int = 10000,
        default_headers: Optional[Dict[str, str]] = None
    ):
        """初始化客户端"""
        self.timeout_ms = timeout_ms
        self.default_headers = default_headers or {}
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建异步客户端"""
        if self._client is None:
            timeout = httpx.Timeout(self.timeout_ms / 1000)
            self._client = httpx.AsyncClient(
                timeout=timeout,
                headers=self.default_headers
            )
        return self._client

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """GET 请求"""
        client = await self._get_client()
        merged_headers = {**self.default_headers, **(headers or {})}
        return await client.get(url, params=params, headers=merged_headers)

    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """POST 请求"""
        client = await self._get_client()
        merged_headers = {**self.default_headers, **(headers or {})}
        return await client.post(url, json=json, data=data, headers=merged_headers)

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()