"""FetchExecutionStrategy 测试"""

import pytest
from unittest.mock import Mock
from melodyi_web.domain.services.fetch_executor import FetchExecutionStrategy
from melodyi_web.providers.fetch.base_fetch_provider import (
    BaseFetchProvider,
    ProviderFetchRequest,
    ProviderFetchResult,
)


class MockFetchProvider(BaseFetchProvider):
    """Mock Fetch 供应商，用于测试"""

    def __init__(
        self,
        name: str,
        should_succeed: bool = True,
        title: str = None,
        content: str = "",
        error_message: str = None,
        response_time_ms: int = 100,
        raise_exception: bool = False
    ):
        self._name = name
        self._should_succeed = should_succeed
        self._title = title
        self._content = content
        self._error_message = error_message
        self._response_time_ms = response_time_ms
        self._raise_exception = raise_exception

    @property
    def name(self) -> str:
        return self._name

    def fetch(self, request: ProviderFetchRequest) -> ProviderFetchResult:
        if self._raise_exception:
            raise Exception(self._error_message or "Provider exception")

        if self._should_succeed:
            return ProviderFetchResult(
                provider=self._name,
                url=request.url,
                title=self._title,
                content=self._content,
                response_time_ms=self._response_time_ms,
            )
        else:
            return ProviderFetchResult(
                provider=self._name,
                url=request.url,
                content="",
                response_time_ms=self._response_time_ms,
                error=self._error_message or "Provider failed"
            )

    def supports_js_render(self) -> bool:
        return False

    def get_output_format(self) -> str:
        return "markdown"


class TestFetchExecutionStrategyNormal:
    """Fetch 正常模式测试"""

    def test_execute_normal_no_providers(self):
        """测试无供应商情况"""
        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([], request)

        assert result.error is not None
        assert result.error.error_type == "NO_PROVIDERS"

    def test_execute_normal_single_provider_success(self):
        """测试单供应商成功"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            title="Test Title",
            content="Test content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider], request)

        assert result.error is None
        assert result.provider == "test-provider"
        assert result.content == "Test content"
        assert result.title == "Test Title"

    def test_execute_normal_provider_fallback(self):
        """测试供应商失败回退"""
        mock_provider1 = MockFetchProvider(
            name="provider1",
            should_succeed=False,
            error_message="Connection failed"
        )

        mock_provider2 = MockFetchProvider(
            name="provider2",
            should_succeed=True,
            title="Success Title",
            content="Success content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider1, mock_provider2], request)

        assert result.error is None
        assert result.provider == "provider2"
        assert result.content == "Success content"

    def test_execute_normal_all_providers_fail(self):
        """测试所有供应商失败"""
        mock_provider = MockFetchProvider(
            name="fail-provider",
            should_succeed=False,
            error_message="Failed"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider], request)

        assert result.error is not None
        assert result.error.error_type == "ALL_PROVIDERS_FAILED"

    def test_execute_normal_provider_exception_fallback(self):
        """测试供应商异常时回退"""
        mock_provider1 = MockFetchProvider(
            name="exception-provider",
            raise_exception=True,
            error_message="Network error"
        )

        mock_provider2 = MockFetchProvider(
            name="backup-provider",
            should_succeed=True,
            content="Backup content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider1, mock_provider2], request)

        assert result.error is None
        assert result.provider == "backup-provider"
        assert result.content == "Backup content"

    def test_execute_normal_all_providers_raise_exception(self):
        """测试所有供应商都抛出异常"""
        mock_provider1 = MockFetchProvider(
            name="provider1",
            raise_exception=True,
            error_message="Error 1"
        )

        mock_provider2 = MockFetchProvider(
            name="provider2",
            raise_exception=True,
            error_message="Error 2"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider1, mock_provider2], request)

        assert result.error is not None
        assert result.error.error_type == "ALL_PROVIDERS_FAILED"
        assert "Error 1" in result.error.original_message
        assert "Error 2" in result.error.original_message

    def test_execute_normal_response_time_preserved(self):
        """测试响应时间被保留"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            content="Test content",
            response_time_ms=250
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider], request)

        assert result.response_time_ms == 250

    def test_execute_normal_url_preserved(self):
        """测试 URL 被保留"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            content="Test content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com/page")
        result = strategy.execute_normal([mock_provider], request)

        assert result.url == "https://example.com/page"

    def test_execute_normal_metadata_preserved(self):
        """测试元数据被保留"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            content="Test content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider], request)

        # metadata 应该存在（可能为空）
        assert hasattr(result, 'metadata')
        assert isinstance(result.metadata, dict)

    def test_execute_normal_callback_on_success(self):
        """测试成功时回调被调用"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            content="Test content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        callback_results = []

        def callback(result):
            callback_results.append(result)

        result = strategy.execute_normal([mock_provider], request, on_provider_complete=callback)

        assert len(callback_results) == 1
        assert callback_results[0].provider == "test-provider"

    def test_execute_normal_callback_on_failure(self):
        """测试失败时回调也被调用"""
        mock_provider1 = MockFetchProvider(
            name="provider1",
            should_succeed=False,
            error_message="Failed"
        )

        mock_provider2 = MockFetchProvider(
            name="provider2",
            should_succeed=True,
            content="Success content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        callback_results = []

        def callback(result):
            callback_results.append(result)

        result = strategy.execute_normal([mock_provider1, mock_provider2], request, on_provider_complete=callback)

        # 两个供应商都应该调用回调
        assert len(callback_results) == 2
        assert callback_results[0].provider == "provider1"
        assert callback_results[1].provider == "provider2"

    def test_execute_normal_multiple_fallback(self):
        """测试多次回退"""
        mock_provider1 = MockFetchProvider(
            name="provider1",
            should_succeed=False,
            error_message="Failed 1"
        )

        mock_provider2 = MockFetchProvider(
            name="provider2",
            should_succeed=False,
            error_message="Failed 2"
        )

        mock_provider3 = MockFetchProvider(
            name="provider3",
            should_succeed=True,
            content="Success content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider1, mock_provider2, mock_provider3], request)

        assert result.error is None
        assert result.provider == "provider3"
        assert result.content == "Success content"


class TestFetchExecutionStrategyResultConversion:
    """结果转换测试"""

    def test_successful_result_conversion(self):
        """测试成功结果转换"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            title="Test Title",
            content="Test content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider], request)

        assert result.is_success()
        assert result.error is None
        assert result.title == "Test Title"
        assert result.content == "Test content"

    def test_failed_result_conversion(self):
        """测试失败结果转换"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=False,
            error_message="Custom error message"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider], request)

        assert not result.is_success()
        # 单个供应商失败时，返回 ALL_PROVIDERS_FAILED
        assert result.error.error_type == "ALL_PROVIDERS_FAILED"

    def test_empty_content_is_success(self):
        """测试空内容也算成功"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            content=""
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider], request)

        assert result.is_success()
        assert not result.has_content()

    def test_has_content_method(self):
        """测试 has_content 方法"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            content="Some content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        result = strategy.execute_normal([mock_provider], request)

        assert result.is_success()
        assert result.has_content()


class TestFetchExecutionStrategyComparison:
    """Fetch 对比模式测试"""

    def test_execute_comparison_no_providers(self):
        """测试无供应商情况"""
        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        mock_recorder = Mock()
        result = strategy.execute_comparison([], request, mock_recorder)

        assert result.error is not None
        assert result.error.error_type == "NO_PROVIDERS"

    def test_execute_comparison_single_provider_success(self):
        """测试单供应商成功"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            title="Test Title",
            content="Test content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        mock_recorder = Mock()
        mock_recorder.generate_session_id.return_value = "20260513-120000-abcd"

        result = strategy.execute_comparison([mock_provider], request, mock_recorder)

        assert result.error is None
        assert result.provider == "test-provider"
        assert result.content == "Test content"
        assert result.title == "Test Title"
        assert result.session_id == "20260513-120000-abcd"
        # 验证 recorder 被调用
        mock_recorder.write_fetch_session.assert_called_once()
        mock_recorder.write_fetch_provider_result.assert_called_once()

    def test_execute_comparison_single_provider_failure(self):
        """测试单供应商失败"""
        mock_provider = MockFetchProvider(
            name="fail-provider",
            should_succeed=False,
            error_message="Provider failed"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        mock_recorder = Mock()
        mock_recorder.generate_session_id.return_value = "20260513-120000-abcd"

        result = strategy.execute_comparison([mock_provider], request, mock_recorder)

        assert result.error is not None
        assert result.session_id == "20260513-120000-abcd"
        # 验证 recorder 被调用
        mock_recorder.write_fetch_session.assert_called_once()
        mock_recorder.write_fetch_provider_result.assert_called_once()

    def test_execute_comparison_multiple_providers(self):
        """测试多供应商对比执行"""
        mock_provider1 = MockFetchProvider(
            name="provider1",
            should_succeed=True,
            title="Title 1",
            content="Content 1",
            response_time_ms=100
        )

        mock_provider2 = MockFetchProvider(
            name="provider2",
            should_succeed=True,
            title="Title 2",
            content="Content 2",
            response_time_ms=200
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        mock_recorder = Mock()
        # 配置 generate_session_id 返回正确格式
        mock_recorder.generate_session_id.return_value = "20260513-120000-abcd"

        result = strategy.execute_comparison([mock_provider1, mock_provider2], request, mock_recorder)

        # 返回第一个供应商结果
        assert result.error is None
        assert result.provider == "provider1"
        assert result.session_id == "20260513-120000-abcd"

        # 验证 recorder 被调用
        mock_recorder.write_fetch_session.assert_called_once()
        # 第一个供应商结果立即写入，后台供应商也会写入
        assert mock_recorder.write_fetch_provider_result.call_count >= 1

    def test_execute_comparison_session_id_format(self):
        """测试 session_id 格式"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            content="Test content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        mock_recorder = Mock()
        # 配置 generate_session_id 返回正确格式
        mock_recorder.generate_session_id.return_value = "20260513-120000-abcd"

        result = strategy.execute_comparison([mock_provider], request, mock_recorder)

        # session_id 应该存在且格式正确
        assert result.session_id is not None
        # 验证格式: YYYYMMDD-HHMMSS-XXXX
        import re
        assert re.match(r"\d{8}-\d{6}-[0-9a-f]{4}", result.session_id)

    def test_execute_comparison_url_recorded(self):
        """测试 URL 被正确记录"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            content="Test content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com/test/page")
        mock_recorder = Mock()
        mock_recorder.generate_session_id.return_value = "20260513-120000-abcd"

        result = strategy.execute_comparison([mock_provider], request, mock_recorder)

        assert result.url == "https://example.com/test/page"
        # 验证 write_fetch_session 被调用时传入了正确的 request
        call_args = mock_recorder.write_fetch_session.call_args
        assert call_args[0][1].url == "https://example.com/test/page"

    def test_execute_comparison_callback_on_first_provider(self):
        """测试回调在第一个供应商完成时被调用"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            content="Test content"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        mock_recorder = Mock()
        mock_recorder.generate_session_id.return_value = "20260513-120000-abcd"

        callback_results = []

        def callback(result):
            callback_results.append(result)

        result = strategy.execute_comparison([mock_provider], request, mock_recorder, callback)

        assert len(callback_results) == 1
        assert callback_results[0].provider == "test-provider"

    def test_execute_comparison_response_time_preserved(self):
        """测试响应时间被保留"""
        mock_provider = MockFetchProvider(
            name="test-provider",
            should_succeed=True,
            content="Test content",
            response_time_ms=350
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        mock_recorder = Mock()
        mock_recorder.generate_session_id.return_value = "20260513-120000-abcd"

        result = strategy.execute_comparison([mock_provider], request, mock_recorder)

        assert result.response_time_ms == 350

    def test_execute_comparison_provider_exception(self):
        """测试第一个供应商异常情况"""
        mock_provider = MockFetchProvider(
            name="exception-provider",
            raise_exception=True,
            error_message="Network timeout"
        )

        strategy = FetchExecutionStrategy()
        request = ProviderFetchRequest(url="https://example.com")
        mock_recorder = Mock()
        mock_recorder.generate_session_id.return_value = "20260513-120000-abcd"

        result = strategy.execute_comparison([mock_provider], request, mock_recorder)

        assert result.error is not None
        assert result.error.error_type == "FIRST_PROVIDER_EXCEPTION"
        assert "Network timeout" in result.error.original_message
        assert result.session_id == "20260513-120000-abcd"