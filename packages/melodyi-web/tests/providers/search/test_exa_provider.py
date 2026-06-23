"""Exa 提供商单元测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.providers.search.exa_provider import ExaProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest


class TestExaProviderInit:
    """ExaProvider 初始化测试"""

    def test_init_with_api_key(self):
        """测试使用 API key 初始化"""
        provider = ExaProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.api_url == "https://api.exa.ai/search"
        assert provider.timeout_ms == 30000
        assert provider.default_type == "auto"

    def test_init_with_custom_url(self):
        """测试自定义 API URL"""
        provider = ExaProvider(
            api_key="test-key",
            api_url="https://custom.api.com/search"
        )
        assert provider.api_url == "https://custom.api.com/search"

    def test_init_with_custom_timeout(self):
        """测试自定义超时时间"""
        provider = ExaProvider(api_key="test-key", timeout_ms=60000)
        assert provider.timeout_ms == 60000

    def test_init_with_custom_type(self):
        """测试自定义搜索类型"""
        provider = ExaProvider(api_key="test-key", search_type="neural")
        assert provider.default_type == "neural"


class TestExaProviderProperties:
    """ExaProvider 属性测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = ExaProvider(api_key="test")
        assert provider.name == "exa"

    def test_supports_time_filter(self):
        """测试支持原生时间过滤"""
        provider = ExaProvider(api_key="test")
        assert provider.supports_time_filter() is True

    def test_supports_domain_filter(self):
        """测试支持原生域名过滤"""
        provider = ExaProvider(api_key="test")
        assert provider.supports_domain_filter() is True

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = ExaProvider(api_key="test")
        assert provider.get_max_results_limit() == 10


class TestBuildStartDate:
    """起始日期构建测试"""

    def test_build_start_date_none(self):
        """测试无时间范围"""
        provider = ExaProvider(api_key="test")
        result = provider._build_start_date(None)
        assert result is None

    def test_build_start_date_empty_range(self):
        """测试空时间范围"""
        provider = ExaProvider(api_key="test")
        time_range = TimeRange()
        result = provider._build_start_date(time_range)
        assert result is None

    def test_build_start_date_day(self):
        """测试 day 时间范围"""
        provider = ExaProvider(api_key="test")
        time_range = TimeRange(range_type="day")
        result = provider._build_start_date(time_range)

        # 验证格式
        assert result is not None
        assert "T" in result
        assert result.endswith("Z")

        # 验证日期约为 1 天前
        parsed_date = datetime.strptime(result, "%Y-%m-%dT%H:%M:%S.000Z")
        expected_date = datetime.utcnow() - timedelta(days=1)
        # 允许 1 分钟误差
        diff = abs((parsed_date - expected_date).total_seconds())
        assert diff < 60

    def test_build_start_date_week(self):
        """测试 week 时间范围"""
        provider = ExaProvider(api_key="test")
        time_range = TimeRange(range_type="week")
        result = provider._build_start_date(time_range)

        assert result is not None
        parsed_date = datetime.strptime(result, "%Y-%m-%dT%H:%M:%S.000Z")
        expected_date = datetime.utcnow() - timedelta(weeks=1)
        diff = abs((parsed_date - expected_date).total_seconds())
        assert diff < 60

    def test_build_start_date_month(self):
        """测试 month 时间范围"""
        provider = ExaProvider(api_key="test")
        time_range = TimeRange(range_type="month")
        result = provider._build_start_date(time_range)

        assert result is not None
        parsed_date = datetime.strptime(result, "%Y-%m-%dT%H:%M:%S.000Z")
        expected_date = datetime.utcnow() - timedelta(days=30)
        diff = abs((parsed_date - expected_date).total_seconds())
        assert diff < 60

    def test_build_start_date_year(self):
        """测试 year 时间范围"""
        provider = ExaProvider(api_key="test")
        time_range = TimeRange(range_type="year")
        result = provider._build_start_date(time_range)

        assert result is not None
        parsed_date = datetime.strptime(result, "%Y-%m-%dT%H:%M:%S.000Z")
        expected_date = datetime.utcnow() - timedelta(days=365)
        diff = abs((parsed_date - expected_date).total_seconds())
        assert diff < 60

    def test_build_start_date_with_explicit_date(self):
        """测试精确起始日期"""
        provider = ExaProvider(api_key="test")
        explicit_date = datetime(2026, 1, 15, 12, 30, 45)
        time_range = TimeRange(start_date=explicit_date)
        result = provider._build_start_date(time_range)

        assert result == "2026-01-15T12:30:45.000Z"


class TestBuildRequestParams:
    """请求参数构建测试"""

    def test_build_request_params_basic(self):
        """测试基本请求参数"""
        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        params = provider._build_request_params(request)

        assert params["query"] == "Python"
        assert params["numResults"] == 10
        assert params["type"] == "auto"
        assert params["contents"] == {"text": True}
        assert "startPublishedDate" not in params
        assert "includeDomains" not in params
        assert "excludeDomains" not in params

    def test_build_request_params_max_results_limit(self):
        """测试最大结果数限制"""
        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python", max_results=50)
        params = provider._build_request_params(request)

        # 应该被限制为 10
        assert params["numResults"] == 10

    def test_build_request_params_with_time_range(self):
        """测试带时间范围的请求参数"""
        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="week")
        )
        params = provider._build_request_params(request)

        assert "startPublishedDate" in params
        assert params["startPublishedDate"].endswith("Z")

    def test_build_request_params_with_include_domains(self):
        """测试带包含域名的请求参数"""
        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            include_domains=["arxiv.org", "github.com"]
        )
        params = provider._build_request_params(request)

        assert params["includeDomains"] == ["arxiv.org", "github.com"]

    def test_build_request_params_with_exclude_domains(self):
        """测试带排除域名的请求参数"""
        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            exclude_domains=["twitter.com", "facebook.com"]
        )
        params = provider._build_request_params(request)

        assert params["excludeDomains"] == ["twitter.com", "facebook.com"]

    def test_build_request_params_with_all_options(self):
        """测试带所有选项的请求参数"""
        provider = ExaProvider(api_key="test-key", search_type="neural")
        request = ProviderSearchRequest(
            query="machine learning",
            max_results=5,
            time_range=TimeRange(range_type="month"),
            include_domains=["arxiv.org"],
            exclude_domains=["twitter.com"]
        )
        params = provider._build_request_params(request)

        assert params["query"] == "machine learning"
        assert params["numResults"] == 5
        assert params["type"] == "neural"
        assert "startPublishedDate" in params
        assert params["includeDomains"] == ["arxiv.org"]
        assert params["excludeDomains"] == ["twitter.com"]


class TestParseResponse:
    """响应解析测试"""

    def test_parse_response_with_results(self):
        """测试解析带结果的响应"""
        provider = ExaProvider(api_key="test")
        response = {
            "results": [
                {
                    "title": "Python Tutorial",
                    "url": "https://example.com/python",
                    "text": "Learn Python programming",
                    "publishedDate": "2026-01-10"
                },
                {
                    "title": "Machine Learning Guide",
                    "url": "https://ml.example.com/guide",
                    "text": "ML introduction"
                }
            ]
        }
        results = provider._parse_response(response)

        assert len(results) == 2
        assert results[0].title == "Python Tutorial"
        assert results[0].url == "https://example.com/python"
        assert results[0].description == "Learn Python programming"
        assert results[0].published_date is not None
        assert results[1].title == "Machine Learning Guide"
        assert results[1].published_date is None

    def test_parse_response_with_iso_date(self):
        """测试解析 ISO 格式日期"""
        provider = ExaProvider(api_key="test")
        response = {
            "results": [
                {
                    "title": "Article",
                    "url": "https://example.com/article",
                    "text": "Content",
                    "publishedDate": "2026-01-10T15:30:00Z"
                }
            ]
        }
        results = provider._parse_response(response)

        assert len(results) == 1
        assert results[0].published_date is not None

    def test_parse_response_empty(self):
        """测试空响应"""
        provider = ExaProvider(api_key="test")
        response = {"results": []}
        results = provider._parse_response(response)
        assert results == []

    def test_parse_response_no_results_key(self):
        """测试无 results 键"""
        provider = ExaProvider(api_key="test")
        response = {}
        results = provider._parse_response(response)
        assert results == []

    def test_parse_response_missing_title(self):
        """测试缺少标题"""
        provider = ExaProvider(api_key="test")
        response = {
            "results": [
                {
                    "url": "https://example.com/article",
                    "text": "Content"
                }
            ]
        }
        results = provider._parse_response(response)
        assert results == []

    def test_parse_response_missing_url(self):
        """测试缺少 URL"""
        provider = ExaProvider(api_key="test")
        response = {
            "results": [
                {
                    "title": "Article",
                    "text": "Content"
                }
            ]
        }
        results = provider._parse_response(response)
        assert results == []

    def test_parse_response_with_extra_fields(self):
        """测试解析额外字段"""
        provider = ExaProvider(api_key="test")
        response = {
            "results": [
                {
                    "title": "Article",
                    "url": "https://example.com/article",
                    "text": "Content",
                    "score": 0.95,
                    "author": "John Doe",
                    "id": "abc123"
                }
            ]
        }
        results = provider._parse_response(response)

        assert len(results) == 1
        assert results[0].provider_extra is not None
        assert results[0].provider_extra["score"] == 0.95
        assert results[0].provider_extra["author"] == "John Doe"
        assert results[0].provider_extra["id"] == "abc123"


class TestSearch:
    """搜索功能测试"""

    @patch("melodyi_web.providers.search.exa_provider.HttpClient")
    def test_search_success(self, mock_http_client_class):
        """测试成功搜索"""
        # 设置 mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Python Tutorial",
                    "url": "https://python.org/tutorial",
                    "text": "Official Python tutorial"
                }
            ]
        }
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error is None
        assert len(result.results) == 1
        assert result.results[0].title == "Python Tutorial"

    @patch("melodyi_web.providers.search.exa_provider.HttpClient")
    def test_search_with_error(self, mock_http_client_class):
        """测试搜索错误"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error is not None
        assert "401" in result.error

    @patch("melodyi_web.providers.search.exa_provider.HttpClient")
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

        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="day")
        )
        result = provider.search(request)

        # 验证请求参数包含时间过滤
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert "startPublishedDate" in payload
        assert payload["startPublishedDate"].endswith("Z")

    @patch("melodyi_web.providers.search.exa_provider.HttpClient")
    def test_search_with_domain_filters(self, mock_http_client_class):
        """测试带域名过滤的搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            include_domains=["arxiv.org"],
            exclude_domains=["twitter.com"]
        )
        result = provider.search(request)

        # 验证请求参数包含域名过滤
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["includeDomains"] == ["arxiv.org"]
        assert payload["excludeDomains"] == ["twitter.com"]

    @patch("melodyi_web.providers.search.exa_provider.HttpClient")
    def test_search_exception(self, mock_http_client_class):
        """测试搜索异常处理"""
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("网络错误")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error == "网络错误"
        assert result.results == []

    @patch("melodyi_web.providers.search.exa_provider.HttpClient")
    def test_search_headers(self, mock_http_client_class):
        """测试请求头设置"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = ExaProvider(api_key="test-api-key")
        request = ProviderSearchRequest(query="test")
        provider.search(request)

        # 验证 HttpClient 初始化参数
        call_args = mock_http_client_class.call_args
        assert call_args.kwargs["timeout_ms"] == 30000
        headers = call_args.kwargs["default_headers"]
        assert headers["Content-Type"] == "application/json"
        assert headers["x-api-key"] == "test-api-key"

    @patch("melodyi_web.providers.search.exa_provider.HttpClient")
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

        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.response_time_ms >= 0
        assert result.response_time_ms < provider.timeout_ms