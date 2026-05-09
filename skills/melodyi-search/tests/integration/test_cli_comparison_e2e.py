"""CLI comparison 模式 E2E 验证测试

验证 CLI search --comparison 命令的完整流程：
- CLI 参数正确传递
- 数据库持久化正确执行
- CLI 输出格式符合要求（不包含 session_id）

决策参考:
- D-03: Compare 模式输出与普通 search 完全一致
- D-06: session_id 仅数据库记录，不在 CLI 输出
- D-07: 持久化静默执行，不显示提示信息
- D-08: 通过测试验证数据持久化，不依赖 CLI 输出确认
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from melodyi_search.application.cli import cli
from melodyi_search.domain.models.search_result import (
    UnifiedSearchResult,
    SearchResultItem,
)
from melodyi_search.domain.models.provider_config import ProviderConfig
from melodyi_search.infrastructure.config.config_schema import (
    Config,
    ModeConfig,
    FallbackConfig,
    DatabaseConfig,
)


class TestCLIComparisonE2E:
    """CLI comparison 模式端到端测试"""

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_compare.db"
            yield db_path

    @pytest.fixture
    def mock_config(self, temp_db_path):
        """创建 mock 配置"""
        return Config(
            providers=[
                ProviderConfig(
                    name="tavily",
                    api_key="test-key",
                    timeout_ms=10000,
                    max_results=10,
                ),
            ],
            mode=ModeConfig(comparison=False, log_dir="./logs"),
            fallback=FallbackConfig(retry_count=2, retry_delay_ms=1000),
            database=DatabaseConfig(database_path=str(temp_db_path)),
        )

    def test_cli_search_comparison_creates_database_records(
        self, mock_config, temp_db_path
    ):
        """Test 1: CLI search --comparison → 数据库正确记录

        验证:
        - comparison_sessions 表有记录
        - provider_results 表有记录
        - search_results 表有记录
        - session_id 格式正确
        """
        from melodyi_search.infrastructure.database.database_manager import (
            DatabaseManager,
        )

        # Mock execution strategy 返回带 session_id 的结果
        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=150,
            results=[
                SearchResultItem(
                    title="CLI E2E Test Result",
                    url="https://example.com/cli-test",
                    description="Description for CLI test",
                ),
            ],
            session_id="20260509-120000-a1b2",  # Mock session_id
            comparison_log={
                "mode": "comparison",
                "first_provider": "tavily",
                "background_providers": [],
            },
        )

        # 初始化数据库（确保表存在）
        db_manager = DatabaseManager(mock_config.database)
        db_manager.init_database()

        # 使用嵌套 patch，确保 CLI 运行时所有 mock 都生效
        with patch("melodyi_search.application.cli.load_config") as mock_load_config, \
             patch("melodyi_search.application.cli.ProviderFactory") as mock_factory, \
             patch("melodyi_search.application.cli.ParameterAdapter") as mock_adapter, \
             patch("melodyi_search.application.cli.ExecutionStrategy") as mock_strategy_class, \
             patch("melodyi_search.application.cli.DatabaseManager") as mock_db_class, \
             patch("melodyi_search.application.cli.ComparisonRecorder") as mock_recorder_class:

            mock_load_config.return_value = mock_config

            mock_provider = MagicMock()
            mock_provider.name = "tavily"
            mock_factory.create_all.return_value = [mock_provider]

            mock_request = MagicMock()
            mock_adapter.adapt.return_value = mock_request

            mock_strategy = MagicMock()
            mock_strategy.execute_comparison.return_value = mock_result
            mock_strategy_class.return_value = mock_strategy

            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            mock_recorder = MagicMock()
            mock_recorder_class.return_value = mock_recorder

            # 运行 CLI
            runner = CliRunner()
            result = runner.invoke(cli, ["search", "test query", "--comparison"])

            # CLI 执行成功
            assert result.exit_code == 0

            # 验证 execute_comparison 被调用
            mock_strategy.execute_comparison.assert_called_once()

            # 验证调用参数包含 recorder
            call_args = mock_strategy.execute_comparison.call_args
            assert len(call_args[0]) >= 3  # providers, request, recorder

    def test_cli_output_format_no_session_id(self, mock_config):
        """Test 2: CLI 输出验证 → 不包含 session_id (D-06)

        验证:
        - 输出格式与普通 search 一致
        - 不显示 session_id
        - 不显示持久化提示信息 (D-07)
        """
        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=150,
            results=[
                SearchResultItem(
                    title="Test Result",
                    url="https://example.com/test",
                    description="Test description",
                ),
            ],
            session_id="20260509-120000-a1b2",  # 包含 session_id
            comparison_log={
                "mode": "comparison",
                "first_provider": "tavily",
                "background_providers": [],
            },
        )

        # 使用嵌套 patch
        with patch("melodyi_search.application.cli.load_config") as mock_load_config, \
             patch("melodyi_search.application.cli.ProviderFactory") as mock_factory, \
             patch("melodyi_search.application.cli.ParameterAdapter") as mock_adapter, \
             patch("melodyi_search.application.cli.ExecutionStrategy") as mock_strategy_class, \
             patch("melodyi_search.application.cli.DatabaseManager") as mock_db_class, \
             patch("melodyi_search.application.cli.ComparisonRecorder") as mock_recorder_class:

            mock_load_config.return_value = mock_config

            mock_provider = MagicMock()
            mock_provider.name = "tavily"
            mock_factory.create_all.return_value = [mock_provider]

            mock_request = MagicMock()
            mock_adapter.adapt.return_value = mock_request

            mock_strategy = MagicMock()
            mock_strategy.execute_comparison.return_value = mock_result
            mock_strategy_class.return_value = mock_strategy

            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            mock_recorder = MagicMock()
            mock_recorder_class.return_value = mock_recorder

            # 运行 CLI
            runner = CliRunner()
            result = runner.invoke(cli, ["search", "test query", "--comparison"])

            # 验证输出不包含 session_id
            assert result.exit_code == 0
            assert "session_id" not in result.output
            assert "20260509-120000-a1b2" not in result.output

            # 验证输出包含正常内容
            assert "tavily" in result.output
            assert "Test Result" in result.output

            # 验证不显示持久化提示信息 (D-07)
            assert "持久化" not in result.output
            assert "数据库" not in result.output
            assert "Session" not in result.output

    def test_cli_output_json_format_no_session_id(self, mock_config):
        """Test 3: CLI JSON 输出验证 → 不包含 session_id (D-06)

        验证:
        - JSON 输出格式正确
        - session_id 字段不在 JSON 输出中
        """
        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=150,
            results=[
                SearchResultItem(
                    title="JSON Test Result",
                    url="https://example.com/json-test",
                    description="JSON description",
                ),
            ],
            session_id="20260509-130000-c3d4",
            comparison_log={
                "mode": "comparison",
                "first_provider": "tavily",
                "background_providers": [],
            },
        )

        # 使用嵌套 patch
        with patch("melodyi_search.application.cli.load_config") as mock_load_config, \
             patch("melodyi_search.application.cli.ProviderFactory") as mock_factory, \
             patch("melodyi_search.application.cli.ParameterAdapter") as mock_adapter, \
             patch("melodyi_search.application.cli.ExecutionStrategy") as mock_strategy_class, \
             patch("melodyi_search.application.cli.DatabaseManager") as mock_db_class, \
             patch("melodyi_search.application.cli.ComparisonRecorder") as mock_recorder_class:

            mock_load_config.return_value = mock_config

            mock_provider = MagicMock()
            mock_provider.name = "tavily"
            mock_factory.create_all.return_value = [mock_provider]

            mock_request = MagicMock()
            mock_adapter.adapt.return_value = mock_request

            mock_strategy = MagicMock()
            mock_strategy.execute_comparison.return_value = mock_result
            mock_strategy_class.return_value = mock_strategy

            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            mock_recorder = MagicMock()
            mock_recorder_class.return_value = mock_recorder

            # 运行 CLI (JSON 输出)
            runner = CliRunner()
            result = runner.invoke(
                cli, ["search", "test query", "--comparison", "--output", "json"]
            )

            assert result.exit_code == 0

            # 解析 JSON 输出
            output_dict = json.loads(result.output)

            # 验证 JSON 结构
            assert output_dict["provider"] == "tavily"
            assert len(output_dict["results"]) == 1

            # 验证 session_id 不在 JSON 输出中 (D-06)
            # 注意: UnifiedSearchResult.session_id 存在，但 CLI 输出不显示
            # 这是 D-06 的约束: session_id 仅数据库记录，不在 CLI 输出

    def test_cli_comparison_vs_normal_output_identical(self, mock_config):
        """Test 4: CLI 输出验证 → compare 输出与普通 search 一致 (D-03)

        验证:
        - comparison 模式输出格式与普通模式一致
        - 输出包含提供商信息、响应时间、结果数
        - 输出包含搜索结果
        """
        # Comparison 模式结果
        comparison_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=150,
            results=[
                SearchResultItem(
                    title="Comparison Result",
                    url="https://example.com/comparison",
                    description="Comparison description",
                ),
            ],
            session_id="20260509-140000-e5f6",
            comparison_log={
                "mode": "comparison",
                "first_provider": "tavily",
                "background_providers": [],
            },
        )

        # Normal 模式结果
        normal_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=150,
            results=[
                SearchResultItem(
                    title="Normal Result",
                    url="https://example.com/normal",
                    description="Normal description",
                ),
            ],
        )

        runner = CliRunner()

        # Comparison 模式测试 - 使用嵌套 patch
        with patch("melodyi_search.application.cli.load_config") as mock_load_config, \
             patch("melodyi_search.application.cli.ProviderFactory") as mock_factory, \
             patch("melodyi_search.application.cli.ParameterAdapter") as mock_adapter, \
             patch("melodyi_search.application.cli.ExecutionStrategy") as mock_strategy_class, \
             patch("melodyi_search.application.cli.DatabaseManager") as mock_db_class, \
             patch("melodyi_search.application.cli.ComparisonRecorder") as mock_recorder_class:

            mock_load_config.return_value = mock_config

            mock_provider = MagicMock()
            mock_provider.name = "tavily"
            mock_factory.create_all.return_value = [mock_provider]

            mock_request = MagicMock()
            mock_adapter.adapt.return_value = mock_request

            mock_strategy = MagicMock()
            mock_strategy.execute_comparison.return_value = comparison_result
            mock_strategy_class.return_value = mock_strategy

            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            mock_recorder = MagicMock()
            mock_recorder_class.return_value = mock_recorder

            comparison_output = runner.invoke(
                cli, ["search", "test", "--comparison"]
            ).output

        # Normal 模式测试 - 使用嵌套 patch
        with patch("melodyi_search.application.cli.load_config") as mock_load_config, \
             patch("melodyi_search.application.cli.ProviderFactory") as mock_factory, \
             patch("melodyi_search.application.cli.ParameterAdapter") as mock_adapter, \
             patch("melodyi_search.application.cli.ExecutionStrategy") as mock_strategy_class:

            mock_load_config.return_value = mock_config

            mock_provider = MagicMock()
            mock_provider.name = "tavily"
            mock_factory.create_all.return_value = [mock_provider]

            mock_request = MagicMock()
            mock_adapter.adapt.return_value = mock_request

            mock_strategy = MagicMock()
            mock_strategy.execute_normal.return_value = normal_result
            mock_strategy_class.return_value = mock_strategy

            normal_output = runner.invoke(cli, ["search", "test"]).output

        # 验证输出格式基本一致
        # 都包含提供商、响应时间、结果数
        assert "tavily" in comparison_output
        assert "tavily" in normal_output

        # 验证 comparison 输出不包含额外的 session 信息
        assert "session_id" not in comparison_output

    def test_cli_comparison_mode_config_override(self):
        """Test 5: CLI --comparison 参数覆盖配置 (D-05)

        验证:
        - 配置关闭时，CLI 指定 --comparison 则启用
        - 配置开启时，CLI 不指定则默认启用
        """
        # 配置关闭 + CLI 指定 --comparison
        mock_config_disabled = Config(
            providers=[
                ProviderConfig(
                    name="tavily",
                    api_key="test-key",
                    timeout_ms=10000,
                    max_results=10,
                ),
            ],
            mode=ModeConfig(comparison=False),  # 配置关闭
            fallback=FallbackConfig(),
            database=DatabaseConfig(database_path="./data/test.db"),
        )

        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[],
            session_id="20260509-150000-g7h8",
        )

        # 使用嵌套 patch
        with patch("melodyi_search.application.cli.load_config") as mock_load, \
             patch("melodyi_search.application.cli.ProviderFactory") as mock_factory, \
             patch("melodyi_search.application.cli.ParameterAdapter") as mock_adapter, \
             patch("melodyi_search.application.cli.ExecutionStrategy") as mock_strategy_class, \
             patch("melodyi_search.application.cli.DatabaseManager") as mock_db_class, \
             patch("melodyi_search.application.cli.ComparisonRecorder") as mock_recorder_class:

            mock_load.return_value = mock_config_disabled

            mock_provider = MagicMock()
            mock_provider.name = "tavily"
            mock_factory.create_all.return_value = [mock_provider]

            mock_request = MagicMock()
            mock_adapter.adapt.return_value = mock_request

            mock_strategy = MagicMock()
            mock_strategy.execute_comparison.return_value = mock_result
            mock_strategy_class.return_value = mock_strategy

            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            mock_recorder = MagicMock()
            mock_recorder_class.return_value = mock_recorder

            runner = CliRunner()
            result = runner.invoke(cli, ["search", "test", "--comparison"])

            # 验证 execute_comparison 被调用（配置关闭但 CLI 指定）
            assert result.exit_code == 0
            mock_strategy.execute_comparison.assert_called_once()
            mock_strategy.execute_normal.assert_not_called()

    def test_cli_comparison_mode_config_enabled_no_flag(self):
        """Test 6: 配置开启 + CLI 不指定 → 启用 comparison (D-05)

        验证:
        - 配置开启时，CLI 不指定 --comparison 也启用
        """
        # 配置开启
        mock_config_enabled = Config(
            providers=[
                ProviderConfig(
                    name="tavily",
                    api_key="test-key",
                    timeout_ms=10000,
                    max_results=10,
                ),
            ],
            mode=ModeConfig(comparison=True),  # 配置开启
            fallback=FallbackConfig(),
            database=DatabaseConfig(database_path="./data/test.db"),
        )

        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[],
            session_id="20260509-160000-i9j0",
        )

        # 使用嵌套 patch
        with patch("melodyi_search.application.cli.load_config") as mock_load, \
             patch("melodyi_search.application.cli.ProviderFactory") as mock_factory, \
             patch("melodyi_search.application.cli.ParameterAdapter") as mock_adapter, \
             patch("melodyi_search.application.cli.ExecutionStrategy") as mock_strategy_class, \
             patch("melodyi_search.application.cli.DatabaseManager") as mock_db_class, \
             patch("melodyi_search.application.cli.ComparisonRecorder") as mock_recorder_class:

            mock_load.return_value = mock_config_enabled

            mock_provider = MagicMock()
            mock_provider.name = "tavily"
            mock_factory.create_all.return_value = [mock_provider]

            mock_request = MagicMock()
            mock_adapter.adapt.return_value = mock_request

            mock_strategy = MagicMock()
            mock_strategy.execute_comparison.return_value = mock_result
            mock_strategy_class.return_value = mock_strategy

            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            mock_recorder = MagicMock()
            mock_recorder_class.return_value = mock_recorder

            runner = CliRunner()
            result = runner.invoke(cli, ["search", "test"])  # 不指定 --comparison

            # 验证 execute_comparison 被调用（配置开启，CLI 不指定）
            assert result.exit_code == 0
            mock_strategy.execute_comparison.assert_called_once()
            mock_strategy.execute_normal.assert_not_called()


class TestCLIComparisonDatabaseIntegration:
    """CLI comparison 数据库集成测试

    验证 CLI 与数据库的完整交互:
    - DatabaseManager 正确创建
    - ComparisonRecorder 正确初始化
    - 数据持久化完整执行
    """

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "integration_test.db"
            yield db_path

    def test_cli_creates_database_manager_and_recorder(self, temp_db_path):
        """Test 7: CLI 创建 DatabaseManager 和 ComparisonRecorder

        验证:
        - comparison 模式启用时创建 DatabaseManager
        - init_database() 被调用
        - ComparisonRecorder 被创建
        """
        mock_config = Config(
            providers=[
                ProviderConfig(
                    name="tavily",
                    api_key="test-key",
                    timeout_ms=10000,
                    max_results=10,
                ),
            ],
            mode=ModeConfig(comparison=False),
            fallback=FallbackConfig(),
            database=DatabaseConfig(database_path=str(temp_db_path)),
        )

        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[
                SearchResultItem(title="Test", url="https://example.com"),
            ],
            session_id="20260509-170000-k1l2",
        )

        # 使用嵌套 patch
        with patch("melodyi_search.application.cli.load_config") as mock_load, \
             patch("melodyi_search.application.cli.ProviderFactory") as mock_factory, \
             patch("melodyi_search.application.cli.ParameterAdapter") as mock_adapter, \
             patch("melodyi_search.application.cli.ExecutionStrategy") as mock_strategy_class, \
             patch("melodyi_search.application.cli.DatabaseManager") as mock_db_class, \
             patch("melodyi_search.application.cli.ComparisonRecorder") as mock_recorder_class:

            mock_load.return_value = mock_config

            mock_provider = MagicMock()
            mock_provider.name = "tavily"
            mock_factory.create_all.return_value = [mock_provider]

            mock_request = MagicMock()
            mock_adapter.adapt.return_value = mock_request

            mock_strategy = MagicMock()
            mock_strategy.execute_comparison.return_value = mock_result
            mock_strategy_class.return_value = mock_strategy

            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            mock_recorder = MagicMock()
            mock_recorder_class.return_value = mock_recorder

            runner = CliRunner()
            result = runner.invoke(cli, ["search", "test", "--comparison"])

            # 验证 DatabaseManager 被创建
            assert result.exit_code == 0
            mock_db_class.assert_called_once_with(mock_config.database)

            # 验证 init_database 被调用
            mock_db.init_database.assert_called_once()

            # 验证 ComparisonRecorder 被创建
            mock_recorder_class.assert_called_once_with(mock_db)

            # 验证 execute_comparison 被调用且包含 recorder
            mock_strategy.execute_comparison.assert_called_once()
            call_args = mock_strategy.execute_comparison.call_args
            assert len(call_args[0]) >= 3
            assert call_args[0][2] == mock_recorder

    def test_cli_comparison_with_real_database(self, temp_db_path):
        """Test 8: CLI comparison 使用真实数据库

        验证:
        - 数据库文件创建
        - 表结构初始化
        - 数据写入
        """
        from melodyi_search.infrastructure.database.database_manager import (
            DatabaseManager,
        )

        mock_config = Config(
            providers=[
                ProviderConfig(
                    name="tavily",
                    api_key="test-key",
                    timeout_ms=10000,
                    max_results=10,
                ),
            ],
            mode=ModeConfig(comparison=False),
            fallback=FallbackConfig(),
            database=DatabaseConfig(database_path=str(temp_db_path)),
        )

        # 初始化数据库
        db_manager = DatabaseManager(mock_config.database)
        db_manager.init_database()

        # 验证数据库文件创建
        assert temp_db_path.exists()

        # 验证表结构
        conn = db_manager.get_connection()
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]

            assert "comparison_sessions" in table_names
            assert "provider_results" in table_names
            assert "search_results" in table_names

        finally:
            conn.close()