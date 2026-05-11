"""Comparison 模式 E2E 验证测试

验证完整的 comparison 模式流程：
- search → execute → persist
- 数据库记录正确性（session、provider、results）
- session_id 格式验证 (YYYYMMDD-HHMMSS-XXXX)

决策参考:
- D-03: Compare 模式输出与普通 search 完全一致
- D-06: session_id 仅数据库记录，不在 CLI 输出
- D-08: 通过测试验证数据持久化，不依赖 CLI 输出确认
"""

import os
import re
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from melodyi_web.domain.services.execution_strategy import ExecutionStrategy
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
    SearchResultItem,
)


class MockProvider(BaseProvider):
    """Mock 提供商，用于测试"""

    def __init__(
        self,
        name: str,
        results: list = None,
        response_time_ms: int = 100,
        error: str = None,
    ):
        self._name = name
        self._results = results or []
        self._response_time_ms = response_time_ms
        self._error = error

    @property
    def name(self) -> str:
        return self._name

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        return ProviderSearchResult(
            provider=self._name,
            results=self._results,
            response_time_ms=self._response_time_ms,
            error=self._error,
            raw_response={"mock": True},
        )

    def supports_time_filter(self) -> bool:
        return True

    def supports_domain_filter(self) -> bool:
        return True

    def get_max_results_limit(self) -> int:
        return 100


class TestComparisonE2E:
    """Comparison 模式端到端测试"""

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_compare.db"
            yield db_path

    @pytest.fixture
    def db_manager(self, temp_db_path):
        """创建数据库管理器"""
        config = DatabaseConfig(database_path=str(temp_db_path))
        manager = DatabaseManager(config)
        manager.init_database()
        return manager

    @pytest.fixture
    def recorder(self, db_manager):
        """创建 recorder 实例"""
        return ComparisonRecorder(db_manager)

    @pytest.fixture
    def strategy(self):
        """创建执行策略实例"""
        return ExecutionStrategy()

    def test_comparison_full_flow(self, strategy, recorder, db_manager, temp_db_path):
        """Test 1: 完整 comparison 流程 → 数据库有所有表记录

        验证:
        - comparison_sessions 表有记录
        - provider_results 表有记录
        - search_results 表有记录
        - session_id 格式正确
        """
        # 创建 mock providers
        mock_providers = [
            MockProvider(
                name="provider1",
                results=[
                    SearchResultItem(
                        title="Result 1 from Provider1",
                        url="https://example.com/1",
                        description="Description for result 1",
                    ),
                    SearchResultItem(
                        title="Result 2 from Provider1",
                        url="https://example.com/2",
                        description="Description for result 2",
                    ),
                ],
                response_time_ms=150,
            ),
            MockProvider(
                name="provider2",
                results=[
                    SearchResultItem(
                        title="Result 1 from Provider2",
                        url="https://provider2.example.com/1",
                        description="Description from provider2",
                    ),
                ],
                response_time_ms=200,
            ),
        ]

        # 执行 comparison
        request = ProviderSearchRequest(query="test query", max_results=10)
        result = strategy.execute_comparison(mock_providers, request, recorder)

        # 验证 session_id 存在
        assert result.session_id is not None
        assert self._validate_session_id_format(result.session_id)

        # 验证数据库记录
        conn = db_manager.get_connection()
        try:
            # 验证 comparison_sessions
            sessions = conn.execute(
                "SELECT session_id, query, params FROM comparison_sessions WHERE session_id = ?",
                (result.session_id,),
            ).fetchall()
            assert len(sessions) == 1
            assert sessions[0][1] == "test query"  # query 字段

            # 验证 provider_results
            providers = conn.execute(
                "SELECT provider, response_time_ms, results_count, status FROM provider_results WHERE session_id = ?",
                (result.session_id,),
            ).fetchall()
            assert len(providers) == 2  # 两个供应商

            # 验证第一个供应商
            provider1_row = [p for p in providers if p[0] == "provider1"][0]
            assert provider1_row[1] == 150  # response_time_ms
            assert provider1_row[2] == 2  # results_count
            assert provider1_row[3] == "success"  # status

            # 验证第二个供应商
            provider2_row = [p for p in providers if p[0] == "provider2"][0]
            assert provider2_row[1] == 200  # response_time_ms
            assert provider2_row[2] == 1  # results_count
            assert provider2_row[3] == "success"  # status

            # 验证 search_results
            results = conn.execute(
                "SELECT provider, rank, title, url, description FROM search_results WHERE session_id = ? ORDER BY provider, rank",
                (result.session_id,),
            ).fetchall()
            assert len(results) == 3  # provider1 有 2 个，provider2 有 1 个

            # 验证 provider1 的搜索结果
            provider1_results = [r for r in results if r[0] == "provider1"]
            assert len(provider1_results) == 2
            assert provider1_results[0][1] == 1  # rank
            assert provider1_results[0][2] == "Result 1 from Provider1"
            assert provider1_results[0][3] == "https://example.com/1"
            assert provider1_results[1][1] == 2  # rank
            assert provider1_results[1][2] == "Result 2 from Provider1"

            # 验证 provider2 的搜索结果
            provider2_results = [r for r in results if r[0] == "provider2"]
            assert len(provider2_results) == 1
            assert provider2_results[0][1] == 1  # rank
            assert provider2_results[0][2] == "Result 1 from Provider2"

        finally:
            conn.close()

    def test_session_id_format_verification(self, strategy, recorder):
        """Test 2: session_id 格式验证 → 符合 YYYYMMDD-HHMMSS-XXXX

        验证:
        - 总长度为 20 字符
        - 时间戳前缀 8 位数字
        - 时间部分 6 位数字
        - 随机后缀 4 位十六进制
        """
        mock_provider = MockProvider(
            name="test_provider",
            results=[SearchResultItem(title="Test", url="https://example.com")],
        )
        request = ProviderSearchRequest(query="test", max_results=10)

        result = strategy.execute_comparison([mock_provider], request, recorder)

        session_id = result.session_id

        # 格式验证: YYYYMMDD-HHMMSS-XXXX
        assert session_id is not None
        assert len(session_id) == 20  # 8+1+6+1+4 = 20
        assert session_id.count("-") == 2

        parts = session_id.split("-")

        # YYYYMMDD: 8位数字
        assert len(parts[0]) == 8
        assert parts[0].isdigit()

        # HHMMSS: 6位数字
        assert len(parts[1]) == 6
        assert parts[1].isdigit()

        # XXXX: 4位十六进制
        assert len(parts[2]) == 4
        assert all(c in "0123456789abcdef" for c in parts[2])

    def test_multiple_providers_all_written(self, strategy, recorder, db_manager):
        """Test 3: 多供应商执行 → 所有供应商结果写入

        验证:
        - 所有供应商结果写入 provider_results 表
        - 所有搜索结果写入 search_results 表
        - 后台线程执行并写入数据
        """
        # 创建 3 个 mock providers
        mock_providers = [
            MockProvider(
                name="provider_a",
                results=[
                    SearchResultItem(title="A Result", url="https://a.example.com"),
                ],
                response_time_ms=50,
            ),
            MockProvider(
                name="provider_b",
                results=[
                    SearchResultItem(title="B Result 1", url="https://b.example.com/1"),
                    SearchResultItem(title="B Result 2", url="https://b.example.com/2"),
                ],
                response_time_ms=100,
            ),
            MockProvider(
                name="provider_c",
                results=[
                    SearchResultItem(title="C Result", url="https://c.example.com"),
                ],
                response_time_ms=150,
            ),
        ]

        request = ProviderSearchRequest(query="multi provider test", max_results=10)
        result = strategy.execute_comparison(mock_providers, request, recorder)

        # 验证数据库记录
        conn = db_manager.get_connection()
        try:
            # 验证所有供应商结果写入
            providers = conn.execute(
                "SELECT provider FROM provider_results WHERE session_id = ?",
                (result.session_id,),
            ).fetchall()
            provider_names = [p[0] for p in providers]

            assert len(providers) == 3
            assert "provider_a" in provider_names
            assert "provider_b" in provider_names
            assert "provider_c" in provider_names

            # 验证所有搜索结果写入
            search_results = conn.execute(
                "SELECT COUNT(*) FROM search_results WHERE session_id = ?",
                (result.session_id,),
            ).fetchone()
            assert search_results[0] == 4  # 1 + 2 + 1

        finally:
            conn.close()

    def test_provider_error_recorded(self, strategy, recorder, db_manager):
        """Test 4: 供应商错误记录

        验证:
        - 失败供应商状态为 error
        - 错误信息正确记录
        """
        mock_providers = [
            MockProvider(
                name="success_provider",
                results=[
                    SearchResultItem(title="Success", url="https://success.example.com"),
                ],
                response_time_ms=100,
            ),
            MockProvider(
                name="error_provider",
                results=[],
                response_time_ms=200,
                error="Connection timeout",
            ),
        ]

        request = ProviderSearchRequest(query="error test", max_results=10)
        result = strategy.execute_comparison(mock_providers, request, recorder)

        # 验证数据库记录
        conn = db_manager.get_connection()
        try:
            # 验证成功供应商
            success_row = conn.execute(
                "SELECT status, error_message FROM provider_results WHERE session_id = ? AND provider = ?",
                (result.session_id, "success_provider"),
            ).fetchone()
            assert success_row is not None
            assert success_row[0] == "success"
            assert success_row[1] is None

            # 验证失败供应商
            error_row = conn.execute(
                "SELECT status, error_message FROM provider_results WHERE session_id = ? AND provider = ?",
                (result.session_id, "error_provider"),
            ).fetchone()
            assert error_row is not None
            assert error_row[0] == "error"
            assert error_row[1] == "Connection timeout"

        finally:
            conn.close()

    def test_session_id_uniqueness(self, strategy, recorder):
        """Test 5: session_id 唯一性验证

        验证:
        - 多次执行生成不同的 session_id
        - session_id 包含随机后缀防止冲突
        """
        mock_provider = MockProvider(
            name="test_provider",
            results=[SearchResultItem(title="Test", url="https://example.com")],
        )
        request = ProviderSearchRequest(query="test", max_results=10)

        # 执行多次
        session_ids = []
        for _ in range(10):
            result = strategy.execute_comparison([mock_provider], request, recorder)
            session_ids.append(result.session_id)

        # 验证所有 session_id 不同
        assert len(set(session_ids)) == 10

        # 验证所有 session_id 格式正确
        for session_id in session_ids:
            assert self._validate_session_id_format(session_id)

    def test_request_params_recorded(self, strategy, recorder, db_manager):
        """Test 6: 请求参数记录

        验证:
        - query 正确记录
        - params JSON 包含 max_results
        """
        mock_provider = MockProvider(
            name="test_provider",
            results=[SearchResultItem(title="Test", url="https://example.com")],
        )
        request = ProviderSearchRequest(
            query="complex query with params",
            max_results=20,
            time_range=None,
            include_domains=["example.com"],
            exclude_domains=["spam.com"],
            language="zh",
        )

        result = strategy.execute_comparison([mock_provider], request, recorder)

        # 验证数据库记录
        conn = db_manager.get_connection()
        try:
            session_row = conn.execute(
                "SELECT query, params FROM comparison_sessions WHERE session_id = ?",
                (result.session_id,),
            ).fetchone()

            assert session_row is not None
            assert session_row[0] == "complex query with params"

            # 验证 params JSON
            import json

            params_dict = json.loads(session_row[1])
            assert params_dict["max_results"] == 20
            assert params_dict["include_domains"] == ["example.com"]
            assert params_dict["exclude_domains"] == ["spam.com"]
            assert params_dict["language"] == "zh"

        finally:
            conn.close()

    def _validate_session_id_format(self, session_id: str) -> bool:
        """验证 session_id 格式: YYYYMMDD-HHMMSS-XXXX"""
        pattern = r"^\d{8}-\d{6}-[0-9a-f]{4}$"
        return re.match(pattern, session_id) is not None


class TestComparisonPersistenceIntegration:
    """Comparison 持久化集成测试

    验证完整的数据流:
    - ExecutionStrategy → ComparisonRecorder → DatabaseManager
    """

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "integration_test.db"
            yield db_path

    @pytest.fixture
    def db_manager(self, temp_db_path):
        """创建数据库管理器"""
        config = DatabaseConfig(database_path=str(temp_db_path))
        manager = DatabaseManager(config)
        manager.init_database()
        return manager

    @pytest.fixture
    def recorder(self, db_manager):
        """创建 recorder 实例"""
        return ComparisonRecorder(db_manager)

    @pytest.fixture
    def strategy(self):
        """创建执行策略实例"""
        return ExecutionStrategy()

    def test_full_persistence_chain(self, strategy, recorder, db_manager):
        """测试完整持久化链

        验证:
        - ExecutionStrategy 调用 ComparisonRecorder
        - ComparisonRecorder 写入 DatabaseManager
        - 数据库表结构正确
        """
        mock_provider = MockProvider(
            name="chain_test_provider",
            results=[
                SearchResultItem(
                    title="Chain Test Result",
                    url="https://chain.example.com",
                    description="Testing the full chain",
                )
            ],
            response_time_ms=100,
        )
        request = ProviderSearchRequest(query="chain test", max_results=10)

        # 执行完整流程
        result = strategy.execute_comparison([mock_provider], request, recorder)

        # 验证数据库表存在并有数据
        conn = db_manager.get_connection()
        try:
            # 验证 comparison_sessions 表
            sessions_count = conn.execute(
                "SELECT COUNT(*) FROM comparison_sessions"
            ).fetchone()
            assert sessions_count[0] >= 1

            # 验证 provider_results 表
            providers_count = conn.execute(
                "SELECT COUNT(*) FROM provider_results"
            ).fetchone()
            assert providers_count[0] >= 1

            # 验证 search_results 表
            results_count = conn.execute(
                "SELECT COUNT(*) FROM search_results"
            ).fetchone()
            assert results_count[0] >= 1

        finally:
            conn.close()

    def test_database_indexes_created(self, db_manager):
        """测试数据库索引创建

        验证:
        - 所有必要索引已创建
        - 查询性能优化
        """
        conn = db_manager.get_connection()
        try:
            # 验证索引数量
            indexes_count = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()
            assert indexes_count[0] >= 6  # 至少 6 个索引

            # 验证关键索引存在
            indexes = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            index_names = [i[0] for i in indexes]

            assert "idx_sessions_timestamp" in index_names
            assert "idx_provider_results_session_id" in index_names
            assert "idx_search_results_session_id" in index_names

        finally:
            conn.close()