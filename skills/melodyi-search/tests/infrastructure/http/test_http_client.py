"""HTTP 客户端测试"""

import pytest
from melodyi_search.infrastructure.http.http_client import HttpClient


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

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试上下文管理器"""
        async with HttpClient(timeout_ms=5000) as client:
            assert client is not None

    @pytest.mark.asyncio
    async def test_close_client(self):
        """测试关闭客户端"""
        client = HttpClient(timeout_ms=5000)
        await client.close()