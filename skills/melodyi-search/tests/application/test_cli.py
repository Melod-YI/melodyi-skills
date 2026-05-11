"""CLI 测试

测试 click 命令行界面。
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from melodyi_web.application.cli import cli, main
from melodyi_web.domain.models.search_result import UnifiedSearchResult, SearchResultItem, SearchError
from melodyi_web.domain.models.provider_config import ProviderConfig
from melodyi_web.infrastructure.config.config_schema import Config, ModeConfig, FallbackConfig


class TestCliHelp:
    """CLI 帮助信息测试"""

    def test_main_help(self):
        """测试主命令 --help"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "melodyi-web" in result.output
        assert "search" in result.output
        assert "config" in result.output

    def test_search_help(self):
        """测试 search 子命令 --help"""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "QUERY" in result.output
        assert "--max-results" in result.output
        assert "--time-range" in result.output
        assert "--include-domains" in result.output
        assert "--exclude-domains" in result.output
        assert "--provider" in result.output
        assert "--comparison" in result.output
        assert "--output" in result.output

    def test_config_help(self):
        """测试 config 子命令 --help"""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output


class TestVersionOption:
    """版本选项测试"""

    def test_version(self):
        """测试 --version"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "melodyi-web" in result.output
        assert "0.1.0" in result.output


class TestConfigShow:
    """config show 命令测试"""

    @patch("melodyi_web.application.cli.load_config")
    def test_config_show_text(self, mock_load_config):
        """测试 config show 文本输出"""
        mock_config = Config(
            providers=[
                ProviderConfig(
                    name="tavily",  # 使用有效的提供商名称
                    api_key="test-key",
                    timeout_ms=10000,
                    max_results=10,
                )
            ],
            mode=ModeConfig(comparison=False, log_dir="./logs"),
            fallback=FallbackConfig(retry_count=2, retry_delay_ms=1000),
        )
        mock_load_config.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "show"])

        assert result.exit_code == 0
        assert "tavily" in result.output
        assert "***" in result.output  # API key masked
        assert "10000" in result.output

    @patch("melodyi_web.application.cli.load_config")
    def test_config_show_json(self, mock_load_config):
        """测试 config show JSON 输出"""
        mock_config = Config(
            providers=[
                ProviderConfig(
                    name="brave",  # 使用有效的提供商名称
                    api_key="test-key",
                    timeout_ms=10000,
                    max_results=10,
                )
            ],
            mode=ModeConfig(comparison=False, log_dir="./logs"),
            fallback=FallbackConfig(retry_count=2, retry_delay_ms=1000),
        )
        mock_load_config.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "show", "--output", "json"])

        assert result.exit_code == 0
        assert '"providers"' in result.output
        assert '"brave"' in result.output
        assert '"***"' in result.output  # API key masked


class TestSearchCommand:
    """search 命令测试"""

    @patch("melodyi_web.application.cli.ProviderFactory")
    @patch("melodyi_web.application.cli.ParameterAdapter")
    @patch("melodyi_web.application.cli.ExecutionStrategy")
    @patch("melodyi_web.application.cli.load_config")
    def test_search_basic(
        self,
        mock_load_config,
        mock_strategy_class,
        mock_adapter_class,
        mock_factory_class,
    ):
        """测试基本搜索"""
        # 模拟配置
        mock_provider_config = ProviderConfig(
            name="tavily",
            api_key="test-key",
            timeout_ms=10000,
            max_results=10,
        )
        mock_config = Config(
            providers=[mock_provider_config],
            mode=ModeConfig(),
            fallback=FallbackConfig(),
        )
        mock_load_config.return_value = mock_config

        # 模拟提供商
        mock_provider = MagicMock()
        mock_provider.name = "tavily"
        mock_factory_class.create_all.return_value = [mock_provider]

        # 模拟适配器
        mock_request = MagicMock()
        mock_adapter_class.adapt.return_value = mock_request

        # 模拟执行策略
        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[
                SearchResultItem(
                    title="Test Result",
                    url="https://example.com",
                    description="Test description",
                )
            ],
        )
        mock_strategy = MagicMock()
        mock_strategy.execute_normal.return_value = mock_result
        mock_strategy_class.return_value = mock_strategy

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query"])

        assert result.exit_code == 0
        assert "tavily" in result.output
        assert "Test Result" in result.output

    @patch("melodyi_web.application.cli.ProviderFactory")
    @patch("melodyi_web.application.cli.ParameterAdapter")
    @patch("melodyi_web.application.cli.ExecutionStrategy")
    @patch("melodyi_web.application.cli.load_config")
    def test_search_with_options(
        self,
        mock_load_config,
        mock_strategy_class,
        mock_adapter_class,
        mock_factory_class,
    ):
        """测试带参数的搜索"""
        mock_provider_config = ProviderConfig(
            name="tavily",
            api_key="test-key",
            timeout_ms=10000,
            max_results=10,
        )
        mock_config = Config(
            providers=[mock_provider_config],
            mode=ModeConfig(),
            fallback=FallbackConfig(),
        )
        mock_load_config.return_value = mock_config

        mock_provider = MagicMock()
        mock_provider.name = "tavily"
        mock_factory_class.create_all.return_value = [mock_provider]

        mock_request = MagicMock()
        mock_adapter_class.adapt.return_value = mock_request

        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[],
        )
        mock_strategy = MagicMock()
        mock_strategy.execute_normal.return_value = mock_result
        mock_strategy_class.return_value = mock_strategy

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "search",
                "test query",
                "--max-results",
                "20",
                "--time-range",
                "day",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        # 验证 JSON 输出
        assert '"provider"' in result.output
        assert '"tavily"' in result.output

    @patch("melodyi_web.application.cli.ProviderFactory")
    @patch("melodyi_web.application.cli.ParameterAdapter")
    @patch("melodyi_web.application.cli.ExecutionStrategy")
    @patch("melodyi_web.application.cli.load_config")
    def test_search_with_include_domains(
        self,
        mock_load_config,
        mock_strategy_class,
        mock_adapter_class,
        mock_factory_class,
    ):
        """测试包含域名过滤"""
        mock_provider_config = ProviderConfig(
            name="tavily",
            api_key="test-key",
            timeout_ms=10000,
            max_results=10,
        )
        mock_config = Config(
            providers=[mock_provider_config],
            mode=ModeConfig(),
            fallback=FallbackConfig(),
        )
        mock_load_config.return_value = mock_config

        mock_provider = MagicMock()
        mock_provider.name = "tavily"
        mock_factory_class.create_all.return_value = [mock_provider]

        mock_request = MagicMock()
        mock_adapter_class.adapt.return_value = mock_request

        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[],
        )
        mock_strategy = MagicMock()
        mock_strategy.execute_normal.return_value = mock_result
        mock_strategy_class.return_value = mock_strategy

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "search",
                "test query",
                "--include-domains",
                "example.com",
                "-i",
                "test.com",
            ],
        )

        assert result.exit_code == 0

    @patch("melodyi_web.application.cli.ProviderFactory")
    @patch("melodyi_web.application.cli.ParameterAdapter")
    @patch("melodyi_web.application.cli.ExecutionStrategy")
    @patch("melodyi_web.application.cli.load_config")
    def test_search_with_provider(
        self,
        mock_load_config,
        mock_strategy_class,
        mock_adapter_class,
        mock_factory_class,
    ):
        """测试指定提供商"""
        mock_provider_config = ProviderConfig(
            name="brave",  # 使用有效的提供商名称
            api_key="test-key",
            timeout_ms=10000,
            max_results=10,
        )
        mock_config = Config(
            providers=[mock_provider_config],
            mode=ModeConfig(),
            fallback=FallbackConfig(),
        )
        mock_load_config.return_value = mock_config

        mock_provider = MagicMock()
        mock_provider.name = "brave"
        # 使用 create_all 而非 create，因为 CLI 总是使用 create_all
        mock_factory_class.create_all.return_value = [mock_provider]

        mock_request = MagicMock()
        mock_adapter_class.adapt.return_value = mock_request

        mock_result = UnifiedSearchResult(
            provider="brave",
            response_time_ms=100,
            results=[],
        )
        mock_strategy = MagicMock()
        mock_strategy.execute_normal.return_value = mock_result
        mock_strategy_class.return_value = mock_strategy

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["search", "test query", "--provider", "brave"],
        )

        assert result.exit_code == 0
        assert "brave" in result.output

    @patch("melodyi_web.application.cli.load_config")
    def test_search_invalid_provider(self, mock_load_config):
        """测试无效提供商"""
        mock_config = Config(
            providers=[
                ProviderConfig(
                    name="tavily",  # 使用有效的提供商名称
                    api_key="test-key",
                    timeout_ms=10000,
                    max_results=10,
                )
            ],
            mode=ModeConfig(),
            fallback=FallbackConfig(),
        )
        mock_load_config.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["search", "test query", "--provider", "invalid-provider"],
        )

        assert result.exit_code == 1
        assert "错误" in result.output or "invalid-provider" in result.output

    @patch("melodyi_web.application.cli.ProviderFactory")
    @patch("melodyi_web.application.cli.ParameterAdapter")
    @patch("melodyi_web.application.cli.ExecutionStrategy")
    @patch("melodyi_web.application.cli.load_config")
    def test_search_comparison_mode(
        self,
        mock_load_config,
        mock_strategy_class,
        mock_adapter_class,
        mock_factory_class,
    ):
        """测试比对模式"""
        mock_provider_config = ProviderConfig(
            name="tavily",
            api_key="test-key",
            timeout_ms=10000,
            max_results=10,
        )
        mock_config = Config(
            providers=[mock_provider_config],
            mode=ModeConfig(),
            fallback=FallbackConfig(),
        )
        mock_load_config.return_value = mock_config

        mock_provider = MagicMock()
        mock_provider.name = "tavily"
        mock_factory_class.create_all.return_value = [mock_provider]

        mock_request = MagicMock()
        mock_adapter_class.adapt.return_value = mock_request

        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[],
            comparison_log={
                "mode": "comparison",
                "first_provider": "tavily",
                "background_providers": ["brave"],
            },
        )
        mock_strategy = MagicMock()
        mock_strategy.execute_comparison.return_value = mock_result
        mock_strategy_class.return_value = mock_strategy

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query", "--comparison"])

        assert result.exit_code == 0
        mock_strategy.execute_comparison.assert_called_once()

    @patch("melodyi_web.application.cli.ComparisonRecorder")
    @patch("melodyi_web.application.cli.DatabaseManager")
    @patch("melodyi_web.application.cli.ProviderFactory")
    @patch("melodyi_web.application.cli.ParameterAdapter")
    @patch("melodyi_web.application.cli.ExecutionStrategy")
    @patch("melodyi_web.application.cli.load_config")
    def test_search_comparison_mode_with_config_enabled(
        self,
        mock_load_config,
        mock_strategy_class,
        mock_adapter_class,
        mock_factory_class,
        mock_db_manager_class,
        mock_recorder_class,
    ):
        """测试配置开启比对模式，CLI 不指定 --comparison 参数"""
        # D-05: 配置开启时，CLI 不指定则默认启用
        mock_provider_config = ProviderConfig(
            name="tavily",
            api_key="test-key",
            timeout_ms=10000,
            max_results=10,
        )
        mock_config = Config(
            providers=[mock_provider_config],
            mode=ModeConfig(comparison=True),  # 配置开启 comparison
            fallback=FallbackConfig(),
        )
        mock_load_config.return_value = mock_config

        mock_provider = MagicMock()
        mock_provider.name = "tavily"
        mock_factory_class.create_all.return_value = [mock_provider]

        mock_request = MagicMock()
        mock_adapter_class.adapt.return_value = mock_request

        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[],
            comparison_log={
                "mode": "comparison",
                "first_provider": "tavily",
                "background_providers": [],
            },
        )
        mock_strategy = MagicMock()
        mock_strategy.execute_comparison.return_value = mock_result
        mock_strategy_class.return_value = mock_strategy

        # Mock DatabaseManager and ComparisonRecorder
        mock_db_manager = MagicMock()
        mock_db_manager_class.return_value = mock_db_manager
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query"])  # 不指定 --comparison

        assert result.exit_code == 0
        # 验证 DatabaseManager 被创建
        mock_db_manager_class.assert_called_once_with(mock_config.database)
        # 验证 init_database 被调用
        mock_db_manager.init_database.assert_called_once()
        # 验证 ComparisonRecorder 被创建
        mock_recorder_class.assert_called_once_with(mock_db_manager)
        # 验证 execute_comparison 被调用（包含 recorder 参数）
        mock_strategy.execute_comparison.assert_called_once()
        call_args = mock_strategy.execute_comparison.call_args
        assert len(call_args[0]) >= 3  # providers, request, recorder
        assert call_args[0][2] == mock_recorder  # 第三个参数是 recorder

    @patch("melodyi_web.application.cli.ComparisonRecorder")
    @patch("melodyi_web.application.cli.DatabaseManager")
    @patch("melodyi_web.application.cli.ProviderFactory")
    @patch("melodyi_web.application.cli.ParameterAdapter")
    @patch("melodyi_web.application.cli.ExecutionStrategy")
    @patch("melodyi_web.application.cli.load_config")
    def test_search_comparison_mode_override_config(
        self,
        mock_load_config,
        mock_strategy_class,
        mock_adapter_class,
        mock_factory_class,
        mock_db_manager_class,
        mock_recorder_class,
    ):
        """测试配置关闭 + CLI 指定 --comparison 则启用持久化"""
        # D-05: 配置关闭时，CLI 指定 --comparison 则启用
        mock_provider_config = ProviderConfig(
            name="tavily",
            api_key="test-key",
            timeout_ms=10000,
            max_results=10,
        )
        mock_config = Config(
            providers=[mock_provider_config],
            mode=ModeConfig(comparison=False),  # 配置关闭 comparison
            fallback=FallbackConfig(),
        )
        mock_load_config.return_value = mock_config

        mock_provider = MagicMock()
        mock_provider.name = "tavily"
        mock_factory_class.create_all.return_value = [mock_provider]

        mock_request = MagicMock()
        mock_adapter_class.adapt.return_value = mock_request

        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[],
            comparison_log={
                "mode": "comparison",
                "first_provider": "tavily",
                "background_providers": [],
            },
        )
        mock_strategy = MagicMock()
        mock_strategy.execute_comparison.return_value = mock_result
        mock_strategy_class.return_value = mock_strategy

        # Mock DatabaseManager and ComparisonRecorder
        mock_db_manager = MagicMock()
        mock_db_manager_class.return_value = mock_db_manager
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query", "--comparison"])

        assert result.exit_code == 0
        # 验证 execute_comparison 被调用（包含 recorder 参数）
        mock_strategy.execute_comparison.assert_called_once()
        call_args = mock_strategy.execute_comparison.call_args
        assert len(call_args[0]) >= 3  # providers, request, recorder
        assert call_args[0][2] == mock_recorder

    @patch("melodyi_web.application.cli.ComparisonRecorder")
    @patch("melodyi_web.application.cli.DatabaseManager")
    @patch("melodyi_web.application.cli.ProviderFactory")
    @patch("melodyi_web.application.cli.ParameterAdapter")
    @patch("melodyi_web.application.cli.ExecutionStrategy")
    @patch("melodyi_web.application.cli.load_config")
    def test_search_normal_mode_with_config_enabled(
        self,
        mock_load_config,
        mock_strategy_class,
        mock_adapter_class,
        mock_factory_class,
        mock_db_manager_class,
        mock_recorder_class,
    ):
        """测试配置开启 + CLI 不指定 --comparison 应启用持久化"""
        # D-05: 配置开启时，CLI 不指定则默认启用
        mock_provider_config = ProviderConfig(
            name="tavily",
            api_key="test-key",
            timeout_ms=10000,
            max_results=10,
        )
        mock_config = Config(
            providers=[mock_provider_config],
            mode=ModeConfig(comparison=True),  # 配置开启
            fallback=FallbackConfig(),
        )
        mock_load_config.return_value = mock_config

        mock_provider = MagicMock()
        mock_provider.name = "tavily"
        mock_factory_class.create_all.return_value = [mock_provider]

        mock_request = MagicMock()
        mock_adapter_class.adapt.return_value = mock_request

        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[],
        )
        mock_strategy = MagicMock()
        mock_strategy.execute_comparison.return_value = mock_result
        mock_strategy_class.return_value = mock_strategy

        mock_db_manager = MagicMock()
        mock_db_manager_class.return_value = mock_db_manager
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query"])

        assert result.exit_code == 0
        # 配置开启，不指定 --comparison，应调用 execute_comparison
        mock_strategy.execute_comparison.assert_called_once()
        mock_strategy.execute_normal.assert_not_called()

    @patch("melodyi_web.application.cli.ProviderFactory")
    @patch("melodyi_web.application.cli.ParameterAdapter")
    @patch("melodyi_web.application.cli.ExecutionStrategy")
    @patch("melodyi_web.application.cli.load_config")
    def test_search_normal_mode_with_config_disabled(
        self,
        mock_load_config,
        mock_strategy_class,
        mock_adapter_class,
        mock_factory_class,
    ):
        """测试配置关闭 + CLI 不指定 --comparison → 不启用持久化"""
        # D-05: 配置关闭 + CLI 不指定 → 不启用持久化
        mock_provider_config = ProviderConfig(
            name="tavily",
            api_key="test-key",
            timeout_ms=10000,
            max_results=10,
        )
        mock_config = Config(
            providers=[mock_provider_config],
            mode=ModeConfig(comparison=False),  # 配置关闭
            fallback=FallbackConfig(),
        )
        mock_load_config.return_value = mock_config

        mock_provider = MagicMock()
        mock_provider.name = "tavily"
        mock_factory_class.create_all.return_value = [mock_provider]

        mock_request = MagicMock()
        mock_adapter_class.adapt.return_value = mock_request

        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[],
        )
        mock_strategy = MagicMock()
        mock_strategy.execute_normal.return_value = mock_result
        mock_strategy_class.return_value = mock_strategy

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query"])

        assert result.exit_code == 0
        # 配置关闭 + CLI 不指定 → 应调用 execute_normal
        mock_strategy.execute_normal.assert_called_once()
        mock_strategy.execute_comparison.assert_not_called()

    @patch("melodyi_web.application.cli.ProviderFactory")
    @patch("melodyi_web.application.cli.ParameterAdapter")
    @patch("melodyi_web.application.cli.ExecutionStrategy")
    @patch("melodyi_web.application.cli.load_config")
    def test_search_error(
        self,
        mock_load_config,
        mock_strategy_class,
        mock_adapter_class,
        mock_factory_class,
    ):
        """测试搜索错误处理"""
        mock_provider_config = ProviderConfig(
            name="tavily",
            api_key="test-key",
            timeout_ms=10000,
            max_results=10,
        )
        mock_config = Config(
            providers=[mock_provider_config],
            mode=ModeConfig(),
            fallback=FallbackConfig(),
        )
        mock_load_config.return_value = mock_config

        mock_provider = MagicMock()
        mock_provider.name = "tavily"
        mock_factory_class.create_all.return_value = [mock_provider]

        mock_request = MagicMock()
        mock_adapter_class.adapt.return_value = mock_request

        mock_result = UnifiedSearchResult(
            provider="tavily",
            response_time_ms=100,
            results=[],
            error=SearchError(
                error_type="TEST_ERROR",
                original_message="Test error message",
                guidance="Try again later",
            ),
        )
        mock_strategy = MagicMock()
        mock_strategy.execute_normal.return_value = mock_result
        mock_strategy_class.return_value = mock_strategy

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query"])

        assert result.exit_code == 0  # Error is still a successful CLI execution
        assert "搜索失败" in result.output or "error" in result.output.lower()

    @patch("melodyi_web.application.cli.load_config")
    def test_search_config_not_found(self, mock_load_config):
        """测试配置文件不存在"""
        mock_load_config.side_effect = FileNotFoundError("Config not found")

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query"])

        assert result.exit_code == 1


class TestMainFunction:
    """main 函数测试"""

    @patch("melodyi_web.application.cli.cli")
    def test_main_calls_cli(self, mock_cli):
        """测试 main 函数调用 cli"""
        main()
        mock_cli.assert_called_once()


class TestCliIntegration:
    """CLI 集成测试（不使用 mock 的基础测试）"""

    def test_cli_group_structure(self):
        """测试 CLI 命令组结构"""
        # 验证主命令
        assert cli.name == "cli" or cli.name is None

        # 验证子命令存在
        commands = cli.list_commands(None)
        assert "search" in commands
        assert "config" in commands

    def test_search_command_parameters(self):
        """测试 search 命令参数"""
        search_cmd = cli.get_command(None, "search")
        assert search_cmd is not None

        # 检查参数定义
        params = {p.name for p in search_cmd.params}
        assert "query" in params
        assert "max_results" in params
        assert "time_range" in params
        assert "include_domains" in params
        assert "exclude_domains" in params
        assert "provider" in params
        assert "comparison" in params
        assert "output" in params
        assert "config_path" in params

    def test_config_show_command_parameters(self):
        """测试 config show 命令参数"""
        config_cmd = cli.get_command(None, "config")
        show_cmd = config_cmd.get_command(None, "show")
        assert show_cmd is not None

        params = {p.name for p in show_cmd.params}
        assert "config_path" in params
        assert "output" in params