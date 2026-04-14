"""CLI 测试

测试 click 命令行界面。
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from melodyi_search.application.cli import cli, main
from melodyi_search.domain.models.search_result import UnifiedSearchResult, SearchResultItem, SearchError
from melodyi_search.domain.models.provider_config import ProviderConfig
from melodyi_search.infrastructure.config.config_schema import Config, ModeConfig, FallbackConfig


class TestCliHelp:
    """CLI 帮助信息测试"""

    def test_main_help(self):
        """测试主命令 --help"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "melodyi-search" in result.output
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
        assert "melodyi-search" in result.output
        assert "0.1.0" in result.output


class TestConfigShow:
    """config show 命令测试"""

    @patch("melodyi_search.application.cli.load_config")
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

    @patch("melodyi_search.application.cli.load_config")
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

    @patch("melodyi_search.application.cli.ProviderFactory")
    @patch("melodyi_search.application.cli.ParameterAdapter")
    @patch("melodyi_search.application.cli.ExecutionStrategy")
    @patch("melodyi_search.application.cli.load_config")
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

    @patch("melodyi_search.application.cli.ProviderFactory")
    @patch("melodyi_search.application.cli.ParameterAdapter")
    @patch("melodyi_search.application.cli.ExecutionStrategy")
    @patch("melodyi_search.application.cli.load_config")
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

    @patch("melodyi_search.application.cli.ProviderFactory")
    @patch("melodyi_search.application.cli.ParameterAdapter")
    @patch("melodyi_search.application.cli.ExecutionStrategy")
    @patch("melodyi_search.application.cli.load_config")
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

    @patch("melodyi_search.application.cli.ProviderFactory")
    @patch("melodyi_search.application.cli.ParameterAdapter")
    @patch("melodyi_search.application.cli.ExecutionStrategy")
    @patch("melodyi_search.application.cli.load_config")
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

    @patch("melodyi_search.application.cli.load_config")
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

    @patch("melodyi_search.application.cli.ProviderFactory")
    @patch("melodyi_search.application.cli.ParameterAdapter")
    @patch("melodyi_search.application.cli.ExecutionStrategy")
    @patch("melodyi_search.application.cli.load_config")
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

    @patch("melodyi_search.application.cli.ProviderFactory")
    @patch("melodyi_search.application.cli.ParameterAdapter")
    @patch("melodyi_search.application.cli.ExecutionStrategy")
    @patch("melodyi_search.application.cli.load_config")
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

    @patch("melodyi_search.application.cli.load_config")
    def test_search_config_not_found(self, mock_load_config):
        """测试配置文件不存在"""
        mock_load_config.side_effect = FileNotFoundError("Config not found")

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query"])

        assert result.exit_code == 1


class TestMainFunction:
    """main 函数测试"""

    @patch("melodyi_search.application.cli.cli")
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