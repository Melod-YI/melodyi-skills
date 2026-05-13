"""Jina Reader Provider 端到端测试

使用真实 API 进行验证。
"""

import pytest
from melodyi_web.providers.fetch.jina_reader_provider import JinaReaderProvider
from melodyi_web.providers.fetch.base_fetch_provider import ProviderFetchRequest


class TestJinaReaderProvider:
    """Jina Reader Provider 端到端测试"""

    def test_provider_name(self):
        """测试供应商名称"""
        provider = JinaReaderProvider()
        assert provider.name == "jina-reader"

    def test_supports_js_render(self):
        """测试 JS 渲染支持"""
        provider = JinaReaderProvider()
        assert provider.supports_js_render() is True

    def test_output_format(self):
        """测试输出格式"""
        provider = JinaReaderProvider()
        assert provider.get_output_format() == "markdown"

    def test_fetch_example_com(self):
        """测试抓取 example.com（真实 API）"""
        provider = JinaReaderProvider(timeout_ms=30000)
        request = ProviderFetchRequest(url="https://example.com")
        result = provider.fetch(request)

        assert result.provider == "jina-reader"
        assert result.url == "https://example.com"
        assert result.error is None
        assert len(result.content) > 0
        assert "Example Domain" in result.content or "example" in result.content.lower()
        assert result.response_time_ms > 0

    def test_fetch_wikipedia(self):
        """测试抓取维基百科（真实 API）"""
        provider = JinaReaderProvider(timeout_ms=30000)
        request = ProviderFetchRequest(url="https://en.wikipedia.org/wiki/Main_Page")
        result = provider.fetch(request)

        assert result.error is None
        assert len(result.content) > 0
        assert result.title is not None

    def test_fetch_invalid_url(self):
        """测试无效 URL"""
        provider = JinaReaderProvider(timeout_ms=10000)
        request = ProviderFetchRequest(url="https://this-url-does-not-exist-12345.com")
        result = provider.fetch(request)

        # 应该返回错误
        assert result.error is not None