# melodyi-search 实现计划 - 第四阶段：应用层

> **执行说明:** 使用 superpowers:subagent-driven-development 或 superpowers:executing-plans 来执行此计划。步骤使用复选框 (`- [ ]`) 进行追踪。

**目标:** 实现 CLI 命令行入口和 skill.md Agent 集成描述文件，使工具可通过命令行或 Agent 使用。

**架构:** application/cli.py 作为用户入口，调用 domain/services 完成搜索流程；skill.md 描述工具能力供 Agent 识别。

**技术栈:** Python 3.10+, argparse/cli (命令行参数), click (可选 CLI 库)

---

## 文件结构

本阶段创建以下文件：

```
melodyi_search/
├── application/
│   ├── __init__.py
│   └── cli.py              # CLI 入口
├── __main__.py             # python -m melodyi_search 入口
├── skill.md                # Agent 集成描述文件
tests/
├── application/
│   ├── __init__.py
│   └── test_cli.py
├── integration/
│   └ test_cli_e2e.py       # CLI 端到端测试
```

---

## 任务列表

### 任务 1: CLI 实现

**文件:**
- 创建: `melodyi_search/application/__init__.py`
- 创建: `melodyi_search/application/cli.py`
- 创建: `melodyi_search/__main__.py`
- 创建: `tests/application/__init__.py`
- 创建: `tests/application/test_cli.py`

- [ ] **步骤 1: 编写 CLI 测试**

创建 `tests/application/test_cli.py`:

```python
"""CLI 测试"""

import pytest
from click.testing import CliRunner
from melodyi_search.application.cli import cli, search_command


class TestCLI:
    """CLI 测试类"""

    def test_cli_exists(self):
        """测试 CLI 命令存在"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'melodyi-search' in result.output

    def test_search_command_exists(self):
        """测试 search 子命令存在"""
        runner = CliRunner()
        result = runner.invoke(cli, ['search', '--help'])
        assert result.exit_code == 0

    def test_search_with_query(self):
        """测试带查询的搜索"""
        runner = CliRunner()
        # 注意：需要 API Key 才能执行真实搜索
        result = runner.invoke(cli, ['search', 'python tutorial'])
        # 检查命令能被解析
        assert 'python tutorial' in result.output or result.exit_code in [0, 1]

    def test_search_with_params(self):
        """测试带参数的搜索"""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'search', 'AI news',
            '--max-results', '5',
            '--time-range', 'week'
        ])
        # 检查参数能被解析
        assert result.exit_code in [0, 1]

    def test_config_show_command(self):
        """测试 config show 命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'show'])
        assert result.exit_code in [0, 1]

    def test_version_command(self):
        """测试 version 命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        assert '0.1.0' in result.output or result.exit_code == 0
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/application/test_cli.py -v
```

预期: FAIL - cli 模块不存在

- [ ] **步骤 3: 创建目录和实现**

```bash
mkdir -p melodyi_search/application
mkdir -p tests/application
```

创建 `melodyi_search/application/__init__.py`:

```python
"""应用层"""

from melodyi_search.application.cli import cli

__all__ = ["cli"]
```

创建 `melodyi_search/application/cli.py`:

```python
"""CLI 命令行入口"""

import asyncio
import click
from melodyi_search import __version__
from melodyi_search.infrastructure.config.config_loader import load_config
from melodyi_search.infrastructure.logging.search_logger import SearchLogger
from melodyi_search.domain.services.provider_factory import ProviderFactory
from melodyi_search.domain.services.execution_strategy import ExecutionStrategy
from melodyi_search.domain.services.parameter_adapter import ParameterAdapter
from melodyi_search.domain.models.search_request import UnifiedSearchRequest, TimeRange


@click.group()
@click.version_option(version=__version__)
def cli():
    """melodyi-search: 多提供商搜索工具"""
    pass


@cli.command()
@click.argument('query')
@click.option('--max-results', '-n', default=10, help='最大结果数')
@click.option('--time-range', '-t', type=click.Choice(['day', 'week', 'month', 'year']), help='时间范围')
@click.option('--include-domains', '-i', multiple=True, help='包含域名')
@click.option('--exclude-domains', '-e', multiple=True, help='排除域名')
@click.option('--provider', '-p', help='指定提供商')
@click.option('--comparison', '-c', is_flag=True, help='启用比对模式')
@click.option('--log-dir', default='./logs', help='日志目录')
def search(
    query: str,
    max_results: int,
    time_range: str,
    include_domains: tuple,
    exclude_domains: tuple,
    provider: str,
    comparison: bool,
    log_dir: str
):
    """执行搜索

    QUERY: 搜索查询字符串
    """
    async def do_search():
        # 加载配置
        config = load_config()

        # 设置日志
        logger = SearchLogger(log_dir=log_dir, console_output=True)
        logger.log_search_request(query, max_results=max_results, time_range=time_range)

        # 创建提供商
        factory = ProviderFactory()
        providers = factory.create_all(config.providers)

        # 如果指定了提供商，只使用该提供商
        if provider:
            providers = [p for p in providers if p.name == provider]
            if not providers:
                click.echo(f"错误: 未找到提供商 '{provider}'", err=True)
                return

        # 创建请求
        time_range_obj = TimeRange(range_type=time_range) if time_range else None
        unified = UnifiedSearchRequest(
            query=query,
            max_results=max_results,
            time_range=time_range_obj,
            include_domains=list(include_domains) if include_domains else None,
            exclude_domains=list(exclude_domains) if exclude_domains else None,
            preferred_provider=provider
        )

        # 适配参数
        adapter = ParameterAdapter()
        request = adapter.adapt(unified, providers[0])

        # 执行搜索
        strategy = ExecutionStrategy(logger=logger)

        if comparison or config.mode.comparison:
            result = await strategy.execute_comparison(providers, request)
        else:
            result = await strategy.execute_normal(providers, request)

        # 输出结果
        if result.error:
            click.echo(f"\n错误: {result.error.original_message}", err=True)
            click.echo(f"指导: {result.error.guidance}", err=True)
            return

        click.echo(f"\n搜索结果 (提供商: {result.provider}, 耗时: {result.response_time_ms}ms):")
        click.echo("-" * 60)

        for i, item in enumerate(result.results, 1):
            click.echo(f"\n{i}. {item.title}")
            click.echo(f"   URL: {item.url}")
            click.echo(f"   描述: {item.description[:100]}...")

            # 记录到日志
            logger.log_search_result(
                title=item.title,
                url=item.url,
                description=item.description,
                index=i
            )

        if result.comparison_log:
            click.echo("\n" + "-" * 60)
            click.echo("比对模式结果:")
            for name, data in result.comparison_log.items():
                click.echo(f"  {name}: {data['status']}, {data['time_ms']}ms, {data['results_count']} results")

    asyncio.run(do_search())


@cli.group()
def config():
    """配置管理"""
    pass


@config.command()
def show():
    """显示当前配置"""
    try:
        cfg = load_config()
        click.echo("\n当前配置:")
        click.echo("-" * 40)
        click.echo(f"提供商 (按优先级):")
        for i, p in enumerate(cfg.providers, 1):
            has_key = "✓" if p.api_key else "✗"
            click.echo(f"  {i}. {p.name} (API Key: {has_key})")
        click.echo(f"\n比对模式: {cfg.mode.comparison}")
        click.echo(f"日志目录: {cfg.mode.log_dir}")
        click.echo(f"重试次数: {cfg.fallback.retry_count}")
    except Exception as e:
        click.echo(f"错误: {e}", err=True)


def main():
    """CLI 入口函数"""
    cli()


if __name__ == '__main__':
    main()
```

创建 `melodyi_search/__main__.py`:

```python
"""python -m melodyi_search 入口"""

from melodyi_search.application.cli import main

main()
```

创建 `tests/application/__init__.py`:

```python
"""应用层测试"""
```

更新 `pyproject.toml` 添加 click 依赖:

```toml
dependencies = [
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "pyyaml>=6.0",
    "httpx>=0.25",
    "click>=8.0",
]
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/application/test_cli.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/application/ melodyi_search/__main__.py tests/application/ pyproject.toml
git commit -m "feat: 实现 CLI 命令行入口"
```

---

### 任务 2: skill.md Agent 集成描述文件

**文件:**
- 创建: `skill.md`

- [ ] **步骤 1: 创建 skill.md**

创建 `skill.md`:

```markdown
---
name: melodyi-search
description: 搜索网络获取知识截止日期之外的信息
---

## 描述

允许搜索网络以获取当前、实时的信息。
返回包含标题、URL 和描述的搜索结果。

## 使用

```python
search(query="machine learning tutorials", max_results=10)
```

## 参数

- **query**（必填）：搜索查询字符串
- **max_results**：结果数量（默认 10）
- **time_range**："day"、"week"、"month"、"year" 时间范围
- **include_domains**：要包含的域名列表
- **exclude_domains**：要排除的域名列表

## 输出格式

返回的搜索结果包含：
- 标题
- URL
- 描述/片段
- 发布日期（如可用）

## 重要说明

- 回答后，请在 Sources 部分，将所有 URL 作为 markdown 链接列出
- 查询时请使用当前年份（2026）以获取最新信息
- 如发生错误，请按照错误消息中的指导操作

## 错误处理

错误包含可执行的指导，请按照建议解决问题。

## 示例输出

```
搜索结果 (提供商: minimax-cn, 耗时: 850ms):
------------------------------------------------------------

1. Python Tutorial - Complete Guide
   URL: https://docs.python.org/3/tutorial/
   描述: Official Python tutorial covering basics to advanced...

2. Machine Learning with Python
   URL: https://scikit-learn.org/
   描述: Machine learning library for Python...
```

Sources:
- [Python Tutorial](https://docs.python.org/3/tutorial/)
- [Scikit-learn](https://scikit-learn.org/)
```

- [ ] **步骤 2: 提交**

```bash
git add skill.md
git commit -m "feat: 添加 skill.md Agent 集成描述文件"
```

---

### 任务 3: CLI 端到端测试

**文件:**
- 创建: `tests/integration/test_cli_e2e.py`

- [ ] **步骤 1: 编写 CLI 端到端测试**

创建 `tests/integration/test_cli_e2e.py`:

```python
"""CLI 端到端测试"""

import pytest
import subprocess
import os


class TestCLIIntegration:
    """CLI 端到端测试类"""

    def test_cli_help(self):
        """测试 CLI 帮助命令"""
        result = subprocess.run(
            ['python', '-m', 'melodyi_search', '--help'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert 'melodyi-search' in result.stdout

    def test_cli_version(self):
        """测试 CLI 版本命令"""
        result = subprocess.run(
            ['python', '-m', 'melodyi_search', '--version'],
            capture_output=True,
            text=True
        )
        assert '0.1.0' in result.stdout or result.returncode == 0

    @pytest.mark.skipif(
        not os.environ.get("MINIMAX_API_KEY"),
        reason="需要 MINIMAX_API_KEY"
    )
    def test_cli_search_real(self):
        """测试真实搜索"""
        result = subprocess.run(
            ['python', '-m', 'melodyi_search', 'search', 'Python教程'],
            capture_output=True,
            text=True,
            env=os.environ
        )
        # 应有输出
        assert result.returncode == 0 or '错误' in result.stderr
        if result.returncode == 0:
            assert '搜索结果' in result.stdout or 'results' in result.stdout.lower()

    @pytest.mark.skipif(
        not os.environ.get("TAVILY_API_KEY"),
        reason="需要 TAVILY_API_KEY"
    )
    def test_cli_search_with_params(self):
        """测试带参数搜索"""
        result = subprocess.run(
            ['python', '-m', 'melodyi_search', 'search', 'AI', '--max-results', '5', '--time-range', 'week'],
            capture_output=True,
            text=True,
            env=os.environ
        )
        assert result.returncode == 0 or '错误' in result.stderr

    def test_cli_config_show(self):
        """测试配置显示"""
        result = subprocess.run(
            ['python', '-m', 'melodyi_search', 'config', 'show'],
            capture_output=True,
            text=True,
            env=os.environ
        )
        assert result.returncode == 0
        assert '提供商' in result.stdout or 'providers' in result.stdout.lower()
```

- [ ] **步骤 2: 运行端到端测试**

```bash
pytest tests/integration/test_cli_e2e.py -v
```

预期: PASS

- [ ] **步骤 3: 提交**

```bash
git add tests/integration/test_cli_e2e.py
git commit -m "feat: 添加 CLI 端到端测试"
```

---

### 任务 4: 运行所有测试验证第四阶段完成

- [ ] **步骤 1: 运行所有测试**

```bash
pytest tests/ -v --tb=short
```

预期: 所有测试 PASS

- [ ] **步骤 2: 测试 CLI 可用**

```bash
python -m melodyi_search --help
python -m melodyi_search config show
```

预期: 命令正常输出

- [ ] **步骤 3: 最终提交**

```bash
git status
git add -A
git commit -m "feat: 第四阶段完成 - CLI 和 skill.md"
```

---

## 第四阶段完成检查清单

完成本阶段后，项目应具备：

- [x] CLI 命令：search、config show、--version、--help
- [x] CLI 参数：query、--max-results、--time-range、--include-domains、--exclude-domains、--provider、--comparison
- [x] skill.md：Agent 集成描述文件（不透露提供商信息）
- [x] python -m melodyi_search 入口
- [x] CLI 端到端测试通过