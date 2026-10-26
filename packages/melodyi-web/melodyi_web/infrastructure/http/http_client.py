"""HTTP 客户端抽象"""

import logging

import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class HttpClient:
    """同步 HTTP 客户端"""

    # 类级默认 SSL 校验开关：由 CLI 在加载配置后统一设置，
    # 这样各 provider 实例化 HttpClient 时无需显式传参即可继承全局配置。
    _default_verify_ssl: bool = True
    # 类级默认 HTTP 代理：同样由 CLI 在加载配置后统一设置，
    # None 表示未配置，走 httpx 默认行为（可读 HTTP_PROXY/HTTPS_PROXY 环境变量）。
    _default_proxy: Optional[str] = None

    @classmethod
    def set_default_verify_ssl(cls, verify: bool) -> None:
        """设置类级默认 SSL 校验开关

        Args:
            verify: True 校验 SSL（默认），False 关闭校验（兼容自签名证书）
        """
        cls._default_verify_ssl = verify

    @classmethod
    def set_default_proxy(cls, proxy: Optional[str]) -> None:
        """设置类级默认 HTTP 代理

        Args:
            proxy: 代理地址（如 http://127.0.0.1:7890），None 表示不使用代理配置
        """
        cls._default_proxy = proxy

    def __init__(
        self,
        timeout_ms: int = 10000,
        default_headers: Optional[Dict[str, str]] = None,
        verify_ssl: Optional[bool] = None,
        proxy: Optional[str] = None,
    ):
        """初始化客户端

        Args:
            timeout_ms: 超时时间（毫秒）
            default_headers: 默认请求头
            verify_ssl: 是否校验 SSL 证书；None 表示使用类级默认值（默认校验）
            proxy: HTTP 代理地址；None 表示使用类级默认值（默认不配置代理）
        """
        self.timeout_ms = timeout_ms
        self.default_headers = default_headers or {}
        # None 时回退到类级默认，便于全局配置覆盖
        self.verify_ssl = self._default_verify_ssl if verify_ssl is None else verify_ssl
        self.proxy = self._default_proxy if proxy is None else proxy
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """获取或创建同步客户端"""
        if self._client is None:
            if self.proxy:
                logger.info("HttpClient 启用代理: %s", self.proxy)
            else:
                logger.info("HttpClient 未配置代理，使用 httpx 默认行为")
            timeout = httpx.Timeout(self.timeout_ms / 1000)
            self._client = httpx.Client(
                timeout=timeout,
                headers=self.default_headers,
                verify=self.verify_ssl,
                proxy=self.proxy,
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