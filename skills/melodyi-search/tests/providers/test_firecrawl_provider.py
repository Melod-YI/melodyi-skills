"""Firecrawl 提供商单元测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.providers.firecrawl_provider import FirecrawlProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest


class TestFirecrawlProviderInit:
    """FirecrawlProvider 初始化测试"""

    def test_init_with_api_key(self):
        """测试使用 API key 初始化"""
        provider = FirecrawlProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.api_url == "https://api.firecrawl.dev/v1/search"
        assert provider.timeout_ms == 10000
        assert provider.max_results == 10

    def test_init_with_custom_url(self):
        """测试自定义 API URL（自托管）"""
        provider = FirecrawlProvider(
            api_key="test-key",
            api_url="http://localhost:8888/v1/search"
        )
        assert provider.api_url == "http://localhost:8888/v1/search"

    def test_init_with_custom_timeout(self):
        """测试自定义超时时间"""
        provider = FirecrawlProvider(api_key="test-key", timeout_ms=5000)
        assert provider.timeout_ms == 5000

    def test_init_with_custom_max_results(self):
        """测试自定义最大结果数"""
        provider = FirecrawlProvider(api_key="test-key", max_results=20)
        assert provider.max_results == 20


class TestFirecrawlProviderProperties:
    """FirecrawlProvider 属性测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = FirecrawlProvider(api_key="test")
        assert provider.name == "firecrawl"

    def test_supports_time_filter(self):
        """测试不支持原生时间过滤"""
        provider = FirecrawlProvider(api_key="test")
        assert provider.supports_time_filter() is False

    def test_supports_domain_filter(self):
        """测试不支持原生域名过滤"""
        provider = FirecrawlProvider(api_key="test")
        assert provider.supports_domain_filter() is False

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = FirecrawlProvider(api_key="test", max_results=15)
        assert provider.get_max_results_limit() == 15


class TestBuildRequestParams:
    """请求参数构建测试"""

    def test_build_request_params_basic(self):
        """测试基本请求参数构建"""
        provider = FirecrawlProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python教程")
        params = provider._build_request_params(request)

        assert params["query"] == "Python教程"
        assert params["limit"] == 10

    def test_build_request_params_with_max_results(self):
        """测试自定义最大结果数"""
        provider = FirecrawlProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python", max_results=5)
        params = provider._build_request_params(request)

        assert params["limit"] == 5

    def test_build_request_params_max_results_capped(self):
        """测试结果数被提供商限制"""
        provider = FirecrawlProvider(api_key="test-key", max_results=8)
        request = ProviderSearchRequest(query="Python", max_results=15)
        params = provider._build_request_params(request)

        # 应该被限制到提供商的 max_results
        assert params["limit"] == 8

    def test_build_request_params_ignores_time_range(self):
        """测试忽略时间范围参数（不支持）"""
        provider = FirecrawlProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="day")
        )
        params = provider._build_request_params(request)

        # 不应包含时间范围参数
        assert "time_range" not in params

    def test_build_request_params_ignores_domain_filter(self):
        """测试忽略域名过滤参数（不支持）"""
        provider = FirecrawlProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            include_domains=["python.org"],
            exclude_domains=["pinterest.com"]
        )
        params = provider._build_request_params(request)

        # 不应包含域名过滤参数
        assert "include_domains" not in params
        assert "exclude_domains" not in params


class TestParseResponse:
    """响应解析测试"""

    def test_parse_response_web_results(self):
        """测试解析 web 结果"""
        provider = FirecrawlProvider(api_key="test")
        response = {
            "success": True,
            "data": {
                "web": [
                    {
                        "title": "Python Tutorial",
                        "url": "https://python.org/tutorial",
                        "description": "Learn Python programming",
                        "position": 1
                    },
                    {
                        "title": "Python Guide",
                        "url": "https://example.com/guide",
                        "description": "Complete guide to Python"
                    }
                ]
            }
        }
        results = provider._parse_response(response)

        assert len(results) == 2
        assert results[0].title == "Python Tutorial"
        assert results[0].url == "https://python.org/tutorial"
        assert results[0].description == "Learn Python programming"
        assert results[1].title == "Python Guide"

    def test_parse_response_news_results(self):
        """测试解析 news 结果"""
        provider = FirecrawlProvider(api_key="test")
        response = {
            "success": True,
            "data": {
                "news": [
                    {
                        "title": "Python News",
                        "url": "https://news.com/article",
                        "snippet": "Breaking Python news",
                        "date": "2024-01-15"
                    }
                ]
            }
        }
        results = provider._parse_response(response)

        assert len(results) == 1
        assert results[0].title == "Python News"
        assert results[0].description == "Breaking Python news"
        assert results[0].published_date is not None
        assert results[0].published_date.year == 2024

    def test_parse_response_news_with_iso_date(self):
        """测试解析 news 结果的 ISO 日期"""
        provider = FirecrawlProvider(api_key="test")
        response = {
            "success": True,
            "data": {
                "news": [
                    {
                        "title": "News Article",
                        "url": "https://news.com/article",
                        "snippet": "Breaking news",
                        "date": "2024-01-15T10:30:00Z"
                    }
                ]
            }
        }
        results = provider._parse_response(response)

        assert len(results) == 1
        assert results[0].published_date is not None

    def test_parse_response_mixed_results(self):
        """测试解析混合结果（web + news）"""
        provider = FirecrawlProvider(api_key="test")
        response = {
            "success": True,
            "data": {
                "web": [
                    {
                        "title": "Web Result",
                        "url": "https://example.com",
                        "description": "Web content"
                    }
                ],
                "news": [
                    {
                        "title": "News Result",
                        "url": "https://news.com",
                        "snippet": "News content",
                        "date": "2024-01-15"
                    }
                ]
            }
        }
        results = provider._parse_response(response)

        # 应包含两种结果
        assert len(results) == 2

    def test_parse_response_empty_data(self):
        """测试解析空数据"""
        provider = FirecrawlProvider(api_key="test")
        response = {
            "success": True,
            "data": {}
        }
        results = provider._parse_response(response)
        assert results == []

    def test_parse_response_no_success(self):
        """测试解析失败响应"""
        provider = FirecrawlProvider(api_key="test")
        response = {
            "success": False,
            "data": {}
        }
        results = provider._parse_response(response)
        assert results == []

    def test_parse_response_no_data_key(self):
        """测试无 data 键的响应"""
        provider = FirecrawlProvider(api_key="test")
        response = {
            "success": True
        }
        results = provider._parse_response(response)
        assert results == []

    def test_parse_response_missing_fields(self):
        """测试缺少必要字段的响应"""
        provider = FirecrawlProvider(api_key="test")
        response = {
            "success": True,
            "data": {
                "web": [
                    {
                        "title": "有标题无URL"
                        # 缺少 url
                    },
                    {
                        "url": "https://example.com"
                        # 缺少 title
                    },
                    {
                        "title": "完整结果",
                        "url": "https://valid.com",
                        "description": "描述"
                    }
                ]
            }
        }
        results = provider._parse_response(response)

        # 只有完整的结果应该被返回
        assert len(results) == 1
        assert results[0].title == "完整结果"

    def test_parse_response_max_results_limit(self):
        """测试结果数量限制"""
        provider = FirecrawlProvider(api_key="test", max_results=2)
        response = {
            "success": True,
            "data": {
                "web": [
                    {"title": "1", "url": "https://a.com"},
                    {"title": "2", "url": "https://b.com"},
                    {"title": "3", "url": "https://c.com"},
                ]
            }
        }
        results = provider._parse_response(response)
        assert len(results) == 2

    def test_parse_response_with_position(self):
        """测试解析 position 字段"""
        provider = FirecrawlProvider(api_key="test")
        response = {
            "success": True,
            "data": {
                "web": [
                    {
                        "title": "Python Tutorial",
                        "url": "https://example.com",
                        "description": "Description",
                        "position": 1
                    }
                ]
            }
        }
        results = provider._parse_response(response)

        assert len(results) == 1
        assert results[0].provider_extra is not None
        assert results[0].provider_extra["position"] == 1


class TestSearch:
    """搜索功能测试"""

    @patch("melodyi_search.providers.firecrawl_provider.HttpClient")
    def test_search_success(self, mock_http_client_class):
        """测试成功搜索"""
        # 设置 mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "web": [
                    {
                        "title": "Python Official",
                        "url": "https://www.python.org/",
                        "description": "Welcome to Python.org"
                    }
                ]
            }
        }
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = FirecrawlProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "firecrawl"
        assert result.error is None
        assert len(result.results) == 1
        assert result.results[0].title == "Python Official"

    @patch("melodyi_search.providers.firecrawl_provider.HttpClient")
    def test_search_with_authorization_header(self, mock_http_client_class):
        """测试 Authorization 请求头"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = FirecrawlProvider(api_key="secret-key")
        request = ProviderSearchRequest(query="Python")
        provider.search(request)

        # 验证请求头包含 Authorization
        call_args = mock_http_client_class.call_args
        headers = call_args.kwargs["default_headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer secret-key"

    @patch("melodyi_search.providers.firecrawl_provider.HttpClient")
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

        provider = FirecrawlProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "firecrawl"
        assert result.error is not None
        assert "401" in result.error

    @patch("melodyi_search.providers.firecrawl_provider.HttpClient")
    def test_search_exception(self, mock_http_client_class):
        """测试搜索异常处理"""
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("网络错误")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = FirecrawlProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "firecrawl"
        assert result.error == "网络错误"
        assert result.results == []

    @patch("melodyi_search.providers.firecrawl_provider.HttpClient")
    def test_search_correct_url(self, mock_http_client_class):
        """测试正确的请求 URL"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = FirecrawlProvider(api_key="test-key")
        request = ProviderSearchRequest(query="test")
        provider.search(request)

        # 验证请求 URL
        call_args = mock_client.post.call_args
        url = call_args.args[0]
        assert url == "https://api.firecrawl.dev/v1/search"

    @patch("melodyi_search.providers.firecrawl_provider.HttpClient")
    def test_search_custom_url(self, mock_http_client_class):
        """测试自定义 URL（自托管）"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = FirecrawlProvider(
            api_key="test-key",
            api_url="http://localhost:8888/v1/search"
        )
        request = ProviderSearchRequest(query="test")
        provider.search(request)

        # 验证请求 URL
        call_args = mock_client.post.call_args
        url = call_args.args[0]
        assert url == "http://localhost:8888/v1/search"

    @patch("melodyi_search.providers.firecrawl_provider.HttpClient")
    def test_search_response_time(self, mock_http_client_class):
        """测试响应时间记录"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = FirecrawlProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.response_time_ms >= 0

    @patch("melodyi_search.providers.firecrawl_provider.HttpClient")
    def test_search_ignores_time_range(self, mock_http_client_class):
        """测试忽略时间范围参数"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = FirecrawlProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="day")
        )
        provider.search(request)

        # 验证请求参数不包含时间范围
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert "time_range" not in payload

    @patch("melodyi_search.providers.firecrawl_provider.HttpClient")
    def test_search_ignores_domain_filter(self, mock_http_client_class):
        """测试忽略域名过滤参数"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = FirecrawlProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            include_domains=["python.org"],
            exclude_domains=["pinterest.com"]
        )
        provider.search(request)

        # 验证请求参数不包含域名过滤
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert "include_domains" not in payload
        assert "exclude_domains" not in payload