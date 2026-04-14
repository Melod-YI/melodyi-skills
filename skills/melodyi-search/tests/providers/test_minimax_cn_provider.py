"""MiniMax-CN 提供商单元测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.providers.minimax_cn_provider import MiniMaxCNProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest


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

    def test_init_with_custom_model(self):
        """测试自定义模型"""
        provider = MiniMaxCNProvider(api_key="test-key", model="custom-model")
        assert provider.model == "custom-model"


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


class TestExtractSearchItems:
    """搜索结果提取测试"""

    def test_extract_markdown_links(self):
        """测试提取 Markdown 链接"""
        provider = MiniMaxCNProvider(api_key="test")
        content = "这是一个[Python教程](https://example.com/python)和[Java教程](https://example.com/java)"
        results = provider._extract_search_items(content)

        assert len(results) == 2
        assert results[0].title == "Python教程"
        assert results[0].url == "https://example.com/python"
        assert results[1].title == "Java教程"
        assert results[1].url == "https://example.com/java"

    def test_extract_plain_urls(self):
        """测试提取纯文本 URL"""
        provider = MiniMaxCNProvider(api_key="test")
        content = "访问 https://example.com/docs 获取更多信息"
        results = provider._extract_search_items(content)

        assert len(results) == 1
        assert results[0].url == "https://example.com/docs"

    def test_extract_mixed_content(self):
        """测试提取混合内容"""
        provider = MiniMaxCNProvider(api_key="test")
        content = """
        推荐资源：
        1. [Python官方文档](https://docs.python.org/3/)
        2. https://www.python.org/
        3. [教程](https://tutorial.python.org/)
        """
        results = provider._extract_search_items(content)

        # 至少提取到两个结果
        assert len(results) >= 2
        urls = [r.url for r in results]
        assert "https://docs.python.org/3/" in urls

    def test_extract_empty_content(self):
        """测试空内容"""
        provider = MiniMaxCNProvider(api_key="test")
        results = provider._extract_search_items("")
        assert results == []


class TestExtractContent:
    """响应内容提取测试"""

    def test_extract_content_openai_format(self):
        """测试 OpenAI 格式响应"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {
            "choices": [
                {
                    "message": {
                        "content": "这是响应内容"
                    }
                }
            ]
        }
        content = provider._extract_content(response)
        assert content == "这是响应内容"

    def test_extract_content_minimax_format(self):
        """测试 MiniMax 格式响应"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "问题"},
                        {"role": "assistant", "content": "这是响应内容"}
                    ]
                }
            ]
        }
        content = provider._extract_content(response)
        assert content == "这是响应内容"

    def test_extract_content_empty_choices(self):
        """测试空 choices"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {"choices": []}
        content = provider._extract_content(response)
        assert content == ""

    def test_extract_content_no_choices(self):
        """测试无 choices 字段"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {}
        content = provider._extract_content(response)
        assert content == ""


class TestSearch:
    """搜索功能测试"""

    @patch("melodyi_search.providers.minimax_cn_provider.HttpClient")
    def test_search_success(self, mock_http_client_class):
        """测试成功搜索"""
        # 设置 mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "推荐：[Python官网](https://www.python.org/)"
                    }
                }
            ]
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
        assert len(result.results) >= 1

    @patch("melodyi_search.providers.minimax_cn_provider.HttpClient")
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

        provider = MiniMaxCNProvider(api_key="test-key")
        request = ProviderSearchRequest(query="Python")
        result = provider.search(request)

        assert result.provider == "minimax-cn"
        assert result.error is not None
        assert "401" in result.error

    @patch("melodyi_search.providers.minimax_cn_provider.HttpClient")
    def test_search_with_time_range(self, mock_http_client_class):
        """测试带时间范围的搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "结果"}}]
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

        # 验证时间关键词被注入
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert "今天" in payload["messages"][0]["content"]

    @patch("melodyi_search.providers.minimax_cn_provider.HttpClient")
    def test_search_with_domain_filter(self, mock_http_client_class):
        """测试带域名过滤的搜索"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "推荐：[Python](https://python.org/) 和 [其他](https://other.com/)"
                    }
                }
            ]
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
        for item in result.results:
            assert "python.org" in item.url

    @patch("melodyi_search.providers.minimax_cn_provider.HttpClient")
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


class TestParseResponse:
    """响应解析测试"""

    def test_parse_response_with_results(self):
        """测试解析带结果的响应"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {
            "choices": [
                {
                    "message": {
                        "content": "搜索结果：[Python](https://python.org/)"
                    }
                }
            ]
        }
        results = provider._parse_response(response)
        assert len(results) >= 1

    def test_parse_response_with_domain_filter(self):
        """测试解析响应并应用域名过滤"""
        provider = MiniMaxCNProvider(api_key="test")
        response = {
            "choices": [
                {
                    "message": {
                        "content": "[A](https://allowed.com/) [B](https://blocked.com/)"
                    }
                }
            ]
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
            "choices": [
                {
                    "message": {
                        "content": "[1](https://a.com/) [2](https://b.com/) [3](https://c.com/)"
                    }
                }
            ]
        }
        results = provider._parse_response(response)
        assert len(results) <= 2