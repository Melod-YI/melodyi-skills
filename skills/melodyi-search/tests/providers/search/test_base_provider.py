"""BaseProvider 抽象基类测试"""

import pytest
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)


class MockProvider(BaseProvider):
    """模拟提供商用于测试"""

    @property
    def name(self) -> str:
        return "mock"

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        return ProviderSearchResult(
            provider="mock",
            results=[],
            response_time_ms=100
        )

    def supports_time_filter(self) -> bool:
        return True

    def supports_domain_filter(self) -> bool:
        return True

    def get_max_results_limit(self) -> int:
        return 50


class TestProviderSearchRequest:
    """ProviderSearchRequest 测试"""

    def test_create_with_query(self):
        """测试创建请求"""
        request = ProviderSearchRequest(query="test query")
        assert request.query == "test query"
        assert request.max_results == 10
        assert request.time_range is None

    def test_native_params(self):
        """测试原生参数"""
        request = ProviderSearchRequest(
            query="test",
            native_params={"depth": "advanced"}
        )
        assert request.native_params == {"depth": "advanced"}


class TestBaseProvider:
    """BaseProvider 测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = MockProvider()
        assert provider.name == "mock"

    def test_supports_time_filter(self):
        """测试时间过滤支持"""
        provider = MockProvider()
        assert provider.supports_time_filter() is True

    def test_supports_domain_filter(self):
        """测试域名过滤支持"""
        provider = MockProvider()
        assert provider.supports_domain_filter() is True

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = MockProvider()
        assert provider.get_max_results_limit() == 50

    def test_cannot_instantiate_abstract_class(self):
        """测试不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            BaseProvider()