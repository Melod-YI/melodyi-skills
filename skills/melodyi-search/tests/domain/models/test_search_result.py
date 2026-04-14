"""搜索结果模型测试"""

import pytest
from datetime import datetime
from melodyi_search.domain.models.search_result import SearchResultItem, UnifiedSearchResult, SearchError


class TestSearchResultItem:
    """SearchResultItem 测试类"""

    def test_create_with_required_fields(self):
        """测试使用必填字段创建"""
        item = SearchResultItem(
            title="Python Tutorial",
            url="https://example.com/python",
            description="Learn Python basics"
        )
        assert item.title == "Python Tutorial"
        assert item.url == "https://example.com/python"
        assert item.description == "Learn Python basics"
        assert item.published_date is None
        assert item.source_domain == "example.com"
        assert item.provider_extra is None

    def test_create_with_all_fields(self):
        """测试使用所有字段创建"""
        published = datetime(2026, 1, 15)
        item = SearchResultItem(
            title="AI News",
            url="https://github.com/repo",
            description="Latest AI developments",
            published_date=published,
            source_domain="github.com",
            provider_extra={"raw": "data"}
        )
        assert item.title == "AI News"
        assert item.url == "https://github.com/repo"
        assert item.published_date == published
        assert item.source_domain == "github.com"
        assert item.provider_extra == {"raw": "data"}

    def test_source_domain_extracted_from_url(self):
        """测试 source_domain 从 URL 自动提取"""
        item = SearchResultItem(
            title="Test",
            url="https://stackoverflow.com/questions/123",
            description="test"
        )
        assert item.source_domain == "stackoverflow.com"

    def test_url_required(self):
        """测试 url 必填"""
        with pytest.raises(Exception):  # ValidationError
            SearchResultItem(title="Test", description="test")

    def test_title_required(self):
        """测试 title 必填"""
        with pytest.raises(Exception):  # ValidationError
            SearchResultItem(url="https://example.com", description="test")

    def test_description_defaults_to_empty(self):
        """测试 description 默认为空字符串"""
        item = SearchResultItem(
            title="Test",
            url="https://example.com"
        )
        assert item.description == ""


class TestSearchError:
    """SearchError 测试类"""

    def test_create_search_error(self):
        """测试创建搜索错误"""
        error = SearchError(
            error_type="RATE_LIMITED",
            original_message="Too many requests",
            guidance="请等待后重试或切换提供商"
        )
        assert error.error_type == "RATE_LIMITED"
        assert error.original_message == "Too many requests"
        assert error.guidance == "请等待后重试或切换提供商"


class TestUnifiedSearchResult:
    """UnifiedSearchResult 测试类"""

    def test_create_success_result(self):
        """测试创建成功结果"""
        item = SearchResultItem(
            title="Test",
            url="https://example.com",
            description="test"
        )
        result = UnifiedSearchResult(
            provider="minimax-cn",
            response_time_ms=850,
            results=[item]
        )
        assert result.provider == "minimax-cn"
        assert result.response_time_ms == 850
        assert len(result.results) == 1
        assert result.error is None
        assert result.comparison_log is None

    def test_create_error_result(self):
        """测试创建错误结果"""
        error = SearchError(
            error_type="RATE_LIMITED",
            original_message="Too many requests",
            guidance="请等待后重试"
        )
        result = UnifiedSearchResult(
            provider="brave",
            response_time_ms=100,
            results=[],
            error=error
        )
        assert result.error.error_type == "RATE_LIMITED"
        assert result.error.guidance == "请等待后重试"

    def test_results_default_empty_list(self):
        """测试 results 默认为空列表"""
        result = UnifiedSearchResult(
            provider="test",
            response_time_ms=100
        )
        assert result.results == []

    def test_is_success_method(self):
        """测试 is_success 方法"""
        # 成功结果
        result = UnifiedSearchResult(provider="test", response_time_ms=100)
        assert result.is_success() is True

        # 错误结果
        error = SearchError(error_type="ERROR", original_message="msg", guidance="guide")
        result = UnifiedSearchResult(provider="test", response_time_ms=100, error=error)
        assert result.is_success() is False

    def test_has_results_method(self):
        """测试 has_results 方法"""
        # 无结果
        result = UnifiedSearchResult(provider="test", response_time_ms=100)
        assert result.has_results() is False

        # 有结果
        item = SearchResultItem(title="Test", url="https://example.com", description="test")
        result = UnifiedSearchResult(provider="test", response_time_ms=100, results=[item])
        assert result.has_results() is True