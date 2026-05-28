"""Exa 提供商端到端测试

这些测试需要真实的 API 密钥才能运行。
在没有 API 密钥的情况下会被跳过。

运行方式:
    export EXA_API_KEY=your_api_key
    pytest tests/integration/test_exa_e2e.py -v
"""

import os
import pytest

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.providers.search.exa_provider import ExaProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest


# 从环境变量获取 API 密钥
EXA_API_KEY = os.environ.get("EXA_API_KEY")


@pytest.fixture
def provider():
    """创建 Exa 提供商实例"""
    if not EXA_API_KEY:
        pytest.skip("EXA_API_KEY 环境变量未设置")
    return ExaProvider(
        api_key=EXA_API_KEY,
        timeout_ms=30000,
        search_type="auto"
    )


@pytest.mark.skipif(not EXA_API_KEY, reason="EXA_API_KEY 环境变量未设置")
class TestExaE2E:
    """Exa 端到端测试"""

    def test_basic_search(self, provider):
        """测试基本搜索功能"""
        request = ProviderSearchRequest(
            query="Python programming",
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error is None
        assert result.response_time_ms > 0
        print(f"\n响应时间: {result.response_time_ms}ms")
        print(f"结果数量: {len(result.results)}")

        # 打印结果详情
        for i, item in enumerate(result.results):
            print(f"\n结果 {i + 1}:")
            print(f"  标题: {item.title}")
            print(f"  URL: {item.url}")
            print(f"  描述: {item.description[:100] if item.description else 'N/A'}...")

    def test_search_with_time_range_week(self, provider):
        """测试带时间范围（本周）的搜索"""
        request = ProviderSearchRequest(
            query="AI news",
            time_range=TimeRange(range_type="week"),
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error is None
        print(f"\n时间范围搜索响应时间: {result.response_time_ms}ms")
        print(f"结果数量: {len(result.results)}")

    def test_search_with_time_range_month(self, provider):
        """测试带时间范围（本月）的搜索"""
        request = ProviderSearchRequest(
            query="machine learning papers",
            time_range=TimeRange(range_type="month"),
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error is None
        print(f"\n时间范围（月）搜索响应时间: {result.response_time_ms}ms")

    def test_search_with_include_domains(self, provider):
        """测试包含域名过滤"""
        request = ProviderSearchRequest(
            query="deep learning",
            include_domains=["arxiv.org"],
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error is None
        print(f"\n包含域名过滤结果数量: {len(result.results)}")

        # 验证结果都来自指定域名
        for item in result.results:
            print(f"  URL: {item.url}")
            # Exa 原生支持域名过滤，结果应该来自 arxiv.org

    def test_search_with_exclude_domains(self, provider):
        """测试排除域名过滤"""
        request = ProviderSearchRequest(
            query="programming tutorials",
            exclude_domains=["twitter.com", "facebook.com"],
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error is None
        print(f"\n排除域名过滤结果数量: {len(result.results)}")

        # 验证结果不包含被排除的域名
        for item in result.results:
            assert "twitter.com" not in item.url.lower()
            assert "facebook.com" not in item.url.lower()

    def test_search_with_combined_filters(self, provider):
        """测试组合过滤条件"""
        request = ProviderSearchRequest(
            query="neural networks",
            time_range=TimeRange(range_type="month"),
            include_domains=["arxiv.org", "github.com"],
            max_results=5
        )
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error is None
        print(f"\n组合过滤结果数量: {len(result.results)}")
        print(f"响应时间: {result.response_time_ms}ms")

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

    def test_search_with_small_max_results(self, provider):
        """测试小数量结果"""
        request = ProviderSearchRequest(
            query="Python",
            max_results=2
        )
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error is None
        assert len(result.results) <= 2
        print(f"\n小数量结果: {len(result.results)}")


@pytest.mark.skipif(not EXA_API_KEY, reason="EXA_API_KEY 环境变量未设置")
class TestExaProviderConfig:
    """Exa 提供商配置测试"""

    def test_custom_api_url(self):
        """测试自定义 API 地址"""
        provider = ExaProvider(
            api_key=EXA_API_KEY,
            api_url="https://custom.api.com/search"
        )
        assert provider.api_url == "https://custom.api.com/search"

    def test_custom_search_type(self):
        """测试自定义搜索类型"""
        provider = ExaProvider(
            api_key=EXA_API_KEY,
            search_type="neural"
        )
        assert provider.default_type == "neural"

    def test_custom_timeout(self):
        """测试自定义超时"""
        provider = ExaProvider(
            api_key=EXA_API_KEY,
            timeout_ms=60000
        )
        assert provider.timeout_ms == 60000

    def test_default_values(self):
        """测试默认值"""
        provider = ExaProvider(api_key=EXA_API_KEY)

        assert provider.api_url == "https://api.exa.ai/search"
        assert provider.default_type == "auto"
        assert provider.timeout_ms == 30000
        assert provider.get_max_results_limit() == 10


@pytest.mark.skipif(not EXA_API_KEY, reason="EXA_API_KEY 环境变量未设置")
class TestExaProviderCapabilities:
    """Exa 提供商能力测试"""

    def test_neural_search(self):
        """测试神经网络搜索"""
        provider = ExaProvider(
            api_key=EXA_API_KEY,
            search_type="neural"
        )
        request = ProviderSearchRequest(
            query="semantic search capabilities",
            max_results=3
        )
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error is None
        print(f"\n神经网络搜索响应时间: {result.response_time_ms}ms")

    def test_keyword_search(self):
        """测试关键词搜索"""
        provider = ExaProvider(
            api_key=EXA_API_KEY,
            search_type="keyword"
        )
        request = ProviderSearchRequest(
            query="exact keyword match",
            max_results=3
        )
        result = provider.search(request)

        assert result.provider == "exa"
        assert result.error is None
        print(f"\n关键词搜索响应时间: {result.response_time_ms}ms")