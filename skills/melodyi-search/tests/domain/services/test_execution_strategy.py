"""ExecutionStrategy 单元测试"""

import threading
import time
import pytest
from unittest.mock import MagicMock
from melodyi_search.domain.services.execution_strategy import ExecutionStrategy
from melodyi_search.providers.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult
from melodyi_search.domain.models.search_result import SearchResultItem


class MockProvider(BaseProvider):
    """Mock 提供商，用于测试"""

    def __init__(
        self,
        name: str,
        should_succeed: bool = True,
        results: list = None,
        error_message: str = None,
        response_time_ms: int = 100,
        raise_exception: bool = False
    ):
        self._name = name
        self._should_succeed = should_succeed
        self._results = results or []
        self._error_message = error_message
        self._response_time_ms = response_time_ms
        self._raise_exception = raise_exception

    @property
    def name(self) -> str:
        return self._name

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        if self._raise_exception:
            raise Exception(self._error_message or "Provider exception")

        if self._should_succeed:
            return ProviderSearchResult(
                provider=self._name,
                results=self._results,
                response_time_ms=self._response_time_ms,
                raw_response={"mock": True}
            )
        else:
            return ProviderSearchResult(
                provider=self._name,
                results=[],
                response_time_ms=self._response_time_ms,
                error=self._error_message or "Provider failed"
            )

    def supports_time_filter(self) -> bool:
        return True

    def supports_domain_filter(self) -> bool:
        return True

    def get_max_results_limit(self) -> int:
        return 100


def create_search_item(title: str, url: str) -> SearchResultItem:
    """创建测试用的搜索结果项"""
    return SearchResultItem(title=title, url=url, description=f"Description for {title}")


class TestExecutionStrategyNormal:
    """正常模式测试"""

    def test_single_provider_success(self):
        """测试单个提供商成功"""
        strategy = ExecutionStrategy()
        provider = MockProvider(
            name="test-provider",
            should_succeed=True,
            results=[create_search_item("Test 1", "https://example.com/1")]
        )
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_normal([provider], request)

        assert result.is_success()
        assert result.provider == "test-provider"
        assert len(result.results) == 1
        assert result.results[0].title == "Test 1"

    def test_single_provider_failure(self):
        """测试单个提供商失败"""
        strategy = ExecutionStrategy()
        provider = MockProvider(
            name="test-provider",
            should_succeed=False,
            error_message="API error"
        )
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_normal([provider], request)

        assert not result.is_success()
        assert result.error.error_type == "ALL_PROVIDERS_FAILED"
        assert "test-provider" in result.error.original_message
        assert "API error" in result.error.original_message

    def test_fallback_to_second_provider(self):
        """测试回退到第二个提供商"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="provider1", should_succeed=False, error_message="Failed 1"),
            MockProvider(
                name="provider2",
                should_succeed=True,
                results=[create_search_item("Test 2", "https://example.com/2")]
            )
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_normal(providers, request)

        assert result.is_success()
        assert result.provider == "provider2"
        assert len(result.results) == 1

    def test_fallback_through_multiple_providers(self):
        """测试多次回退"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="provider1", should_succeed=False, error_message="Failed 1"),
            MockProvider(name="provider2", should_succeed=False, error_message="Failed 2"),
            MockProvider(
                name="provider3",
                should_succeed=True,
                results=[create_search_item("Test 3", "https://example.com/3")]
            )
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_normal(providers, request)

        assert result.is_success()
        assert result.provider == "provider3"

    def test_all_providers_fail(self):
        """测试所有提供商都失败"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="provider1", should_succeed=False, error_message="Failed 1"),
            MockProvider(name="provider2", should_succeed=False, error_message="Failed 2")
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_normal(providers, request)

        assert not result.is_success()
        assert result.error.error_type == "ALL_PROVIDERS_FAILED"
        assert "provider1" in result.error.original_message
        assert "provider2" in result.error.original_message

    def test_empty_providers_list(self):
        """测试空提供商列表"""
        strategy = ExecutionStrategy()
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_normal([], request)

        assert not result.is_success()
        assert result.error.error_type == "NO_PROVIDERS"

    def test_provider_raises_exception(self):
        """测试提供商抛出异常"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(
                name="exception-provider",
                raise_exception=True,
                error_message="Network error"
            ),
            MockProvider(
                name="backup-provider",
                should_succeed=True,
                results=[create_search_item("Backup", "https://example.com/backup")]
            )
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_normal(providers, request)

        assert result.is_success()
        assert result.provider == "backup-provider"

    def test_all_providers_raise_exception(self):
        """测试所有提供商都抛出异常"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="provider1", raise_exception=True, error_message="Error 1"),
            MockProvider(name="provider2", raise_exception=True, error_message="Error 2")
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_normal(providers, request)

        assert not result.is_success()
        assert result.error.error_type == "ALL_PROVIDERS_FAILED"
        assert "Error 1" in result.error.original_message
        assert "Error 2" in result.error.original_message

    def test_callback_called_on_success(self):
        """测试成功时回调被调用"""
        strategy = ExecutionStrategy()
        provider = MockProvider(
            name="test-provider",
            should_succeed=True,
            results=[create_search_item("Test", "https://example.com")]
        )
        request = ProviderSearchRequest(query="test query")
        callback_results = []

        def callback(result):
            callback_results.append(result)

        strategy.execute_normal([provider], request, on_provider_complete=callback)

        assert len(callback_results) == 1
        assert callback_results[0].provider == "test-provider"

    def test_callback_called_on_failure(self):
        """测试失败时回调也被调用"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="provider1", should_succeed=False),
            MockProvider(name="provider2", should_succeed=True, results=[create_search_item("Test", "https://example.com")])
        ]
        request = ProviderSearchRequest(query="test query")
        callback_results = []

        def callback(result):
            callback_results.append(result)

        strategy.execute_normal(providers, request, on_provider_complete=callback)

        # 两个提供商都应该调用回调
        assert len(callback_results) == 2


class TestExecutionStrategyComparison:
    """比对模式测试"""

    def test_first_provider_returns_immediately(self):
        """测试第一个提供商立即返回"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(
                name="first-provider",
                should_succeed=True,
                results=[create_search_item("First", "https://example.com/first")],
                response_time_ms=50
            ),
            MockProvider(
                name="second-provider",
                should_succeed=True,
                results=[create_search_item("Second", "https://example.com/second")],
                response_time_ms=100
            )
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_comparison(providers, request)

        assert result.is_success()
        assert result.provider == "first-provider"
        assert len(result.results) == 1
        assert result.results[0].title == "First"

    def test_first_provider_fails(self):
        """测试第一个提供商失败"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(
                name="first-provider",
                should_succeed=False,
                error_message="First failed"
            ),
            MockProvider(
                name="second-provider",
                should_succeed=True
            )
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_comparison(providers, request)

        # 比对模式始终返回第一个提供商的结果（即使失败）
        assert not result.is_success()
        assert result.provider == "first-provider"
        assert result.error.error_type == "PROVIDER_ERROR"

    def test_empty_providers_list_comparison(self):
        """测试比对模式空提供商列表"""
        strategy = ExecutionStrategy()
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_comparison([], request)

        assert not result.is_success()
        assert result.error.error_type == "NO_PROVIDERS"

    def test_single_provider_comparison(self):
        """测试比对模式只有一个提供商"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(
                name="only-provider",
                should_succeed=True,
                results=[create_search_item("Only", "https://example.com/only")]
            )
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_comparison(providers, request)

        assert result.is_success()
        assert result.provider == "only-provider"

    def test_comparison_log_included(self):
        """测试比对日志包含在结果中"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="first", should_succeed=True),
            MockProvider(name="second", should_succeed=True),
            MockProvider(name="third", should_succeed=True)
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_comparison(providers, request)

        assert result.comparison_log is not None
        assert result.comparison_log["mode"] == "comparison"
        assert result.comparison_log["first_provider"] == "first"
        assert "second" in result.comparison_log["background_providers"]
        assert "third" in result.comparison_log["background_providers"]

    def test_background_providers_execute(self):
        """测试后台提供商被执行"""
        strategy = ExecutionStrategy()
        executed_providers = []

        class TrackingMockProvider(MockProvider):
            def search(self, request):
                executed_providers.append(self._name)
                return super().search(request)

        providers = [
            TrackingMockProvider(name="first", should_succeed=True, response_time_ms=10),
            TrackingMockProvider(name="second", should_succeed=True, response_time_ms=10),
            TrackingMockProvider(name="third", should_succeed=True, response_time_ms=10)
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_comparison(providers, request)

        # 第一个提供商应该立即执行
        assert "first" in executed_providers

        # 等待后台线程完成
        time.sleep(0.2)

        # 所有提供商都应该被执行
        assert "second" in executed_providers
        assert "third" in executed_providers

    def test_comparison_results_tracking(self):
        """测试比对结果追踪"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="first", should_succeed=True, response_time_ms=50),
            MockProvider(name="second", should_succeed=True, response_time_ms=100)
        ]
        request = ProviderSearchRequest(query="test query")

        strategy.execute_comparison(providers, request)

        # 等待后台线程完成
        time.sleep(0.2)

        results = strategy.get_comparison_results()
        assert "first" in results
        assert "second" in results
        assert results["first"]["status"] == "success"
        assert results["second"]["status"] == "success"

    def test_callback_called_for_first_provider(self):
        """测试比对模式下第一个提供商调用回调"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(
                name="first-provider",
                should_succeed=True,
                results=[create_search_item("First", "https://example.com")]
            )
        ]
        request = ProviderSearchRequest(query="test query")
        callback_results = []

        def callback(result):
            callback_results.append(result)

        strategy.execute_comparison(providers, request, on_provider_complete=callback)

        assert len(callback_results) == 1
        assert callback_results[0].provider == "first-provider"

    def test_callback_called_for_background_providers(self):
        """测试比对模式下后台提供商也调用回调"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="first", should_succeed=True, response_time_ms=10),
            MockProvider(name="second", should_succeed=True, response_time_ms=10),
            MockProvider(name="third", should_succeed=True, response_time_ms=10)
        ]
        request = ProviderSearchRequest(query="test query")
        callback_results = []
        callback_lock = threading.Lock()

        def callback(result):
            with callback_lock:
                callback_results.append(result)

        strategy.execute_comparison(providers, request, on_provider_complete=callback)

        # 等待后台线程完成
        time.sleep(0.3)

        with callback_lock:
            assert len(callback_results) == 3

    def test_background_provider_exception_handling(self):
        """测试后台提供商异常处理"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="first", should_succeed=True),
            MockProvider(name="second", raise_exception=True, error_message="Background error"),
            MockProvider(name="third", should_succeed=True)
        ]
        request = ProviderSearchRequest(query="test query")

        # 不应该抛出异常
        result = strategy.execute_comparison(providers, request)

        assert result.is_success()

        # 等待后台线程完成
        time.sleep(0.2)

        # 比对结果应该记录异常
        results = strategy.get_comparison_results()
        assert "second" in results
        assert results["second"]["status"] == "exception"


class TestExecutionStrategyResponseTime:
    """响应时间测试"""

    def test_response_time_preserved(self):
        """测试响应时间被保留"""
        strategy = ExecutionStrategy()
        provider = MockProvider(
            name="test-provider",
            should_succeed=True,
            response_time_ms=250
        )
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_normal([provider], request)

        assert result.response_time_ms == 250

    def test_response_time_comparison_mode(self):
        """测试比对模式响应时间"""
        strategy = ExecutionStrategy()
        provider = MockProvider(
            name="test-provider",
            should_succeed=True,
            response_time_ms=300
        )
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_comparison([provider], request)

        assert result.response_time_ms == 300


class TestExecutionStrategyResultConversion:
    """结果转换测试"""

    def test_successful_result_conversion(self):
        """测试成功结果转换"""
        strategy = ExecutionStrategy()
        items = [
            create_search_item("Test 1", "https://example.com/1"),
            create_search_item("Test 2", "https://example.com/2")
        ]
        provider = MockProvider(name="test", should_succeed=True, results=items)
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_normal([provider], request)

        assert result.is_success()
        assert result.error is None
        assert len(result.results) == 2

    def test_failed_result_conversion(self):
        """测试失败结果转换"""
        strategy = ExecutionStrategy()
        provider = MockProvider(
            name="test",
            should_succeed=False,
            error_message="Custom error message"
        )
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_normal([provider], request)

        assert not result.is_success()
        # 单个提供商失败时，返回 ALL_PROVIDERS_FAILED
        assert result.error.error_type == "ALL_PROVIDERS_FAILED"

    def test_comparison_mode_returns_first_provider_only(self):
        """测试比对模式只返回第一个提供商结果"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(
                name="first",
                should_succeed=True,
                results=[create_search_item("First", "https://example.com/first")]
            ),
            MockProvider(
                name="second",
                should_succeed=True,
                results=[create_search_item("Second", "https://example.com/second")]
            )
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_comparison(providers, request)

        assert len(result.results) == 1
        assert result.results[0].title == "First"