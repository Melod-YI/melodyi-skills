"""Tavily 提供商单元测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.providers.tavily_provider import TavilyProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest


class TestTavilyProviderInit:
    """TavilyProvider 初始化测试"""

    def test_init_with_api_key(self):
        """测试使用 API key 初始化"""
        provider = TavilyProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.api_url == "https://api.tavily.com/search"
        assert provider.timeout_ms == 10000
        assert provider.default_depth == "basic"

    def test_init_with_custom_url(self):
        """测试自定义 API URL"""
        provider = TavilyProvider(
            api_key="test-key",
            api_url="https://custom.api.com/search"
        )
        assert provider.api_url == "https://custom.api.com/search"

    def test_init_with_custom_timeout(self):
        """测试自定义超时时间"""
        provider = TavilyProvider(api_key="test-key", timeout_ms=5000)
        assert provider.timeout_ms == 5000

    def test_init_with_custom_depth(self):
        """测试自定义搜索深度"""
        provider = TavilyProvider(api_key="test-key", search_depth="advanced")
        assert provider.default_depth == "advanced"


class TestTavilyProviderProperties:
    """TavilyProvider 属性测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = TavilyProvider(api_key="test")
        assert provider.name == "tavily"

    def test_supports_time_filter(self):
        """测试支持原生时间过滤"""
        provider = TavilyProvider(api_key="test")
        assert provider.supports_time_filter() is True

    def test_supports_domain_filter(self):
        """测试支持原生域名过滤"""
        provider = TavilyProvider(api_key="test")
        assert provider.supports_domain_filter() is True

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = TavilyProvider(api_key="test")
        assert provider.get_max_results_limit() == 20


class TestBuildRequestParams:
    """请求参数构建测试"""

    def test_build_request_params_basic(self):
        """测试基本请求参数构建"""
        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python教程")
        params = provider._build_request_params(request)

        assert params["api_key"] == "test-key"
        assert params["query"] == "Python教程"
        assert params["search_depth"] == "basic"
        assert params["max_results"] == 10

    def test_build_request_params_with_max_results(self):
        """测试自定义最大结果数"""
        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python", max_results=15)
        params = provider._build_request_params(request)

        assert params["max_results"] == 15

    def test_build_request_params_with_time_range_day(self):
        """测试时间范围参数（day）"""
        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="day")
        )
        params = provider._build_request_params(request)

        assert params["time_range"] == "day"

    def test_build_request_params_with_time_range_week(self):
        """测试时间范围参数（week）"""
        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="week")
        )
        params = provider._build_request_params(request)

        assert params["time_range"] == "week"

    def test_build_request_params_with_time_range_month(self):
        """测试时间范围参数（month）"""
        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="month")
        )
        params = provider._build_request_params(request)

        assert params["time_range"] == "month"

    def test_build_request_params_with_time_range_year(self):
        """测试时间范围参数（year）"""
        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="year")
        )
        params = provider._build_request_params(request)

        assert params["time_range"] == "year"

    def test_build_request_params_with_include_domains(self):
        """测试包含域名参数"""
        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            include_domains=["python.org", "github.com"]
        )
        params = provider._build_request_params(request)

        assert params["include_domains"] == ["python.org", "github.com"]

    def test_build_request_params_with_exclude_domains(self):
        """测试排除域名参数"""
        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            exclude_domains=["pinterest.com"]
        )
        params = provider._build_request_params(request)

        assert params["exclude_domains"] == ["pinterest.com"]

    def test_build_request_params_with_advanced_depth(self):
        """测试高级搜索深度"""
        provider = TavilyProvider(api_key="test-key", search_depth="advanced")
        request = ProviderSearchRequest(query="Python")
        params = provider._build_request_params(request)

        assert params["search_depth"] == "advanced"


class TestParseResponse:
    """响应解析测试"""

    def test_parse_response_with_results(self):
        """测试解析带结果的响应"""
        provider = TavilyProvider(api_key="test")
        response = {
            "results": [
                {
                    "title": "Python Tutorial",
                    "url": "https://python.org/tutorial",
                    "content": "Learn Python programming",
                    "published_date": "2024-01-15"
                },
                {
                    "title": "Python Guide",
                    "url": "https://example.com/guide",
                    "content": "Complete guide to Python"
                }
            ]
        }
        results = provider._parse_response(response)

        assert len(results) == 2
        assert results[0].title == "Python Tutorial"
        assert results[0].url == "https://python.org/tutorial"
        assert results[0].description == "Learn Python programming"
        assert results[1].title == "Python Guide"

    def test_parse_response_empty_results(self):
        """测试解析空结果响应"""
        provider = TavilyProvider(api_key="test")
        response = {"results": []}
        results = provider._parse_response(response)

        assert results == []

    def test_parse_response_no_results_key(self):
        """测试解析无 results 键的响应"""
        provider = TavilyProvider(api_key="test")
        response = {}
        results = provider._parse_response(response)

        assert results == []

    def test_parse_response_with_published_date(self):
        """测试解析带发布日期的响应"""
        provider = TavilyProvider(api_key="test")
        response = {
            "results": [
                {
                    "title": "News Article",
                    "url": "https://news.com/article",
                    "content": "Breaking news",
                    "published_date": "2024-01-15T10:30:00Z"
                }
            ]
        }
        results = provider._parse_response(response)

        assert len(results) == 1
        assert results[0].published_date is not None

    def test_parse_response_with_raw_data(self):
        """测试保留原始数据"""
        provider = TavilyProvider(api_key="test")
        response = {
            "results": [
                {
                    "title": "Test",
                    "url": "https://example.com",
                    "content": "Test content",
                    "score": 0.95,
                    "raw_content": "Full content..."
                }
            ]
        }
        results = provider._parse_response(response)

        assert results[0].provider_extra is not None
        assert results[0].provider_extra.get("score") == 0.95


class TestSearch:
    """搜索功能测试"""

    @patch("melodyi_search.providers.tavily_provider.HttpClient")
    def test_search_success(self, mock_http_client_class):
        """测试成功搜索"""
        # 设置 mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Python Official",
                    "url": "https://www.python.org/",
                    "content": "Welcome to Python.org"
                }
            ]
        }
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "tavily"
        assert result.error is None
        assert len(result.results) == 1
        assert result.results[0].title == "Python Official"

    @patch("melodyi_search.providers.tavily_provider.HttpClient")
    def test_search_with_error(self, mock_http_client_class):
        """测试搜索错误"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "tavily"
        assert result.error is not None
        assert "401" in result.error

    @patch("melodyi_search.providers.tavily_provider.HttpClient")
    def test_search_with_time_range(self, mock_http_client_class):
        """测试带时间范围的搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="day")
        )
        result = provider.search(request)

        # 验证时间范围参数被传递
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["time_range"] == "day"

    @patch("melodyi_search.providers.tavily_provider.HttpClient")
    def test_search_with_domain_filter(self, mock_http_client_class):
        """测试带域名过滤的搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Python",
                    "url": "https://python.org/",
                    "content": "Python"
                }
            ]
        }
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            include_domains=["python.org"],
            exclude_domains=["pinterest.com"]
        )
        result = provider.search(request)

        # 验证域名过滤参数被传递
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["include_domains"] == ["python.org"]
        assert payload["exclude_domains"] == ["pinterest.com"]

    @patch("melodyi_search.providers.tavily_provider.HttpClient")
    def test_search_exception(self, mock_http_client_class):
        """测试搜索异常处理"""
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("网络错误")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "tavily"
        assert result.error == "网络错误"
        assert result.results == []

    @patch("melodyi_search.providers.tavily_provider.HttpClient")
    def test_search_response_time(self, mock_http_client_class):
        """测试响应时间记录"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.response_time_ms >= 0