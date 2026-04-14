"""搜索结果模型测试"""

import pytest
from datetime import datetime
from melodyi_search.domain.models.search_result import SearchResultItem


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