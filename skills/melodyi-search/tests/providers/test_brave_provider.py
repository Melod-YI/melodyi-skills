"""Brave 提供商单元测试

注意：Brave 不支持域名过滤，site: 操作符不可靠，因此不测试域名过滤功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.providers.brave_provider import BraveProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest


class TestBraveProviderInit:
    """BraveProvider 初始化测试"""

    def test_init_with_api_key(self):
        """测试使用 API key 初始化"""
        provider = BraveProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.api_url == "https://api.search.brave.com/res/v1/web/search"
        assert provider.timeout_ms == 10000

    def test_init_with_custom_url(self):
        """测试自定义 API URL"""
        provider = BraveProvider(
            api_key="test-key",
            api_url="https://custom.api.com/search"
        )
        assert provider.api_url == "https://custom.api.com/search"

    def test_init_with_custom_timeout(self):
        """测试自定义超时时间"""
        provider = BraveProvider(api_key="test-key", timeout_ms=5000)
        assert provider.timeout_ms == 5000


class TestBraveProviderProperties:
    """BraveProvider 属性测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = BraveProvider(api_key="test")
        assert provider.name == "brave"

    def test_supports_time_filter(self):
        """测试支持原生时间过滤"""
        provider = BraveProvider(api_key="test")
        assert provider.supports_time_filter() is True

    def test_supports_domain_filter(self):
        """测试不支持域名过滤

        Brave 不支持域名过滤，site: 操作符不可靠，搜索引擎不保证遵守。
        """
        provider = BraveProvider(api_key="test")
        assert provider.supports_domain_filter() is False

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = BraveProvider(api_key="test")
        assert provider.get_max_results_limit() == 20


class TestBuildFreshness:
    """freshness 参数映射测试"""

    def test_build_freshness_day(self):
        """测试 day 映射到 pd"""
        provider = BraveProvider(api_key="test")
        freshness = provider._build_freshness("day")
        assert freshness == "pd"

    def test_build_freshness_week(self):
        """测试 week 映射到 pw"""
        provider = BraveProvider(api_key="test")
        freshness = provider._build_freshness("week")
        assert freshness == "pw"

    def test_build_freshness_month(self):
        """测试 month 映射到 pm"""
        provider = BraveProvider(api_key="test")
        freshness = provider._build_freshness("month")
        assert freshness == "pm"

    def test_build_freshness_year(self):
        """测试 year 映射到 py"""
        provider = BraveProvider(api_key="test")
        freshness = provider._build_freshness("year")
        assert freshness == "py"

    def test_build_freshness_unknown(self):
        """测试未知类型返回 None"""
        provider = BraveProvider(api_key="test")
        freshness = provider._build_freshness("unknown")
        assert freshness is None


class TestBuildRequestParams:
    """请求参数构建测试"""

    def test_build_request_params_basic(self):
        """测试基本请求参数构建"""
        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python教程")
        params = provider._build_request_params("Python教程", request)

        assert params["q"] == "Python教程"
        assert params["count"] == 10

    def test_build_request_params_with_max_results(self):
        """测试自定义最大结果数"""
        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python", max_results=15)
        params = provider._build_request_params("Python", request)

        assert params["count"] == 15

    def test_build_request_params_with_max_results_over_limit(self):
        """测试最大结果数超过限制"""
        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python", max_results=50)
        params = provider._build_request_params("Python", request)

        assert params["count"] == 20  # 限制为 20

    def test_build_request_params_with_time_range_day(self):
        """测试时间范围参数（day）"""
        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="day")
        )
        params = provider._build_request_params("Python", request)

        assert params["freshness"] == "pd"

    def test_build_request_params_with_time_range_week(self):
        """测试时间范围参数（week）"""
        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="week")
        )
        params = provider._build_request_params("Python", request)

        assert params["freshness"] == "pw"

    def test_build_request_params_with_time_range_month(self):
        """测试时间范围参数（month）"""
        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="month")
        )
        params = provider._build_request_params("Python", request)

        assert params["freshness"] == "pm"

    def test_build_request_params_with_time_range_year(self):
        """测试时间范围参数（year）"""
        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="year")
        )
        params = provider._build_request_params("Python", request)

        assert params["freshness"] == "py"


class TestParseResponse:
    """响应解析测试"""

    def test_parse_response_with_results(self):
        """测试解析带结果的响应"""
        provider = BraveProvider(api_key="test")
        response = {
            "web": {
                "results": [
                    {
                        "title": "Python Tutorial",
                        "url": "https://python.org/tutorial",
                        "description": "Learn Python programming"
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

    def test_parse_response_empty_results(self):
        """测试解析空结果响应"""
        provider = BraveProvider(api_key="test")
        response = {"web": {"results": []}}
        results = provider._parse_response(response)

        assert results == []

    def test_parse_response_no_web_key(self):
        """测试解析无 web 键的响应"""
        provider = BraveProvider(api_key="test")
        response = {}
        results = provider._parse_response(response)

        assert results == []

    def test_parse_response_no_results_key(self):
        """测试解析无 results 键的响应"""
        provider = BraveProvider(api_key="test")
        response = {"web": {}}
        results = provider._parse_response(response)

        assert results == []

    def test_parse_response_with_extra_data(self):
        """测试保留原始数据"""
        provider = BraveProvider(api_key="test")
        response = {
            "web": {
                "results": [
                    {
                        "title": "Test",
                        "url": "https://example.com",
                        "description": "Test content",
                        "type": "search",
                        "thumbnail": {"url": "https://example.com/thumb.jpg"}
                    }
                ]
            }
        }
        results = provider._parse_response(response)

        assert len(results) == 1
        assert results[0].provider_extra is not None
        assert results[0].provider_extra.get("type") == "search"

    def test_parse_response_skip_invalid(self):
        """测试跳过无效项"""
        provider = BraveProvider(api_key="test")
        response = {
            "web": {
                "results": [
                    {
                        "title": "",
                        "url": "https://example.com",
                        "description": "No title"
                    },
                    {
                        "title": "Valid",
                        "url": "https://valid.com",
                        "description": "Valid result"
                    }
                ]
            }
        }
        results = provider._parse_response(response)

        assert len(results) == 1
        assert results[0].title == "Valid"


class TestSearch:
    """搜索功能测试"""

    @patch("melodyi_search.providers.brave_provider.HttpClient")
    def test_search_success(self, mock_http_client_class):
        """测试成功搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Python Official",
                        "url": "https://www.python.org/",
                        "description": "Welcome to Python.org"
                    }
                ]
            }
        }
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "brave"
        assert result.error is None
        assert len(result.results) == 1
        assert result.results[0].title == "Python Official"

    @patch("melodyi_search.providers.brave_provider.HttpClient")
    def test_search_with_error(self, mock_http_client_class):
        """测试搜索错误"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "brave"
        assert result.error is not None
        assert "401" in result.error

    @patch("melodyi_search.providers.brave_provider.HttpClient")
    def test_search_with_time_range(self, mock_http_client_class):
        """测试带时间范围的搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"web": {"results": []}}
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="day")
        )
        result = provider.search(request)

        # 验证时间范围参数被传递
        call_args = mock_client.get.call_args
        params = call_args.kwargs["params"]
        assert params["freshness"] == "pd"

    @patch("melodyi_search.providers.brave_provider.HttpClient")
    def test_search_domain_params_ignored(self, mock_http_client_class):
        """测试域名过滤参数被忽略

        Brave 不支持域名过滤，include_domains 和 exclude_domains 参数被忽略。
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Python",
                        "url": "https://python.org/",
                        "description": "Python"
                    }
                ]
            }
        }
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            include_domains=["python.org"],
            exclude_domains=["pinterest.com"]
        )
        result = provider.search(request)

        # 验证查询没有被修改（无 site: 操作符注入）
        call_args = mock_client.get.call_args
        params = call_args.kwargs["params"]
        assert params["q"] == "Python"
        assert "site:" not in params["q"]
        assert "-site:" not in params["q"]

    @patch("melodyi_search.providers.brave_provider.HttpClient")
    def test_search_exception(self, mock_http_client_class):
        """测试搜索异常处理"""
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("网络错误")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "brave"
        assert result.error == "网络错误"
        assert result.results == []

    @patch("melodyi_search.providers.brave_provider.HttpClient")
    def test_search_response_time(self, mock_http_client_class):
        """测试响应时间记录"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"web": {"results": []}}
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.response_time_ms >= 0

    @patch("melodyi_search.providers.brave_provider.HttpClient")
    def test_search_headers(self, mock_http_client_class):
        """测试请求头设置"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"web": {"results": []}}
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = BraveProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        provider.search(request)

        # 验证 HttpClient 使用正确的 headers
        call_args = mock_http_client_class.call_args
        headers = call_args.kwargs["default_headers"]
        assert headers["Accept"] == "application/json"
        assert headers["X-Subscription-Token"] == "test-key"