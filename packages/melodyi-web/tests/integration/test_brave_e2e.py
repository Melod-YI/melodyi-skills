"""Brave 提供商端到端测试

这些测试需要真实的 API 密钥才能运行。
在没有 API 密钥的情况下会被跳过。

注意：Brave 不支持域名过滤（site: 操作符不可靠），因此不测试域名过滤功能。

运行方式:
    export BRAVE_API_KEY=your_api_key
    pytest tests/integration/test_brave_e2e.py -v
"""

import os
import pytest

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest


# 从环境变量获取 API 密钥
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY")


@pytest.fixture
def provider():
    """创建 Brave 提供商实例"""
    if not BRAVE_API_KEY:
        pytest.skip("BRAVE_API_KEY 环境变量未设置")
    return BraveProvider(
        api_key=BRAVE_API_KEY,
        timeout_ms=30000,
    )


@pytest.mark.skipif(not BRAVE_API_KEY, reason="BRAVE_API_KEY 环境变量未设置")
class TestBraveE2E:
    """Brave 端到端测试"""

    def test_basic_search(self, provider):
        """测试基本搜索功能"""
        request = ProviderSearchRequest(
            query="Python programming",
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "brave"
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

        assert result.provider == "brave"
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

        assert result.provider == "brave"
        assert result.error is None
        print(f"\n时间范围（week）搜索响应时间: {result.response_time_ms}ms")

    def test_search_with_time_range_month(self, provider):
        """测试带时间范围（month）的搜索"""
        request = ProviderSearchRequest(
            query="machine learning",
            time_range=TimeRange(range_type="month"),
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "brave"
        assert result.error is None
        print(f"\n时间范围（month）搜索响应时间: {result.response_time_ms}ms")

    def test_search_with_time_range_year(self, provider):
        """测试带时间范围（year）的搜索"""
        request = ProviderSearchRequest(
            query="programming trends",
            time_range=TimeRange(range_type="year"),
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "brave"
        assert result.error is None
        print(f"\n时间范围（year）搜索响应时间: {result.response_time_ms}ms")

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

    def test_search_with_description(self, provider):
        """测试结果包含描述"""
        request = ProviderSearchRequest(
            query="Python programming",
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "brave"
        assert result.error is None

        # 检查是否有结果包含描述
        items_with_description = [r for r in result.results if r.description]
        print(f"\n带描述的结果数量: {len(items_with_description)}")

    def test_multiple_searches(self, provider):
        """测试多次连续搜索"""
        queries = ["Python", "JavaScript", "Rust"]

        for query in queries:
            request = ProviderSearchRequest(query=query, max_results=3)
            result = provider.search(request)

            assert result.provider == "brave"
            assert result.error is None
            print(f"\n查询 '{query}' 响应时间: {result.response_time_ms}ms")


@pytest.mark.skipif(not BRAVE_API_KEY, reason="BRAVE_API_KEY 环境变量未设置")
class TestBraveProviderConfig:
    """Brave 提供商配置测试"""

    def test_custom_api_url(self):
        """测试自定义 API 地址"""
        provider = BraveProvider(
            api_key=BRAVE_API_KEY,
            api_url="https://custom.api.com/search"
        )
        assert provider.api_url == "https://custom.api.com/search"

    def test_default_values(self):
        """测试默认值"""
        provider = BraveProvider(api_key=BRAVE_API_KEY)

        assert provider.api_url == "https://api.search.brave.com/res/v1/web/search"
        assert provider.timeout_ms == 10000

    def test_provider_capabilities(self):
        """测试提供商能力

        Brave 支持时间过滤，不支持域名过滤。
        """
        provider = BraveProvider(api_key=BRAVE_API_KEY)

        assert provider.supports_time_filter() is True
        assert provider.supports_domain_filter() is False
        assert provider.get_max_results_limit() == 20