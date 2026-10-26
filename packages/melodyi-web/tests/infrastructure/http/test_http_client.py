"""HTTP 客户端测试"""

from unittest.mock import patch

import pytest
from melodyi_web.infrastructure.http.http_client import HttpClient


class TestHttpClient:
    """HttpClient 测试类"""

    def test_create_client(self):
        """测试创建客户端"""
        client = HttpClient(timeout_ms=10000)
        assert client.timeout_ms == 10000

    def test_create_client_with_headers(self):
        """测试创建带 headers 的客户端"""
        client = HttpClient(
            timeout_ms=5000,
            default_headers={"Authorization": "Bearer test"}
        )
        assert client.default_headers["Authorization"] == "Bearer test"

    def test_context_manager(self):
        """测试上下文管理器"""
        with HttpClient(timeout_ms=5000) as client:
            assert client is not None

    def test_close_client(self):
        """测试关闭客户端"""
        client = HttpClient(timeout_ms=5000)
        client.close()

    def test_default_verify_ssl(self):
        """测试默认校验 SSL"""
        client = HttpClient(timeout_ms=5000)
        assert client.verify_ssl is True

    def test_explicit_verify_ssl_true(self):
        """测试显式开启 SSL 校验"""
        client = HttpClient(timeout_ms=5000, verify_ssl=True)
        assert client.verify_ssl is True

    def test_explicit_verify_ssl_false(self):
        """测试显式关闭 SSL 校验"""
        client = HttpClient(timeout_ms=5000, verify_ssl=False)
        assert client.verify_ssl is False

    def test_set_default_verify_ssl(self):
        """测试类级默认 SSL 开关覆盖：未显式传参时继承类级默认值

        回归保护：CLI 加载配置后调用 set_default_verify_ssl，
        后续各 provider 实例化的 HttpClient 必须继承该全局设置。
        """
        original = HttpClient._default_verify_ssl
        try:
            HttpClient.set_default_verify_ssl(False)
            client = HttpClient(timeout_ms=5000)
            assert client.verify_ssl is False
            # 显式传参优先于类级默认
            client_explicit = HttpClient(timeout_ms=5000, verify_ssl=True)
            assert client_explicit.verify_ssl is True
        finally:
            HttpClient.set_default_verify_ssl(original)


class TestHttpClientProxy:
    """HttpClient 代理配置测试"""

    def test_default_proxy_is_none(self):
        """测试默认不配置代理（走 httpx 默认行为）"""
        client = HttpClient(timeout_ms=5000)
        assert client.proxy is None

    def test_explicit_proxy(self):
        """测试显式传入代理地址"""
        client = HttpClient(timeout_ms=5000, proxy="http://127.0.0.1:7890")
        assert client.proxy == "http://127.0.0.1:7890"

    def test_set_default_proxy(self):
        """测试类级默认代理覆盖：未显式传参时继承类级默认值

        回归保护：CLI 加载配置后调用 set_default_proxy，
        后续各 provider 实例化的 HttpClient 必须继承该全局设置。
        """
        original = HttpClient._default_proxy
        try:
            HttpClient.set_default_proxy("http://10.0.0.1:8080")
            client = HttpClient(timeout_ms=5000)
            assert client.proxy == "http://10.0.0.1:8080"
            # 显式传参优先于类级默认
            client_explicit = HttpClient(timeout_ms=5000, proxy="http://127.0.0.1:7890")
            assert client_explicit.proxy == "http://127.0.0.1:7890"
        finally:
            HttpClient.set_default_proxy(original)

    def test_get_client_passes_proxy_to_httpx(self):
        """测试 _get_client 把代理地址传给 httpx.Client

        回归保护：配置了代理时 httpx.Client 构造必须带 proxy 参数。
        """
        with patch("melodyi_web.infrastructure.http.http_client.httpx.Client") as mock_client:
            client = HttpClient(timeout_ms=5000, verify_ssl=True, proxy="http://127.0.0.1:7890")
            client._get_client()
            mock_client.assert_called_once()
            kwargs = mock_client.call_args.kwargs
            assert kwargs["proxy"] == "http://127.0.0.1:7890"
            assert kwargs["verify"] is True

    def test_get_client_without_proxy_passes_none(self):
        """测试未配置代理时 httpx.Client 收到 proxy=None（等价于不传）"""
        with patch("melodyi_web.infrastructure.http.http_client.httpx.Client") as mock_client:
            client = HttpClient(timeout_ms=5000)
            client._get_client()
            kwargs = mock_client.call_args.kwargs
            assert kwargs["proxy"] is None