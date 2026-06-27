"""Tavily Extract Provider 端到端测试

使用真实 API 进行验证。需要 TAVILY_API_KEY 环境变量。
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from melodyi_web.providers.fetch.tavily_extract_provider import TavilyExtractProvider
from melodyi_web.providers.fetch.base_fetch_provider import ProviderFetchRequest


@pytest.fixture
def tavily_api_key():
    """获取 Tavily API Key"""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        pytest.skip("TAVILY_API_KEY 环境变量未设置")
    return api_key


class TestTavilyExtractProvider:
    """Tavily Extract Provider 端到端测试"""

    def test_provider_name(self):
        """测试供应商名称"""
        provider = TavilyExtractProvider(api_key="dummy")
        assert provider.name == "tavily-extract"

    def test_supports_js_render(self):
        """测试 JS 渲染支持"""
        provider = TavilyExtractProvider(api_key="dummy")
        assert provider.supports_js_render() is True

    def test_output_format(self):
        """测试输出格式"""
        provider = TavilyExtractProvider(api_key="dummy")
        assert provider.get_output_format() == "raw"

    def test_fetch_example_com(self, tavily_api_key):
        """测试抓取 example.com（真实 API）—— example.com 为占位页，Tavily 侧稳定提取失败

        回归保护：results 为空时，provider 应把 failed_results 里的真实失败原因透出到 error，
        而不是返回笼统的"无提取结果"且 error 为 None。
        """
        provider = TavilyExtractProvider(
            api_key=tavily_api_key,
            timeout_ms=30000
        )
        request = ProviderFetchRequest(url="https://example.com")
        result = provider.fetch(request)

        assert result.provider == "tavily-extract"
        assert result.url == "https://example.com"
        # example.com 在 Tavily 侧提取失败：应返回非空 error（携带真实原因），content 为空
        assert result.error is not None
        assert result.content == ""
        assert result.response_time_ms > 0

    def test_fetch_wikipedia(self, tavily_api_key):
        """测试抓取维基百科（真实 API）"""
        provider = TavilyExtractProvider(
            api_key=tavily_api_key,
            timeout_ms=30000
        )
        request = ProviderFetchRequest(url="https://en.wikipedia.org/wiki/Main_Page")
        result = provider.fetch(request)

        assert result.error is None
        assert len(result.content) > 0

    def test_fetch_without_api_key(self):
        """测试缺少 API Key"""
        provider = TavilyExtractProvider(api_key="")
        request = ProviderFetchRequest(url="https://example.com")
        result = provider.fetch(request)

        # 应该返回错误
        assert result.error is not None


class TestTavilyExtractProviderFailedResults:
    """results 为空、failed_results 非空时的错误透出测试（不依赖真实 API）"""

    def _make_provider_with_client(self, response_payload, status_code=200):
        """构造 provider 与 mock HttpClient，client.post 返回给定响应体。"""
        provider = TavilyExtractProvider(api_key="dummy-key")
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = response_payload
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        return provider, mock_client

    def test_failed_results_error_surfaced(self):
        """results 为空时应把 failed_results 的真实错误透出到 error。"""
        payload = {
            "results": [],
            "failed_results": [
                {"url": "https://example.com", "error": "Error fetching content"}
            ],
        }
        provider, mock_client = self._make_provider_with_client(payload)
        with patch(
            "melodyi_web.providers.fetch.tavily_extract_provider.HttpClient",
            return_value=mock_client,
        ):
            result = provider.fetch(ProviderFetchRequest(url="https://example.com"))

        assert result.error is not None
        assert "Error fetching content" in result.error
        assert result.content == ""

    def test_failed_results_picks_matching_url(self):
        """多个 failed_results 时应优先取与请求 url 匹配的那条错误。"""
        payload = {
            "results": [],
            "failed_results": [
                {"url": "https://other.com", "error": "other error"},
                {"url": "https://example.com", "error": "Error fetching content"},
            ],
        }
        provider, mock_client = self._make_provider_with_client(payload)
        with patch(
            "melodyi_web.providers.fetch.tavily_extract_provider.HttpClient",
            return_value=mock_client,
        ):
            result = provider.fetch(ProviderFetchRequest(url="https://example.com"))

        assert "Error fetching content" in result.error
        assert "other error" not in result.error

    def test_empty_results_without_failed_results(self):
        """results 与 failed_results 均为空时退回笼统的"无提取结果"。"""
        payload = {"results": [], "failed_results": []}
        provider, mock_client = self._make_provider_with_client(payload)
        with patch(
            "melodyi_web.providers.fetch.tavily_extract_provider.HttpClient",
            return_value=mock_client,
        ):
            result = provider.fetch(ProviderFetchRequest(url="https://example.com"))

        assert result.error == "无提取结果"