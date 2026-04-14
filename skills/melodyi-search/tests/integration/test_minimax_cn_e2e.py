"""MiniMax-CN 提供商端到端测试

这些测试需要真实的 API 密钥才能运行。
在没有 API 密钥的情况下会被跳过。

运行方式:
    export MINIMAX_API_KEY=your_api_key
    pytest tests/integration/test_minimax_cn_e2e.py -v
"""

import os
import pytest

from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.providers.minimax_cn_provider import MiniMaxCNProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest


# 从环境变量获取 API 密钥
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY")


@pytest.fixture
def provider():
    """创建 MiniMax-CN 提供商实例"""
    if not MINIMAX_API_KEY:
        pytest.skip("MINIMAX_API_KEY 环境变量未设置")
    return MiniMaxCNProvider(
        api_key=MINIMAX_API_KEY,
        timeout_ms=30000,
        max_results=5
    )


@pytest.mark.skipif(not MINIMAX_API_KEY, reason="MINIMAX_API_KEY 环境变量未设置")
class TestMiniMaxCNE2E:
    """MiniMax-CN 端到端测试"""

    def test_basic_search(self, provider):
        """测试基本搜索功能"""
        request = ProviderSearchRequest(
            query="Python 编程",
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "minimax-cn"
        assert result.error is None
        assert result.response_time_ms > 0
        print(f"\n响应时间: {result.response_time_ms}ms")
        print(f"结果数量: {len(result.results)}")

    def test_search_with_time_range_day(self, provider):
        """测试带时间范围（今天）的搜索"""
        request = ProviderSearchRequest(
            query="科技新闻",
            time_range=TimeRange(range_type="day"),
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "minimax-cn"
        assert result.error is None
        print(f"\n时间范围搜索响应时间: {result.response_time_ms}ms")

    def test_search_with_time_range_week(self, provider):
        """测试带时间范围（本周）的搜索"""
        request = ProviderSearchRequest(
            query="AI 最新动态",
            time_range=TimeRange(range_type="week"),
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "minimax-cn"
        assert result.error is None

    def test_search_with_include_domains(self, provider):
        """测试包含域名过滤"""
        request = ProviderSearchRequest(
            query="Python 教程",
            include_domains=["python.org"],
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "minimax-cn"
        # 注意：由于 MiniMax 不支持原生域名过滤，结果可能不包含指定域名
        # 这是预期行为，域名过滤是后过滤
        print(f"\n包含域名过滤结果数量: {len(result.results)}")

    def test_search_with_exclude_domains(self, provider):
        """测试排除域名过滤"""
        request = ProviderSearchRequest(
            query="编程教程",
            exclude_domains=["github.com"],
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "minimax-cn"
        # 验证结果中不包含被排除的域名
        for item in result.results:
            assert "github.com" not in item.url.lower()
        print(f"\n排除域名过滤结果数量: {len(result.results)}")

    def test_search_response_time(self, provider):
        """测试响应时间在合理范围内"""
        request = ProviderSearchRequest(
            query="测试查询",
            max_results=3
        )
        result = provider.search(request)

        assert result.response_time_ms > 0
        # 响应时间应小于超时时间
        assert result.response_time_ms < provider.timeout_ms
        print(f"\n响应时间: {result.response_time_ms}ms")

    def test_multiple_concurrent_searches(self, provider):
        """测试多次连续搜索"""
        queries = ["Python", "Java", "JavaScript"]

        for query in queries:
            request = ProviderSearchRequest(query=query, max_results=3)
            result = provider.search(request)

            assert result.provider == "minimax-cn"
            assert result.error is None
            print(f"\n查询 '{query}' 响应时间: {result.response_time_ms}ms")


@pytest.mark.skipif(not MINIMAX_API_KEY, reason="MINIMAX_API_KEY 环境变量未设置")
class TestMiniMaxCNProviderConfig:
    """MiniMax-CN 提供商配置测试"""

    def test_custom_api_host(self):
        """测试自定义 API 地址"""
        provider = MiniMaxCNProvider(
            api_key=MINIMAX_API_KEY,
            api_host="https://custom.api.com"
        )
        assert provider.api_host == "https://custom.api.com"

    def test_default_values(self):
        """测试默认值"""
        provider = MiniMaxCNProvider(api_key=MINIMAX_API_KEY)

        assert provider.api_host == "https://api.minimaxi.com"
        assert provider.timeout_ms == 10000
        assert provider.max_results == 10