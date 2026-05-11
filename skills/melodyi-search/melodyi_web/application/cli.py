"""CLI 命令行入口

使用 click 实现命令行界面，支持：
- melodyi-web search <query> [--max-results] [--time-range] ...
- melodyi-web config show
- melodyi-web --version
"""

import json
import sys
from typing import List, Optional

import click

from melodyi_web import __version__
from melodyi_web.domain.models.search_request import UnifiedSearchRequest, TimeRange
from melodyi_web.domain.services.execution_strategy import ExecutionStrategy
from melodyi_web.domain.services.parameter_adapter import ParameterAdapter
from melodyi_web.domain.services.provider_factory import ProviderFactory
from melodyi_web.infrastructure.config.config_loader import load_config
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
from melodyi_web.infrastructure.database.database_manager import DatabaseManager


@click.group()
@click.version_option(version=__version__, prog_name="melodyi-web")
def cli():
    """melodyi-web: 多提供商搜索与网页抓取工具"""
    pass


@cli.command()
@click.argument("query", required=True)
@click.option(
    "--max-results",
    "-n",
    type=int,
    default=10,
    help="期望最大结果数 (默认: 10)",
)
@click.option(
    "--time-range",
    "-t",
    type=click.Choice(["day", "week", "month", "year"]),
    default=None,
    help="时间范围过滤: day, week, month, year",
)
@click.option(
    "--include-domains",
    "-i",
    multiple=True,
    help="仅搜索指定域名 (可多次使用)",
)
@click.option(
    "--exclude-domains",
    "-e",
    multiple=True,
    help="排除指定域名 (可多次使用)",
)
@click.option(
    "--provider",
    "-p",
    type=str,
    default=None,
    help="指定使用的提供商",
)
@click.option(
    "--comparison",
    "-c",
    is_flag=True,
    default=False,
    help="比对模式：第一个提供商立即返回，其余后台执行",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="输出格式: text 或 json (默认: text)",
)
@click.option(
    "--config",
    "-f",
    "config_path",
    type=click.Path(exists=True),
    default=None,
    help="配置文件路径",
)
def search(
    query: str,
    max_results: int,
    time_range: Optional[str],
    include_domains: tuple,
    exclude_domains: tuple,
    provider: Optional[str],
    comparison: bool,
    output: str,
    config_path: Optional[str],
):
    """执行搜索

    QUERY 是搜索关键词，必填参数。

    示例:
        melodyi-web search "Python教程"
        melodyi-web search "AI新闻" --max-results 20 --time-range day
        melodyi-web search "技术博客" --include-domains blog.csdn.net -i juejin.cn
    """
    try:
        # 1. 加载配置
        config = load_config(config_path)

        # 2. 构建统一搜索请求
        time_range_obj = None
        if time_range:
            time_range_obj = TimeRange(range_type=time_range)

        unified_request = UnifiedSearchRequest(
            query=query,
            max_results=max_results,
            time_range=time_range_obj,
            include_domains=list(include_domains) if include_domains else None,
            exclude_domains=list(exclude_domains) if exclude_domains else None,
            preferred_provider=provider,
        )

        # 3. 获取提供商配置
        if provider:
            provider_config = config.get_provider_by_name(provider)
            if not provider_config:
                click.echo(f"错误: 未找到提供商 '{provider}'", err=True)
                click.echo(f"可用提供商: {', '.join(config.get_provider_names())}", err=True)
                sys.exit(1)
            provider_configs = [provider_config]
        else:
            provider_configs = config.providers

        # 验证提供商列表非空
        if not provider_configs:
            click.echo("错误: 配置文件中未定义任何提供商", err=True)
            sys.exit(1)

        # 4. 创建提供商实例
        providers = ProviderFactory.create_all(provider_configs)

        # 5. 适配请求参数
        provider_requests = [
            ParameterAdapter.adapt(unified_request, p) for p in providers
        ]

        # 6. 执行搜索
        # D-05: CLI 参数覆盖配置开关
        # 配置关闭时，CLI 指定 --comparison 则启用
        # 配置开启时，CLI 不指定则默认启用
        use_comparison = comparison or config.mode.comparison

        strategy = ExecutionStrategy()
        if use_comparison:
            # 创建 DatabaseManager 和 ComparisonRecorder
            db_manager = DatabaseManager(config.database)
            try:
                db_manager.init_database()  # D-01: Lazy initialization
                recorder = ComparisonRecorder(db_manager)
            except Exception as e:
                click.echo(f"数据库初始化失败: {e}", err=True)
                click.echo("请检查数据库路径配置和权限", err=True)
                sys.exit(1)
            try:
                result = strategy.execute_comparison(providers, provider_requests[0], recorder)
            finally:
                # 确保数据库连接关闭
                if hasattr(db_manager, 'close'):
                    db_manager.close()
        else:
            result = strategy.execute_normal(providers, provider_requests[0])

        # 7. 输出结果
        if output == "json":
            _output_json(result)
        else:
            _output_text(result)

    except FileNotFoundError as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"配置错误: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"搜索失败: {e}", err=True)
        sys.exit(1)


@cli.group()
def config():
    """配置管理命令"""
    pass


@config.command("show")
@click.option(
    "--config",
    "-f",
    "config_path",
    type=click.Path(exists=True),
    default=None,
    help="配置文件路径",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="输出格式: text 或 json (默认: text)",
)
def config_show(config_path: Optional[str], output: str):
    """显示当前配置

    示例:
        melodyi-web config show
        melodyi-web config show --output json
    """
    try:
        config = load_config(config_path)

        if output == "json":
            config_dict = config.model_dump(mode="python")
            # 隐藏敏感信息
            for provider in config_dict.get("providers", []):
                if provider.get("api_key"):
                    provider["api_key"] = "***"
            click.echo(json.dumps(config_dict, indent=2, ensure_ascii=False))
        else:
            click.echo("提供商配置:")
            for p in config.providers:
                api_key_display = "***" if p.api_key else "(未设置)"
                click.echo(f"  - {p.name}:")
                click.echo(f"      api_key: {api_key_display}")
                click.echo(f"      host: {p.host or '(默认)'}")
                click.echo(f"      timeout_ms: {p.timeout_ms}")
                click.echo(f"      max_results: {p.max_results}")

            click.echo(f"\n运行模式:")
            click.echo(f"  comparison: {config.mode.comparison}")
            click.echo(f"  log_dir: {config.mode.log_dir}")

            click.echo(f"\n回退配置:")
            click.echo(f"  retry_count: {config.fallback.retry_count}")
            click.echo(f"  retry_delay_ms: {config.fallback.retry_delay_ms}")

    except FileNotFoundError as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"读取配置失败: {e}", err=True)
        sys.exit(1)


def _output_text(result):
    """文本格式输出"""
    if result.error:
        click.echo(f"搜索失败 [{result.provider}]: {result.error.original_message}")
        click.echo(f"提示: {result.error.guidance}")
        return

    click.echo(f"提供商: {result.provider}")
    click.echo(f"响应时间: {result.response_time_ms}ms")
    click.echo(f"结果数: {len(result.results)}")

    # D-03/D-07: 不输出 comparison_log，保持与普通 search 一致
    if result.results:
        click.echo(f"\n搜索结果:")
        for i, item in enumerate(result.results, 1):
            click.echo(f"\n[{i}] {item.title}")
            click.echo(f"    URL: {item.url}")
            if item.description:
                desc = item.description[:100] + "..." if len(item.description) > 100 else item.description
                click.echo(f"    描述: {desc}")
            if item.published_date:
                click.echo(f"    日期: {item.published_date.strftime('%Y-%m-%d')}")


def _output_json(result):
    """JSON 格式输出"""
    result_dict = result.model_dump(mode="python")
    # D-06: 移除 session_id，仅保留数据库记录
    result_dict.pop("session_id", None)
    click.echo(json.dumps(result_dict, indent=2, ensure_ascii=False, default=str))


def main():
    """CLI 入口函数"""
    cli()


if __name__ == "__main__":
    main()