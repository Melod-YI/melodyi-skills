"""SearXNG 提供商单元测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.providers.searxng_provider import SearXNGProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest


class TestSearXNGProviderInit:
    """SearXNGProvider 初始化测试"""

    def test_init_with_host(self):
        """测试使用 host 初始化"""
        provider = SearXNGProvider(host="http://localhost:8888")
        assert provider.host == "http://localhost:8888"
        assert provider.timeout_ms == 10000
        assert provider.max_results == 10
        assert provider.api_key is None

    def test_init_with_custom_host(self):
        """测试自定义 host"""
        provider = SearXNGProvider(
            host="https://search.example.com/",
        )
        assert provider.host == "https://search.example.com"

    def test_init_with_custom_timeout(self):
        """测试自定义超时时间"""
        provider = SearXNGProvider(host="http://localhost:8888", timeout_ms=5000)
        assert provider.timeout_ms == 5000

    def test_init_with_max_results(self):
        """测试自定义最大结果数"""
        provider = SearXNGProvider(host="http://localhost:8888", max_results=20)
        assert provider.max_results == 20

    def test_init_with_api_key(self):
        """测试自定义 API key"""
        provider = SearXNGProvider(host="http://localhost:8888", api_key="secret-key")
        assert provider.api_key == "secret-key"


class TestSearXNGProviderProperties:
    """SearXNGProvider 属性测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = SearXNGProvider(host="http://localhost:8888")
        assert provider.name == "searxng"

    def test_supports_time_filter(self):
        """测试支持原生时间过滤"""
        provider = SearXNGProvider(host="http://localhost:8888")
        assert provider.supports_time_filter() is True

    def test_supports_domain_filter(self):
        """测试不支持原生域名过滤"""
        provider = SearXNGProvider(host="http://localhost:8888")
        assert provider.supports_domain_filter() is False

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = SearXNGProvider(host="http://localhost:8888", max_results=15)
        assert provider.get_max_results_limit() == 15


class TestBuildRequestParams:
    """请求参数构建测试"""

    def test_build_params_basic(self):
        """测试基础参数构建"""
        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(query="Python教程")
        params = provider._build_request_params(request)

        assert params["q"] == "Python教程"
        assert params["format"] == "json"
        assert params["pageno"] == 1

    def test_build_params_with_time_range_day(self):
        """测试时间范围参数 - day"""
        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(
            query="Python教程",
            time_range=TimeRange(range_type="day")
        )
        params = provider._build_request_params(request)
        assert params["time_range"] == "day"

    def test_build_params_with_time_range_week(self):
        """测试时间范围参数 - week"""
        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(
            query="Python教程",
            time_range=TimeRange(range_type="week")
        )
        params = provider._build_request_params(request)
        assert params["time_range"] == "week"

    def test_build_params_with_time_range_month(self):
        """测试时间范围参数 - month"""
        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(
            query="Python教程",
            time_range=TimeRange(range_type="month")
        )
        params = provider._build_request_params(request)
        assert params["time_range"] == "month"

    def test_build_params_with_time_range_year(self):
        """测试时间范围参数 - year"""
        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(
            query="Python教程",
            time_range=TimeRange(range_type="year")
        )
        params = provider._build_request_params(request)
        assert params["time_range"] == "year"

    def test_build_params_with_language(self):
        """测试语言参数"""
        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(
            query="Python教程",
            language="zh-CN"
        )
        params = provider._build_request_params(request)
        assert params["language"] == "zh-CN"

    def test_build_params_no_time_range(self):
        """测试无时间范围"""
        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(query="Python教程")
        params = provider._build_request_params(request)
        assert "time_range" not in params


class TestParseResponse:
    """响应解析测试"""

    def test_parse_response_with_results(self):
        """测试解析带结果的响应"""
        provider = SearXNGProvider(host="http://localhost:8888")
        response = {
            "results": [
                {
                    "title": "Python 官方文档",
                    "url": "https://docs.python.org/3/",
                    "content": "Python 官方文档首页"
                },
                {
                    "title": "Python 教程",
                    "url": "https://www.runoob.com/python/",
                    "content": "Python 基础教程"
                }
            ]
        }
        results = provider._parse_response(response)

        assert len(results) == 2
        assert results[0].title == "Python 官方文档"
        assert results[0].url == "https://docs.python.org/3/"
        assert results[0].description == "Python 官方文档首页"
        assert results[1].title == "Python 教程"

    def test_parse_response_empty(self):
        """测试空响应"""
        provider = SearXNGProvider(host="http://localhost:8888")
        response = {"results": []}
        results = provider._parse_response(response)
        assert results == []

    def test_parse_response_no_results_key(self):
        """测试无 results 键"""
        provider = SearXNGProvider(host="http://localhost:8888")
        response = {}
        results = provider._parse_response(response)
        assert results == []

    def test_parse_response_missing_fields(self):
        """测试缺少字段的响应"""
        provider = SearXNGProvider(host="http://localhost:8888")
        response = {
            "results": [
                {
                    "title": "有标题无URL",
                    # 缺少 url
                },
                {
                    "url": "https://example.com",
                    # 缺少 title
                },
                {
                    "title": "完整结果",
                    "url": "https://valid.com",
                    "content": "描述"
                }
            ]
        }
        results = provider._parse_response(response)

        # 只有完整的结果应该被返回
        assert len(results) == 1
        assert results[0].title == "完整结果"

    def test_parse_response_max_results_limit(self):
        """测试结果数量限制"""
        provider = SearXNGProvider(host="http://localhost:8888", max_results=2)
        response = {
            "results": [
                {"title": "1", "url": "https://a.com"},
                {"title": "2", "url": "https://b.com"},
                {"title": "3", "url": "https://c.com"},
            ]
        }
        results = provider._parse_response(response)
        assert len(results) == 2

    def test_parse_response_with_extra_data(self):
        """测试额外数据解析"""
        provider = SearXNGProvider(host="http://localhost:8888")
        response = {
            "results": [
                {
                    "title": "Python 教程",
                    "url": "https://example.com",
                    "content": "描述",
                    "engine": "google",
                    "engines": ["google", "bing"]
                }
            ]
        }
        results = provider._parse_response(response)

        assert len(results) == 1
        assert results[0].provider_extra is not None
        assert results[0].provider_extra["engine"] == "google"


class TestSearch:
    """搜索功能测试"""

    @patch("melodyi_search.providers.searxng_provider.HttpClient")
    def test_search_success(self, mock_http_client_class):
        """测试成功搜索"""
        # 设置 mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Python 官方文档",
                    "url": "https://docs.python.org/",
                    "content": "官方文档"
                }
            ]
        }
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "searxng"
        assert result.error is None
        assert len(result.results) == 1
        assert result.results[0].title == "Python 官方文档"

    @patch("melodyi_search.providers.searxng_provider.HttpClient")
    def test_search_with_api_key(self, mock_http_client_class):
        """测试带 API key 的搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = SearXNGProvider(
            host="http://localhost:8888",
            api_key="test-key"
        )
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        # 验证请求头包含 Authorization
        call_args = mock_http_client_class.call_args
        headers = call_args.kwargs["default_headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key"

    @patch("melodyi_search.providers.searxng_provider.HttpClient")
    def test_search_with_error(self, mock_http_client_class):
        """测试搜索错误"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "searxng"
        assert result.error is not None
        assert "500" in result.error

    @patch("melodyi_search.providers.searxng_provider.HttpClient")
    def test_search_with_time_range(self, mock_http_client_class):
        """测试带时间范围的搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="day")
        )
        result = provider.search(request)

        # 验证参数包含 time_range
        call_args = mock_client.get.call_args
        params = call_args.kwargs["params"]
        assert params["time_range"] == "day"

    @patch("melodyi_search.providers.searxng_provider.HttpClient")
    def test_search_exception(self, mock_http_client_class):
        """测试搜索异常处理"""
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("网络错误")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "searxng"
        assert result.error == "网络错误"
        assert result.results == []

    @patch("melodyi_search.providers.searxng_provider.HttpClient")
    def test_search_correct_url(self, mock_http_client_class):
        """测试正确的请求 URL"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = SearXNGProvider(host="http://localhost:8888")
        request = ProviderSearchRequest(query="test")
        provider.search(request)

        # 验证请求 URL
        call_args = mock_client.get.call_args
        url = call_args.args[0]
        assert url == "http://localhost:8888/search"

    @patch("melodyi_search.providers.searxng_provider.HttpClient")
    def test_search_host_trailing_slash(self, mock_http_client_class):
        """测试 host 带尾部斜杠"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = SearXNGProvider(host="http://localhost:8888/")
        request = ProviderSearchRequest(query="test")
        provider.search(request)

        # 验证 URL 正确处理
        call_args = mock_client.get.call_args
        url = call_args.args[0]
        assert url == "http://localhost:8888/search"