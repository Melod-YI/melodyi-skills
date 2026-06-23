"""Tavily 提供商端到端测试

这些测试需要真实的 API 密钥才能运行。
在没有 API 密钥的情况下会被跳过。

运行方式:
    export TAVILY_API_KEY=your_api_key
    pytest tests/integration/test_tavily_e2e.py -v
"""

import os
import pytest

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest


# 从环境变量获取 API 密钥
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")


@pytest.fixture
def provider():
    """创建 Tavily 提供商实例"""
    if not TAVILY_API_KEY:
        pytest.skip("TAVILY_API_KEY 环境变量未设置")
    return TavilyProvider(
        api_key=TAVILY_API_KEY,
        timeout_ms=30000,
        search_depth="basic"
    )


@pytest.mark.skipif(not TAVILY_API_KEY, reason="TAVILY_API_KEY 环境变量未设置")
class TestTavilyE2E:
    """Tavily 端到端测试"""

    def test_basic_search(self, provider):
        """测试基本搜索功能"""
        request = ProviderSearchRequest(
            query="Python programming",
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "tavily"
        assert result.error is None
        assert result.response_time_ms > 0
        print(f"\n响应时间: {result.response_time_ms}ms")
        print(f"结果数量: {len(result.results)}")

        # 验证结果格式
        if result.results:
            for item in result.results:
                assert item.title
                assert item.url
                print(f"  - {item.title}: {item.url}")

    def test_search_with_time_range_day(self, provider):
        """测试带时间范围（day）的搜索"""
        request = ProviderSearchRequest(
            query="technology news",
            time_range=TimeRange(range_type="day"),
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "tavily"
        assert result.error is None
        print(f"\n时间范围（day）搜索响应时间: {result.response_time_ms}ms")
        print(f"结果数量: {len(result.results)}")

    def test_search_with_time_range_week(self, provider):
        """测试带时间范围（week）的搜索"""
        request = ProviderSearchRequest(
            query="AI latest developments",
            time_range=TimeRange(range_type="week"),
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "tavily"
        assert result.error is None
        print(f"\n时间范围（week）搜索响应时间: {result.response_time_ms}ms")

    def test_search_with_include_domains(self, provider):
        """测试包含域名过滤"""
        request = ProviderSearchRequest(
            query="Python tutorial",
            include_domains=["python.org"],
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "tavily"
        assert result.error is None
        print(f"\n包含域名过滤结果数量: {len(result.results)}")

        # 验证所有结果都来自指定域名
        for item in result.results:
            assert "python.org" in item.url.lower()
            print(f"  - {item.url}")

    def test_search_with_exclude_domains(self, provider):
        """测试排除域名过滤"""
        request = ProviderSearchRequest(
            query="programming tutorials",
            exclude_domains=["pinterest.com", "quora.com"],
            max_results=10
        )
        result = provider.search(request)

        assert result.provider == "tavily"
        assert result.error is None
        print(f"\n排除域名过滤结果数量: {len(result.results)}")

        # 验证结果中不包含被排除的域名
        for item in result.results:
            assert "pinterest.com" not in item.url.lower()
            assert "quora.com" not in item.url.lower()

    def test_search_with_domain_filter_combined(self, provider):
        """测试组合域名过滤"""
        request = ProviderSearchRequest(
            query="Python documentation",
            include_domains=["docs.python.org", "python.org"],
            exclude_domains=["forum.python.org"],
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "tavily"
        assert result.error is None
        print(f"\n组合域名过滤结果数量: {len(result.results)}")

    def test_search_with_advanced_depth(self):
        """测试高级搜索深度"""
        if not TAVILY_API_KEY:
            pytest.skip("TAVILY_API_KEY 环境变量未设置")

        provider = TavilyProvider(
            api_key=TAVILY_API_KEY,
            search_depth="advanced"
        )
        request = ProviderSearchRequest(
            query="machine learning",
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "tavily"
        assert result.error is None
        print(f"\n高级深度搜索响应时间: {result.response_time_ms}ms")

    def test_search_response_time(self, provider):
        """测试响应时间在合理范围内"""
        request = ProviderSearchRequest(
            query="test query",
            max_results=3
        )
        result = provider.search(request)

        assert result.response_time_ms > 0
        # 响应时间应小于超时时间
        assert result.response_time_ms < provider.timeout_ms
        print(f"\n响应时间: {result.response_time_ms}ms")

    def test_search_with_published_date(self, provider):
        """测试结果包含发布日期"""
        request = ProviderSearchRequest(
            query="news today",
            time_range=TimeRange(range_type="day"),
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "tavily"
        assert result.error is None

        # 检查是否有结果包含发布日期
        items_with_dates = [r for r in result.results if r.published_date]
        print(f"\n带发布日期的结果数量: {len(items_with_dates)}")

    def test_multiple_searches(self, provider):
        """测试多次连续搜索"""
        queries = ["Python", "JavaScript", "Rust"]

        for query in queries:
            request = ProviderSearchRequest(query=query, max_results=3)
            result = provider.search(request)

            assert result.provider == "tavily"
            assert result.error is None
            print(f"\n查询 '{query}' 响应时间: {result.response_time_ms}ms")


@pytest.mark.skipif(not TAVILY_API_KEY, reason="TAVILY_API_KEY 环境变量未设置")
class TestTavilyProviderConfig:
    """Tavily 提供商配置测试"""

    def test_custom_api_url(self):
        """测试自定义 API 地址"""
        provider = TavilyProvider(
            api_key=TAVILY_API_KEY,
            api_url="https://custom.api.com/search"
        )
        assert provider.api_url == "https://custom.api.com/search"

    def test_custom_search_depth(self):
        """测试自定义搜索深度"""
        provider = TavilyProvider(
            api_key=TAVILY_API_KEY,
            search_depth="advanced"
        )
        assert provider.default_depth == "advanced"

    def test_default_values(self):
        """测试默认值"""
        provider = TavilyProvider(api_key=TAVILY_API_KEY)

        assert provider.api_url == "https://api.tavily.com/search"
        assert provider.default_depth == "basic"
        assert provider.timeout_ms == 10000

    def test_provider_capabilities(self):
        """测试提供商能力"""
        provider = TavilyProvider(api_key=TAVILY_API_KEY)

        assert provider.supports_time_filter() is True
        assert provider.supports_domain_filter() is True
        assert provider.get_max_results_limit() == 20