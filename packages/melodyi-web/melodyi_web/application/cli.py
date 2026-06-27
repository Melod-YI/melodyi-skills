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
from melodyi_web.domain.models.fetch_request import FetchRequest
from melodyi_web.domain.models.fetch_provider_config import FetchProviderConfig
from melodyi_web.domain.services.execution_strategy import ExecutionStrategy
from melodyi_web.domain.services.parameter_adapter import ParameterAdapter
from melodyi_web.domain.services.provider_factory import ProviderFactory
from melodyi_web.domain.services.fetch_provider_factory import FetchProviderFactory
from melodyi_web.domain.services.fetch_executor import FetchExecutionStrategy
from melodyi_web.infrastructure.config.config_loader import load_config
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.providers.fetch.base_fetch_provider import ProviderFetchRequest


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

        # 3. 获取供应商配置
        if provider:
            provider_config = config.get_search_provider_by_name(provider)
            if not provider_config:
                click.echo(f"错误: 未找到搜索供应商 '{provider}'", err=True)
                click.echo(f"可用供应商: {', '.join(config.get_search_provider_names())}", err=True)
                sys.exit(1)
            provider_configs = [provider_config]
        else:
            provider_configs = config.search_providers

        # 验证供应商列表非空
        if not provider_configs:
            click.echo("错误: 未配置任何搜索供应商", err=True)
            click.echo("请运行 'melodyi-web config init' 创建配置文件", err=True)
            click.echo("然后编辑 ~/.melodyi-skills/melodyi-web/config.yaml 添加 search_providers", err=True)
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


@cli.command()
@click.argument("url", required=True)
@click.option(
    "--provider",
    "-p",
    type=str,
    default=None,
    help="指定使用的供应商",
)
@click.option(
    "--comparison",
    "-c",
    is_flag=True,
    default=False,
    help="比对模式：第一个供应商立即返回，其余后台执行",
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
def fetch(
    url: str,
    provider: Optional[str],
    comparison: bool,
    output: str,
    config_path: Optional[str],
):
    """执行网页抓取

    URL 是目标网址，必填参数。

    示例:
        melodyi-web fetch https://example.com
        melodyi-web fetch https://example.com --provider jina-reader
        melodyi-web fetch https://example.com --comparison
    """
    try:
        # 1. 加载配置
        config = load_config(config_path)

        # 2. 构建抓取请求
        fetch_request = FetchRequest(url=url, preferred_provider=provider)

        # 3. 获取供应商配置（优先级：配置文件 > CLI 参数 > 内置默认）
        if config.fetch_providers:
            provider_configs = config.fetch_providers
            if provider:
                # CLI 指定供应商时，只使用该供应商
                provider_config = config.get_fetch_provider_by_name(provider)
                if provider_config:
                    provider_configs = [provider_config]
                else:
                    provider_configs = [FetchProviderConfig(name=provider)]
        elif provider:
            provider_configs = [FetchProviderConfig(name=provider)]
        else:
            # 内置默认（已在 config_loader 中定义）
            provider_configs = [
                FetchProviderConfig(name="jina-reader"),
                FetchProviderConfig(name="markdown-new"),
            ]

        # 4. 创建供应商实例
        providers = FetchProviderFactory.create_all(provider_configs)

        # 5. 执行抓取
        provider_request = ProviderFetchRequest(url=url)

        strategy = FetchExecutionStrategy()
        if comparison:
            db_manager = DatabaseManager(config.database)
            try:
                db_manager.init_database()
                recorder = ComparisonRecorder(db_manager)
                result = strategy.execute_comparison(providers, provider_request, recorder)
            finally:
                if hasattr(db_manager, 'close'):
                    db_manager.close()
        else:
            result = strategy.execute_normal(providers, provider_request)

        # 6. 输出结果
        if output == "json":
            _output_fetch_json(result)
        else:
            _output_fetch_text(result)

    except Exception as e:
        click.echo(f"抓取失败: {e}", err=True)
        sys.exit(1)


@cli.group()
def config():
    """配置管理命令"""
    pass


@config.command("init")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="强制覆盖已存在的配置文件",
)
def config_init(force: bool):
    """创建默认配置文件

    在 ~/.melodyi-skills/melodyi-web/ 目录下创建默认配置文件。

    示例:
        melodyi-web config init
        melodyi-web config init --force  # 覆盖已存在的配置
    """
    from pathlib import Path

    from melodyi_web.infrastructure.config.config_loader import USER_CONFIG_DIR

    config_dir = USER_CONFIG_DIR
    config_file = config_dir / "config.yaml"

    if config_file.exists() and not force:
        click.echo(f"配置文件已存在: {config_file}")
        click.echo("使用 --force 选项覆盖，或使用 'config show' 查看当前配置")
        return

    # 创建目录
    config_dir.mkdir(parents=True, exist_ok=True)

    # 完整配置文件内容（带注释）
    config_content = """# melodyi-web 配置文件

# ====================
# 搜索供应商配置
# ====================
# 支持的供应商: minimax-cn, tavily, brave, exa, searxng, firecrawl
# 供应商按顺序执行，第一个成功即返回，失败则回退到下一个
search_providers:
  # Tavily - 高质量搜索 API
  # - name: tavily
  #   api_key: ${TAVILY_API_KEY}   # 从环境变量读取，或直接填写
  #   timeout_ms: 10000
  #   max_results: 20
  #   extra_params:
  #     depth: basic              # basic 或 advanced

  # Brave Search
  # - name: brave
  #   api_key: ${BRAVE_API_KEY}
  #   timeout_ms: 10000
  #   max_results: 20

  # Exa - AI 语义搜索
  # - name: exa
  #   api_key: ${EXA_API_KEY}
  #   timeout_ms: 30000
  #   max_results: 10
  #   extra_params:
  #     type: auto                # auto, keyword, neural

  # MiniMax CN - 中国区域搜索
  # - name: minimax-cn
  #   api_key: ${MINIMAX_API_KEY}
  #   timeout_ms: 10000
  #   max_results: 10

  # SearXNG - 自托管搜索（需配置 host）
  # - name: searxng
  #   host: http://localhost:8888
  #   timeout_ms: 10000
  #   max_results: 10

  # Firecrawl - 自托管搜索+抓取（需配置 host）
  # - name: firecrawl
  #   host: http://localhost:3002
  #   api_key: ${FIRECRAW_API_KEY}
  #   timeout_ms: 10000
  #   max_results: 10

# ====================
# 抓取供应商配置
# ====================
# 支持的供应商: jina, markdown-new, tavily-extract, exa-contents
# jina 和 markdown-new 无需 API Key，可直接使用
fetch_providers:
  - name: jina
    timeout_ms: 15000
    # api_key: ${JINA_API_KEY}    # 可选，提升速率限制
    # extra_params:
    #   engine: browser           # browser（支持JS）或 direct（更快）
    #   with_summary: true        # 生成摘要
    #   with_links: true          # 保留链接
    #   remove_selector: nav,footer  # CSS 选择器，移除元素
    #   include_selector: article   # CSS 选择器，仅包含指定元素

  - name: markdown-new
    timeout_ms: 15000

  # Tavily Extract - 需要 API Key
  # - name: tavily-extract
  #   api_key: ${TAVILY_API_KEY}
  #   timeout_ms: 10000
  #   extra_params:
  #     extract_depth: basic      # basic 或 advanced

  # Exa Contents - 需要 API Key
  # - name: exa-contents
  #   api_key: ${EXA_API_KEY}
  #   timeout_ms: 30000

# ====================
# 运行模式配置
# ====================
mode:
  # 比对模式：第一个供应商立即返回，其余后台执行并记录
  # 用于分析供应商质量差异
  comparison: false
  log_dir: ${HOME}/.melodyi-skills/melodyi-web/logs

# ====================
# 回退配置
# ====================
fallback:
  retry_count: 2          # 每个供应商失败后重试次数
  retry_delay_ms: 1000    # 重试间隔（毫秒）

# ====================
# 数据库配置
# ====================
# 比对模式下存储结果数据
database:
  database_path: ${HOME}/.melodyi-skills/melodyi-web/data/compare.db

# ====================
# 环境变量说明
# ====================
# 创建 ~/.melodyi-skills/melodyi-web/.env 文件存放 API Key：
#
# TAVILY_API_KEY=tvly-xxxxx
# BRAVE_API_KEY=xxxxx
# EXA_API_KEY=xxxxx
# MINIMAX_API_KEY=xxxxx
# JINA_API_KEY=xxxxx
# FIRECRAW_API_KEY=xxxxx
#
# 或直接在 YAML 中填写 api_key 值（不推荐，有安全风险）
"""

    # 写入文件
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)

    click.echo(f"配置文件已创建: {config_file}")
    click.echo("\n下一步:")
    click.echo("  1. 编辑配置文件，取消注释需要的供应商")
    click.echo(f"  2. 创建 .env 文件: {config_dir / '.env'}")
    click.echo("  3. 运行 'melodyi-web config show' 验证配置")


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
            for provider in config_dict.get("search_providers", []):
                if provider.get("api_key"):
                    provider["api_key"] = "***"
            for provider in config_dict.get("fetch_providers", []) or []:
                if provider.get("api_key"):
                    provider["api_key"] = "***"
            # 移除废弃字段
            config_dict.pop("providers", None)
            click.echo(json.dumps(config_dict, indent=2, ensure_ascii=False))
        else:
            click.echo("搜索供应商配置:")
            for p in config.search_providers:
                api_key_display = "***" if p.api_key else "(未设置)"
                click.echo(f"  - {p.name}:")
                click.echo(f"      api_key: {api_key_display}")
                click.echo(f"      host: {p.host or '(默认)'}")
                click.echo(f"      timeout_ms: {p.timeout_ms}")
                click.echo(f"      max_results: {p.max_results}")

            click.echo("\n抓取供应商配置:")
            for p in config.fetch_providers or []:
                api_key_display = "***" if p.api_key else "(未设置)"
                click.echo(f"  - {p.name}:")
                click.echo(f"      api_key: {api_key_display}")
                click.echo(f"      host: {p.host or '(默认)'}")
                click.echo(f"      timeout_ms: {p.timeout_ms}")
                if p.extra_params:
                    click.echo(f"      extra_params: {p.extra_params}")

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


def _output_fetch_text(result):
    """文本格式输出 fetch 结果"""
    if result.error:
        click.echo(f"抓取失败 [{result.provider}]: {result.error.original_message}")
        click.echo(f"提示: {result.error.guidance}")
        return

    click.echo(f"供应商: {result.provider}")
    click.echo(f"响应时间: {result.response_time_ms}ms")
    if result.title:
        click.echo(f"标题: {result.title}")
    click.echo(f"\n{result.content}")


def _output_fetch_json(result):
    """JSON 格式输出 fetch 结果"""
    result_dict = result.model_dump(mode="python")
    result_dict.pop("session_id", None)
    click.echo(json.dumps(result_dict, indent=2, ensure_ascii=False))


def main():
    """CLI 入口函数"""
    cli()


if __name__ == "__main__":
    main()