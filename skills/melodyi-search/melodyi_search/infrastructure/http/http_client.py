"""HTTP 客户端抽象"""

import httpx
from typing import Optional, Dict, Any


class HttpClient:
    """同步 HTTP 客户端"""

    def __init__(
        self,
        timeout_ms: int = 10000,
        default_headers: Optional[Dict[str, str]] = None
    ):
        """初始化客户端

        Args:
            timeout_ms: 超时时间（毫秒）
            default_headers: 默认请求头
        """
        self.timeout_ms = timeout_ms
        self.default_headers = default_headers or {}
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """获取或创建同步客户端"""
        if self._client is None:
            timeout = httpx.Timeout(self.timeout_ms / 1000)
            self._client = httpx.Client(
                timeout=timeout,
                headers=self.default_headers
            )
        return self._client

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """GET 请求"""
        client = self._get_client()
        merged_headers = {**self.default_headers, **(headers or {})}
        return client.get(url, params=params, headers=merged_headers)

    def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """POST 请求"""
        client = self._get_client()
        merged_headers = {**self.default_headers, **(headers or {})}
        return client.post(url, json=json, data=data, headers=merged_headers)

    def close(self):
        """关闭客户端"""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()