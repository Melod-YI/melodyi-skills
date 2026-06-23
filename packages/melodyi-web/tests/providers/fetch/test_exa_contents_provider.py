"""Exa Contents Provider 端到端测试

使用真实 API 进行验证。需要 EXA_API_KEY 环境变量。
"""

import os
import pytest
from melodyi_web.providers.fetch.exa_contents_provider import ExaContentsProvider
from melodyi_web.providers.fetch.base_fetch_provider import ProviderFetchRequest


@pytest.fixture
def exa_api_key():
    """获取 Exa API Key"""
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        pytest.skip("EXA_API_KEY 环境变量未设置")
    return api_key


class TestExaContentsProvider:
    """Exa Contents Provider 端到端测试"""

    def test_provider_name(self):
        """测试供应商名称"""
        provider = ExaContentsProvider(api_key="dummy")
        assert provider.name == "exa-contents"

    def test_supports_js_render(self):
        """测试 JS 渲染支持"""
        provider = ExaContentsProvider(api_key="dummy")
        # Exa Contents 不明确支持 JS 渲染
        assert provider.supports_js_render() is False

    def test_output_format(self):
        """测试输出格式"""
        provider = ExaContentsProvider(api_key="dummy")
        assert provider.get_output_format() == "raw"

    def test_fetch_example_com(self, exa_api_key):
        """测试抓取 example.com（真实 API）"""
        provider = ExaContentsProvider(
            api_key=exa_api_key,
            timeout_ms=30000
        )
        request = ProviderFetchRequest(url="https://example.com")
        result = provider.fetch(request)

        assert result.provider == "exa-contents"
        assert result.url == "https://example.com"
        assert result.error is None
        assert len(result.content) > 0
        assert result.response_time_ms > 0

    def test_fetch_wikipedia(self, exa_api_key):
        """测试抓取维基百科（真实 API）"""
        provider = ExaContentsProvider(
            api_key=exa_api_key,
            timeout_ms=30000
        )
        request = ProviderFetchRequest(url="https://en.wikipedia.org/wiki/Main_Page")
        result = provider.fetch(request)

        assert result.error is None
        assert len(result.content) > 0

    def test_fetch_without_api_key(self):
        """测试缺少 API Key"""
        provider = ExaContentsProvider(api_key="")
        request = ProviderFetchRequest(url="https://example.com")
        result = provider.fetch(request)

        # 应该返回错误
        assert result.error is not None