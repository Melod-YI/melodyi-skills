"""ExecutionStrategy 单元测试"""

import os
import tempfile
import threading
import time
import pytest
from unittest.mock import MagicMock, Mock
from melodyi_web.domain.services.execution_strategy import ExecutionStrategy
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
from melodyi_web.providers.search.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult
from melodyi_web.domain.models.search_result import SearchResultItem


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

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        config = DatabaseConfig(database_path=db_path)
        manager = DatabaseManager(config)
        manager.init_database()
        yield manager
        # Cleanup
        try:
            os.unlink(db_path)
        except Exception:
            pass

    @pytest.fixture
    def recorder(self, temp_db):
        """创建 recorder 实例"""
        return ComparisonRecorder(temp_db)

    def test_first_provider_returns_immediately(self, recorder):
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

        result = strategy.execute_comparison(providers, request, recorder)

        assert result.is_success()
        assert result.provider == "first-provider"
        assert len(result.results) == 1
        assert result.results[0].title == "First"

    def test_first_provider_fails(self, recorder):
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

        result = strategy.execute_comparison(providers, request, recorder)

        # 比对模式始终返回第一个提供商的结果（即使失败）
        assert not result.is_success()
        assert result.provider == "first-provider"
        assert result.error.error_type == "PROVIDER_ERROR"

    def test_empty_providers_list_comparison(self, recorder):
        """测试比对模式空提供商列表"""
        strategy = ExecutionStrategy()
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_comparison([], request, recorder)

        assert not result.is_success()
        assert result.error.error_type == "NO_PROVIDERS"

    def test_single_provider_comparison(self, recorder):
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

        result = strategy.execute_comparison(providers, request, recorder)

        assert result.is_success()
        assert result.provider == "only-provider"

    def test_comparison_log_included(self, recorder):
        """测试比对日志包含在结果中"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="first", should_succeed=True),
            MockProvider(name="second", should_succeed=True),
            MockProvider(name="third", should_succeed=True)
        ]
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_comparison(providers, request, recorder)

        assert result.comparison_log is not None
        assert result.comparison_log["mode"] == "comparison"
        assert result.comparison_log["first_provider"] == "first"
        assert "second" in result.comparison_log["background_providers"]
        assert "third" in result.comparison_log["background_providers"]

    def test_background_providers_execute(self, recorder):
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

        result = strategy.execute_comparison(providers, request, recorder)

        # 第一个提供商应该立即执行
        assert "first" in executed_providers

        # 等待后台线程完成
        time.sleep(0.2)

        # 所有提供商都应该被执行
        assert "second" in executed_providers
        assert "third" in executed_providers

    def test_comparison_results_tracking(self, recorder):
        """测试比对结果追踪"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="first", should_succeed=True, response_time_ms=50),
            MockProvider(name="second", should_succeed=True, response_time_ms=100)
        ]
        request = ProviderSearchRequest(query="test query")

        strategy.execute_comparison(providers, request, recorder)

        # 等待后台线程完成
        time.sleep(0.2)

        results = strategy.get_comparison_results()
        assert "first" in results
        assert "second" in results
        assert results["first"]["status"] == "success"
        assert results["second"]["status"] == "success"

    def test_callback_called_for_first_provider(self, recorder):
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

        strategy.execute_comparison(providers, request, recorder, on_provider_complete=callback)

        assert len(callback_results) == 1
        assert callback_results[0].provider == "first-provider"

    def test_callback_called_for_background_providers(self, recorder):
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

        strategy.execute_comparison(providers, request, recorder, on_provider_complete=callback)

        # 等待后台线程完成
        time.sleep(0.3)

        with callback_lock:
            assert len(callback_results) == 3

    def test_background_provider_exception_handling(self, recorder):
        """测试后台提供商异常处理"""
        strategy = ExecutionStrategy()
        providers = [
            MockProvider(name="first", should_succeed=True),
            MockProvider(name="second", raise_exception=True, error_message="Background error"),
            MockProvider(name="third", should_succeed=True)
        ]
        request = ProviderSearchRequest(query="test query")

        # 不应该抛出异常
        result = strategy.execute_comparison(providers, request, recorder)

        assert result.is_success()

        # 等待后台线程完成
        time.sleep(0.2)

        # 比对结果应该记录异常
        results = strategy.get_comparison_results()
        assert "second" in results
        assert results["second"]["status"] == "exception"


class TestExecutionStrategyResponseTime:
    """响应时间测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        config = DatabaseConfig(database_path=db_path)
        manager = DatabaseManager(config)
        manager.init_database()
        yield manager
        # Cleanup
        try:
            os.unlink(db_path)
        except Exception:
            pass

    @pytest.fixture
    def recorder(self, temp_db):
        """创建 recorder 实例"""
        return ComparisonRecorder(temp_db)

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

    def test_response_time_comparison_mode(self, recorder):
        """测试比对模式响应时间"""
        strategy = ExecutionStrategy()
        provider = MockProvider(
            name="test-provider",
            should_succeed=True,
            response_time_ms=300
        )
        request = ProviderSearchRequest(query="test query")

        result = strategy.execute_comparison([provider], request, recorder)

        assert result.response_time_ms == 300


class TestExecutionStrategyResultConversion:
    """结果转换测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        config = DatabaseConfig(database_path=db_path)
        manager = DatabaseManager(config)
        manager.init_database()
        yield manager
        # Cleanup
        try:
            os.unlink(db_path)
        except Exception:
            pass

    @pytest.fixture
    def recorder(self, temp_db):
        """创建 recorder 实例"""
        return ComparisonRecorder(temp_db)

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

    def test_comparison_mode_returns_first_provider_only(self, recorder):
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

        result = strategy.execute_comparison(providers, request, recorder)

        assert len(result.results) == 1
        assert result.results[0].title == "First"


class TestComparisonPersistence:
    """集成测试: Compare 模式持久化 (COMP-02, COMP-06, COMP-07)"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        config = DatabaseConfig(database_path=db_path)
        manager = DatabaseManager(config)
        manager.init_database()
        yield manager
        # Cleanup
        try:
            os.unlink(db_path)
        except Exception:
            pass

    @pytest.fixture
    def recorder(self, temp_db):
        """创建 recorder 实例"""
        return ComparisonRecorder(temp_db)

    @pytest.fixture
    def strategy(self):
        """创建执行策略实例"""
        return ExecutionStrategy()

    def test_execute_comparison_accepts_recorder_parameter(self, strategy, recorder, temp_db):
        """测试 execute_comparison() 接受 recorder 参数"""
        provider = MockProvider(
            name="test_provider",
            should_succeed=True,
            results=[create_search_item("Test", "https://example.com")]
        )
        request = ProviderSearchRequest(query="test", max_results=10)

        result = strategy.execute_comparison(
            providers=[provider],
            request=request,
            recorder=recorder
        )

        # COMP-06: 验证 session_id 存在
        assert result.session_id is not None

    def test_session_written_to_database(self, strategy, recorder, temp_db):
        """测试 session 写入数据库"""
        provider = MockProvider(
            name="test_provider",
            should_succeed=True,
            results=[create_search_item("Test", "https://example.com")]
        )
        request = ProviderSearchRequest(query="test query", max_results=10)

        result = strategy.execute_comparison(
            providers=[provider],
            request=request,
            recorder=recorder
        )

        # 验证数据库写入
        conn = temp_db.get_connection()
        session = conn.execute(
            "SELECT session_id, query FROM comparison_sessions WHERE session_id=?",
            (result.session_id,)
        ).fetchone()
        conn.close()

        assert session is not None
        assert session[1] == "test query"

    def test_first_provider_result_written_to_database(self, strategy, recorder, temp_db):
        """测试第一个供应商结果写入数据库"""
        provider = MockProvider(
            name="provider1",
            should_succeed=True,
            results=[create_search_item("Test", "https://example.com")]
        )
        request = ProviderSearchRequest(query="test", max_results=10)

        result = strategy.execute_comparison(
            providers=[provider],
            request=request,
            recorder=recorder
        )

        # 验证供应商结果写入
        conn = temp_db.get_connection()
        provider_result = conn.execute(
            "SELECT provider, response_time_ms, results_count FROM provider_results WHERE session_id=?",
            (result.session_id,)
        ).fetchone()
        conn.close()

        assert provider_result is not None
        assert provider_result[0] == "provider1"

    def test_daemon_false_thread_wait(self, strategy, recorder, temp_db):
        """测试 daemon=False + thread.join(timeout=10) 确保写入"""
        provider1 = MockProvider(
            name="provider1",
            should_succeed=True,
            results=[create_search_item("P1", "https://p1.com")],
            response_time_ms=50
        )
        provider2 = MockProvider(
            name="provider2",
            should_succeed=True,
            results=[create_search_item("P2", "https://p2.com")],
            response_time_ms=50
        )

        request = ProviderSearchRequest(query="test", max_results=10)
        result = strategy.execute_comparison(
            providers=[provider1, provider2],
            request=request,
            recorder=recorder
        )

        # 等待后台线程完成（strategy 内部已等待）
        # 验证两个供应商结果都已写入
        conn = temp_db.get_connection()
        providers_written = conn.execute(
            "SELECT provider FROM provider_results WHERE session_id=?",
            (result.session_id,)
        ).fetchall()
        conn.close()

        assert len(providers_written) == 2

    def test_search_results_written_with_rank(self, strategy, recorder, temp_db):
        """测试搜索结果写入数据库含 rank 字段"""
        provider = MockProvider(
            name="test_provider",
            should_succeed=True,
            results=[
                create_search_item("Result 1", "https://example.com/1"),
                create_search_item("Result 2", "https://example.com/2")
            ]
        )
        request = ProviderSearchRequest(query="test", max_results=10)

        result = strategy.execute_comparison(
            providers=[provider],
            request=request,
            recorder=recorder
        )

        # 验证搜索结果写入
        conn = temp_db.get_connection()
        search_results = conn.execute(
            "SELECT rank, title FROM search_results WHERE session_id=? ORDER BY rank",
            (result.session_id,)
        ).fetchall()
        conn.close()

        assert len(search_results) == 2
        assert search_results[0][0] == 1  # rank 字段
        assert search_results[1][0] == 2

    def test_background_thread_parameter_recorder_session_id(self, strategy, recorder, temp_db):
        """测试后台线程参数包含 recorder 和 session_id"""
        provider1 = MockProvider(
            name="provider1",
            should_succeed=True,
            results=[create_search_item("P1", "https://p1.com")],
            response_time_ms=50
        )
        provider2 = MockProvider(
            name="provider2",
            should_succeed=True,
            results=[create_search_item("P2", "https://p2.com")],
            response_time_ms=50
        )

        request = ProviderSearchRequest(query="test", max_results=10)
        result = strategy.execute_comparison(
            providers=[provider1, provider2],
            request=request,
            recorder=recorder
        )

        # 后台供应商结果应该写入数据库
        conn = temp_db.get_connection()
        provider2_result = conn.execute(
            "SELECT provider FROM provider_results WHERE session_id=? AND provider=?",
            (result.session_id, "provider2")
        ).fetchone()
        conn.close()

        assert provider2_result is not None

    def test_result_contains_session_id(self, strategy, recorder, temp_db):
        """测试 execute_comparison() 返回 session_id 并验证格式 (COMP-06)"""
        mock_provider = MockProvider(
            name="test_provider",
            should_succeed=True,
            results=[create_search_item("Test", "https://example.com")]
        )
        request = ProviderSearchRequest(query="test", max_results=10)

        result = strategy.execute_comparison(
            providers=[mock_provider],
            request=request,
            recorder=recorder
        )

        # 验证 session_id 存在
        assert result.session_id is not None

        # 验证格式 YYYYMMDD-HHMMSS-XXXX
        session_id = result.session_id
        assert session_id.count('-') == 2
        parts = session_id.split('-')
        assert len(parts[0]) == 8  # YYYYMMDD
        assert len(parts[1]) == 6  # HHMMSS
        assert len(parts[2]) == 4  # XXXX

    def test_normal_mode_no_session_id(self, strategy):
        """测试正常模式不返回 session_id (COMP-06)"""
        mock_provider = MockProvider(
            name="test_provider",
            should_succeed=True,
            results=[create_search_item("Test", "https://example.com")]
        )
        request = ProviderSearchRequest(query="test", max_results=10)

        result = strategy.execute_normal(
            providers=[mock_provider],
            request=request
        )

        # 正常模式无 session_id
        assert result.session_id is None