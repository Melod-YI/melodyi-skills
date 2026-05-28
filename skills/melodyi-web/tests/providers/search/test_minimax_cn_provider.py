"""MiniMax-CN 提供商单元测试

基于 MiniMax Coding Plan Search API 规范：
- URL: https://api.minimaxi.com/v1/coding_plan/search
- 方法: POST
- 请求体: {"q": query}
- 响应: {"organic": [...], "base_resp": {...}}
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.providers.search.minimax_cn_provider import MiniMaxCNProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest


class TestMiniMaxCNProviderInit:
    """MiniMaxCNProvider 初始化测试"""

    def test_init_with_api_key(self):
        """测试使用 API key 初始化"""
        provider = MiniMaxCNProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.api_host == "https://api.minimaxi.com"
        assert provider.timeout_ms == 10000
        assert provider.max_results == 10

    def test_init_with_custom_host(self):
        """测试自定义 API host"""
        provider = MiniMaxCNProvider(
            api_key="test-key",
            api_host="https://custom.api.com"
        )
        assert provider.api_host == "https://custom.api.com"

    def test_init_with_custom_timeout(self):
        """测试自定义超时时间"""
        provider = MiniMaxCNProvider(api_key="test-key", timeout_ms=5000)
        assert provider.timeout_ms == 5000

    def test_init_with_custom_max_results(self):
        """测试自定义最大结果数"""
        provider = MiniMaxCNProvider(api_key="test-key", max_results=20)
        assert provider.max_results == 20


class TestMiniMaxCNProviderProperties:
    """MiniMaxCNProvider 属性测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = MiniMaxCNProvider(api_key="test")
        assert provider.name == "minimax-cn"

    def test_supports_time_filter(self):
        """测试不支持原生时间过滤"""
        provider = MiniMaxCNProvider(api_key="test")
        assert provider.supports_time_filter() is False

    def test_supports_domain_filter(self):
        """测试不支持原生域名过滤"""
        provider = MiniMaxCNProvider(api_key="test")
        assert provider.supports_domain_filter() is False

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = MiniMaxCNProvider(api_key="test")
        assert provider.get_max_results_limit() == 10


class TestInjectTimeKeywords:
    """时间关键词注入测试"""

    def test_inject_time_keywords_none(self):
        """测试无时间范围"""
        provider = MiniMaxCNProvider(api_key="test")
        query = provider._inject_time_keywords("python教程", None)
        assert query == "python教程"

    def test_inject_time_keywords_empty_range(self):
        """测试空时间范围"""
        provider = MiniMaxCNProvider(api_key="test")
        time_range = TimeRange()
        query = provider._inject_time_keywords("python教程", time_range)
        assert query == "python教程"

    def test_inject_time_keywords_day(self):
        """测试注入"今天"关键词"""
        provider = MiniMaxCNProvider(api_key="test")
        time_range = TimeRange(range_type="day")
        query = provider._inject_time_keywords("python教程", time_range)
        assert "今天" in query
        assert "最新" in query
        assert "python教程" in query

    def test_inject_time_keywords_week(self):
        """测试注入"本周"关键词"""
        provider = MiniMaxCNProvider(api_key="test")
        time_range = TimeRange(range_type="week")
        query = provider._inject_time_keywords("python教程", time_range)
        assert "本周" in query
        assert "最新" in query

    def test_inject_time_keywords_month(self):
        """测试注入"本月"关键词"""
        provider = MiniMaxCNProvider(api_key="test")
        time_range = TimeRange(range_type="month")
        query = provider._inject_time_keywords("python教程", time_range)
        assert "本月" in query
        assert "最新" in query

    def test_inject_time_keywords_year(self):
        """测试注入"今年"关键词"""
        provider = MiniMaxCNProvider(api_key="test")
        time_range = TimeRange(range_type="year")
        query = provider._inject_time_keywords("python教程", time_range)
        assert "今年" in query
        assert "最新" in query


class TestDomainFilter:
    """域名过滤测试"""

    def test_passes_domain_filter_no_filter(self):
        """测试无过滤条件"""
        provider = MiniMaxCNProvider(api_key="test")
        result = provider._passes_domain_filter(
            "https://example.com/page",
            None,
            None
        )
        assert result is True

    def test_passes_domain_filter_include_match(self):
        """测试包含域名匹配"""
        provider = MiniMaxCNProvider(api_key="test")
        result = provider._passes_domain_filter(
            "https://example.com/page",
            ["example.com", "test.com"],
            None
        )
        assert result is True

    def test_passes_domain_filter_include_no_match(self):
        """测试包含域名不匹配"""
        provider = MiniMaxCNProvider(api_key="test")
        result = provider._passes_domain_filter(
            "https://other.com/page",
            ["example.com", "test.com"],
            None
        )
        assert result is False

    def test_passes_domain_filter_exclude_match(self):
        """测试排除域名匹配"""
        provider = MiniMaxCNProvider(api_key="test")
        result = provider._passes_domain_filter(
            "https://example.com/page",
            None,
            ["example.com", "test.com"]
        )
        assert result is False

    def test_passes_domain_filter_exclude_no_match(self):
        """测试排除域名不匹配"""
        provider = MiniMaxCNProvider(api_key="test")
        result = provider._passes_domain_filter(
            "https://other.com/page",
            None,
            ["example.com", "test.com"]
        )
        assert result is True

    def test_passes_domain_filter_case_insensitive(self):
        """测试域名过滤大小写不敏感"""
        provider = MiniMaxCNProvider(api_key="test")
        result = provider._passes_domain_filter(
            "https://EXAMPLE.COM/page",
            ["example.com"],
            None
        )
        assert result is True


class TestParseResponse:
    """响应解析测试 - 基于 coding_plan/search API 格式"""

    def test_parse_response_success(self):
        """测试解析成功响应"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {
            "organic": [
                {
                    "title": "Python教程",
                    "link": "https://python.org/docs",
                    "snippet": "Python 官方教程",
                    "date": "2026-04-14 10:00:00"
                },
                {
                    "title": "菜鸟教程",
                    "link": "https://runoob.com/python",
                    "snippet": "Python 基础教程",
                    "date": "2026-04-13 15:00:00"
                }
            ],
            "base_resp": {
                "status_code": 0,
                "status_msg": "success"
            }
        }
        results = provider._parse_response(response)

        assert len(results) == 2
        assert results[0].title == "Python教程"
        assert results[0].url == "https://python.org/docs"
        assert results[0].description == "Python 官方教程"

    def test_parse_response_with_error_status(self):
        """测试解析错误状态响应"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {
            "organic": [],
            "base_resp": {
                "status_code": 1,
                "status_msg": "error"
            }
        }
        results = provider._parse_response(response)
        assert results == []

    def test_parse_response_empty_organic(self):
        """测试解析空 organic"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {
            "organic": [],
            "base_resp": {
                "status_code": 0,
                "status_msg": "success"
            }
        }
        results = provider._parse_response(response)
        assert results == []

    def test_parse_response_with_domain_filter(self):
        """测试解析响应并应用域名过滤"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {
            "organic": [
                {
                    "title": "Python",
                    "link": "https://allowed.com/python",
                    "snippet": "desc",
                    "date": ""
                },
                {
                    "title": "其他",
                    "link": "https://blocked.com/other",
                    "snippet": "desc",
                    "date": ""
                }
            ],
            "base_resp": {"status_code": 0, "status_msg": "success"}
        }
        results = provider._parse_response(
            response,
            include_domains=["allowed.com"]
        )

        assert len(results) == 1
        assert "allowed.com" in results[0].url

    def test_parse_response_max_results(self):
        """测试结果数量限制"""
        provider = MiniMaxCNProvider(api_key="test", max_results=2)
        response = {
            "organic": [
                {"title": "A", "link": "https://a.com", "snippet": "", "date": ""},
                {"title": "B", "link": "https://b.com", "snippet": "", "date": ""},
                {"title": "C", "link": "https://c.com", "snippet": "", "date": ""},
            ],
            "base_resp": {"status_code": 0, "status_msg": "success"}
        }
        results = provider._parse_response(response)
        assert len(results) == 2

    def test_parse_response_with_date(self):
        """测试解析带日期的结果"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {
            "organic": [
                {
                    "title": "标题",
                    "link": "https://example.com",
                    "snippet": "描述",
                    "date": "2026-04-14 10:00:00"
                }
            ],
            "base_resp": {"status_code": 0, "status_msg": "success"}
        }
        results = provider._parse_response(response)

        assert len(results) == 1
        assert results[0].published_date is not None
        assert results[0].published_date.year == 2026

    def test_parse_response_missing_link(self):
        """测试解析缺少 link 的结果"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {
            "organic": [
                {"title": "无链接", "snippet": "描述", "date": ""}
            ],
            "base_resp": {"status_code": 0, "status_msg": "success"}
        }
        results = provider._parse_response(response)
        # 缺少链接的结果应被跳过
        assert len(results) == 0


class TestSearch:
    """搜索功能测试"""

    @patch("melodyi_web.providers.search.minimax_cn_provider.HttpClient")
    def test_search_success(self, mock_http_client_class):
        """测试成功搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "Python教程",
                    "link": "https://python.org/docs",
                    "snippet": "Python 官方教程",
                    "date": "2026-04-14 10:00:00"
                }
            ],
            "base_resp": {"status_code": 0, "status_msg": "success"}
        }
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = MiniMaxCNProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "minimax-cn"
        assert result.error is None
        assert len(result.results) == 1
        assert result.results[0].title == "Python教程"

    @patch("melodyi_web.providers.search.minimax_cn_provider.HttpClient")
    def test_search_with_error_status(self, mock_http_client_class):
        """测试搜索错误状态"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [],
            "base_resp": {
                "status_code": 1,
                "status_msg": "API 错误"
            }
        }
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = MiniMaxCNProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "minimax-cn"
        assert result.error is None  # base_resp 错误不触发 error，只是结果为空
        assert len(result.results) == 0

    @patch("melodyi_web.providers.search.minimax_cn_provider.HttpClient")
    def test_search_with_http_error(self, mock_http_client_class):
        """测试 HTTP 错误"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "base_resp": {"status_code": 401, "status_msg": "Unauthorized"}
        }
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = MiniMaxCNProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "minimax-cn"
        assert result.error is not None
        assert "401" in result.error

    @patch("melodyi_web.providers.search.minimax_cn_provider.HttpClient")
    def test_search_with_time_range(self, mock_http_client_class):
        """测试带时间范围的搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [{"title": "结果", "link": "https://example.com", "snippet": "", "date": ""}],
            "base_resp": {"status_code": 0, "status_msg": "success"}
        }
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = MiniMaxCNProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            time_range=TimeRange(range_type="day")
        )
        result = provider.search(request)

        # 验证时间关键词被注入到查询中
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert "今天" in payload["q"]
        assert "最新" in payload["q"]

    @patch("melodyi_web.providers.search.minimax_cn_provider.HttpClient")
    def test_search_with_domain_filter(self, mock_http_client_class):
        """测试带域名过滤的搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [
                {"title": "Python", "link": "https://python.org/docs", "snippet": "", "date": ""},
                {"title": "其他", "link": "https://other.com/page", "snippet": "", "date": ""}
            ],
            "base_resp": {"status_code": 0, "status_msg": "success"}
        }
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = MiniMaxCNProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="Python",
            include_domains=["python.org"]
        )
        result = provider.search(request)

        # 只应包含 python.org 的结果
        assert len(result.results) == 1
        assert "python.org" in result.results[0].url

    @patch("melodyi_web.providers.search.minimax_cn_provider.HttpClient")
    def test_search_exception(self, mock_http_client_class):
        """测试搜索异常处理"""
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("网络错误")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = MiniMaxCNProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "minimax-cn"
        assert result.error == "网络错误"
        assert result.results == []

    @patch("melodyi_web.providers.search.minimax_cn_provider.HttpClient")
    def test_search_correct_endpoint(self, mock_http_client_class):
        """测试调用正确的 API endpoint"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [],
            "base_resp": {"status_code": 0, "status_msg": "success"}
        }
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_http_client_class.return_value = mock_client

        provider = MiniMaxCNProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        # 验证调用了正确的 endpoint
        call_args = mock_client.post.call_args
        url = call_args.args[0]
        assert url == "https://api.minimaxi.com/v1/coding_plan/search"

        # 验证请求体格式正确
        payload = call_args.kwargs["json"]
        assert "q" in payload
        assert payload["q"] == "Python"
        # 不应包含 model 参数
        assert "model" not in payload
        assert "messages" not in payload