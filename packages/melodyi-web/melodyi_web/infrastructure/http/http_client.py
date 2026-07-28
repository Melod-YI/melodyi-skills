"""HTTP 客户端抽象"""

import httpx
from typing import Optional, Dict, Any


class HttpClient:
    """同步 HTTP 客户端"""

    # 类级默认 SSL 校验开关：由 CLI 在加载配置后统一设置，
    # 这样各 provider 实例化 HttpClient 时无需显式传参即可继承全局配置。
    _default_verify_ssl: bool = True

    @classmethod
    def set_default_verify_ssl(cls, verify: bool) -> None:
        """设置类级默认 SSL 校验开关

        Args:
            verify: True 校验 SSL（默认），False 关闭校验（兼容自签名证书）
        """
        cls._default_verify_ssl = verify

    def __init__(
        self,
        timeout_ms: int = 10000,
        default_headers: Optional[Dict[str, str]] = None,
        verify_ssl: Optional[bool] = None,
    ):
        """初始化客户端

        Args:
            timeout_ms: 超时时间（毫秒）
            default_headers: 默认请求头
            verify_ssl: 是否校验 SSL 证书；None 表示使用类级默认值（默认校验）
        """
        self.timeout_ms = timeout_ms
        self.default_headers = default_headers or {}
        # None 时回退到类级默认，便于全局配置覆盖
        self.verify_ssl = self._default_verify_ssl if verify_ssl is None else verify_ssl
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """获取或创建同步客户端"""
        if self._client is None:
            timeout = httpx.Timeout(self.timeout_ms / 1000)
            self._client = httpx.Client(
                timeout=timeout,
                headers=self.default_headers,
                verify=self.verify_ssl,
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