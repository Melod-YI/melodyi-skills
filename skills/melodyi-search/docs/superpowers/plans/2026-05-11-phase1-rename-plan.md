# Phase 1: melodyi-search → melodyi-web 重命名实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 melodyi-search 项目重命名为 melodyi-web，并调整目录结构以支持 search 和 fetch 两个独立领域。

**Architecture:** 
- 包目录重命名: `melodyi_search/` → `melodyi_web/`
- providers 目录拆分: 添加 `search/` 和 `fetch/` 子目录
- 所有 import 路径从 `melodyi_search` 改为 `melodyi_web`
- CLI 命令从 `melodyi-search` 改为 `melodyi-web`

**Tech Stack:** Python 3.10+, Pydantic V2, click CLI, pytest

---

## 文件变更清单

### 目录重命名
| 操作 | 当前路径 | 新路径 |
|------|----------|--------|
| 重命名 | `melodyi_search/` | `melodyi_web/` |
| 新建 | - | `melodyi_web/providers/search/` |
| 新建 | - | `melodyi_web/providers/fetch/` |
| 新建 | - | `tests/providers/search/` |
| 新建 | - | `tests/providers/fetch/` |

### providers 文件移动
| 当前位置 | 新位置 |
|----------|--------|
| `melodyi_search/providers/base_provider.py` | `melodyi_web/providers/search/base_provider.py` |
| `melodyi_search/providers/tavily_provider.py` | `melodyi_web/providers/search/tavily_provider.py` |
| `melodyi_search/providers/brave_provider.py` | `melodyi_web/providers/search/brave_provider.py` |
| `melodyi_search/providers/exa_provider.py` | `melodyi_web/providers/search/exa_provider.py` |
| `melodyi_search/providers/minimax_cn_provider.py` | `melodyi_web/providers/search/minimax_cn_provider.py` |
| `melodyi_search/providers/searxng_provider.py` | `melodyi_web/providers/search/searxng_provider.py` |
| `melodyi_search/providers/firecrawl_provider.py` | `melodyi_web/providers/search/firecrawl_provider.py` |
| `melodyi_search/providers/__init__.py` | `melodyi_web/providers/search/__init__.py` |

### 测试文件移动
| 当前位置 | 新位置 |
|----------|--------|
| `tests/providers/test_base_provider.py` | `tests/providers/search/test_base_provider.py` |
| `tests/providers/test_tavily_provider.py` | `tests/providers/search/test_tavily_provider.py` |
| `tests/providers/test_brave_provider.py` | `tests/providers/search/test_brave_provider.py` |
| `tests/providers/test_exa_provider.py` | `tests/providers/search/test_exa_provider.py` |
| `tests/providers/test_minimax_cn_provider.py` | `tests/providers/search/test_minimax_cn_provider.py` |
| `tests/providers/test_searxng_provider.py` | `tests/providers/search/test_searxng_provider.py` |
| `tests/providers/test_firecrawl_provider.py` | `tests/providers/search/test_firecrawl_provider.py` |
| `tests/providers/__init__.py` | `tests/providers/search/__init__.py` |

---

## Task 1: 创建新目录结构

**Files:**
- Create: `melodyi_web/` (目录)
- Create: `melodyi_web/providers/search/` (目录)
- Create: `melodyi_web/providers/fetch/` (目录)
- Create: `tests/providers/search/` (目录)
- Create: `tests/providers/fetch/` (目录)

- [ ] **Step 1: 创建 melodyi_web 目录结构**

```bash
mkdir -p melodyi_web/providers/search
mkdir -p melodyi_web/providers/fetch
mkdir -p tests/providers/search
mkdir -p tests/providers/fetch
```

- [ ] **Step 2: 复制整个 melodyi_search 目录内容到 melodyi_web**

```bash
cp -r melodyi_search/* melodyi_web/
```

- [ ] **Step 3: 移动 providers 文件到 search 子目录**

```bash
mv melodyi_web/providers/*.py melodyi_web/providers/search/
```

- [ ] **Step 4: 移动 tests/providers 文件到 search 子目录**

```bash
mv tests/providers/test_*.py tests/providers/search/
mv tests/providers/__init__.py tests/providers/search/
```

- [ ] **Step 5: 创建 fetch 子目录的空 __init__.py**

```python
# melodyi_web/providers/fetch/__init__.py
"""Fetch 提供商实现 - 阶段三填充"""

__all__ = []
```

```python
# tests/providers/fetch/__init__.py
"""Fetch 提供商测试 - 阶段三填充"""
```

---

## Task 2: 更新 pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 更新项目名和 CLI 命令**

将 `pyproject.toml` 中以下内容修改：

```toml
[project]
name = "melodyi-web"
version = "0.1.0"
description = "多提供商搜索与网页抓取工具"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "pyyaml>=6.0",
    "httpx>=0.25",
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]

[project.scripts]
melodyi-web = "melodyi_web.application.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["melodyi_web"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## Task 3: 更新 melodyi_web 包顶层 __init__.py

**Files:**
- Modify: `melodyi_web/__init__.py`

- [ ] **Step 1: 更新包描述**

```python
"""melodyi-web: 多提供商搜索与网页抓取工具"""

__version__ = "0.1.0"
```

---

## Task 4: 更新 CLI 模块

**Files:**
- Modify: `melodyi_web/application/cli.py`

- [ ] **Step 1: 更新 CLI 描述和 prog_name**

修改以下位置：

```python
"""CLI 命令行入口

使用 click 实现命令行界面，支持：
- melodyi-web search <query> [--max-results] [--time-range] ...
- melodyi-web config show
- melodyi-web --version
"""
```

```python
@click.group()
@click.version_option(version=__version__, prog_name="melodyi-web")
def cli():
    """melodyi-web: 多提供商搜索与网页抓取工具"""
    pass
```

- [ ] **Step 2: 更新 CLI 示例文档字符串**

```python
    """执行搜索

    QUERY 是搜索关键词，必填参数。

    示例:
        melodyi-web search "Python教程"
        melodyi-web search "AI新闻" --max-results 20 --time-range day
        melodyi-web search "技术博客" --include-domains blog.csdn.net -i juejin.cn
    """
```

```python
    """显示当前配置

    示例:
        melodyi-web config show
        melodyi-web config show --output json
    """
```

---

## Task 5: 更新 providers/search/__init__.py

**Files:**
- Modify: `melodyi_web/providers/search/__init__.py`

- [ ] **Step 1: 更新 import 路径**

```python
"""搜索提供商实现"""

from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
from melodyi_web.providers.search.minimax_cn_provider import MiniMaxCNProvider
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.providers.search.exa_provider import ExaProvider
from melodyi_web.providers.search.searxng_provider import SearXNGProvider
from melodyi_web.providers.search.firecrawl_provider import FirecrawlProvider

__all__ = [
    "BaseProvider",
    "ProviderSearchRequest",
    "ProviderSearchResult",
    "MiniMaxCNProvider",
    "TavilyProvider",
    "BraveProvider",
    "ExaProvider",
    "SearXNGProvider",
    "FirecrawlProvider",
]
```

---

## Task 6: 更新 providers/search/base_provider.py

**Files:**
- Modify: `melodyi_web/providers/search/base_provider.py`

- [ ] **Step 1: 更新 import 路径**

```python
from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
```

---

## Task 7: 更新所有 provider 文件

**Files:**
- Modify: `melodyi_web/providers/search/tavily_provider.py`
- Modify: `melodyi_web/providers/search/brave_provider.py`
- Modify: `melodyi_web/providers/search/exa_provider.py`
- Modify: `melodyi_web/providers/search/minimax_cn_provider.py`
- Modify: `melodyi_web/providers/search/searxng_provider.py`
- Modify: `melodyi_web/providers/search/firecrawl_provider.py`

- [ ] **Step 1: 更新 tavily_provider.py import 路径**

```python
from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

- [ ] **Step 2: 更新 brave_provider.py import 路径**

```python
from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

- [ ] **Step 3: 更新 exa_provider.py import 路径**

```python
from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

- [ ] **Step 4: 更新 minimax_cn_provider.py import 路径**

```python
from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

- [ ] **Step 5: 更新 searxng_provider.py import 路径**

```python
from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

- [ ] **Step 6: 更新 firecrawl_provider.py import 路径**

```python
from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

---

## Task 8: 更新 domain 层所有文件

**Files:**
- Modify: `melodyi_web/domain/models/__init__.py`
- Modify: `melodyi_web/domain/models/search_request.py`
- Modify: `melodyi_web/domain/models/search_result.py`
- Modify: `melodyi_web/domain/models/error.py`
- Modify: `melodyi_web/domain/models/provider_config.py`
- Modify: `melodyi_web/domain/services/__init__.py`
- Modify: `melodyi_web/domain/services/parameter_adapter.py`
- Modify: `melodyi_web/domain/services/provider_factory.py`
- Modify: `melodyi_web/domain/services/execution_strategy.py`
- Modify: `melodyi_web/domain/services/comparison_recorder.py`

- [ ] **Step 1: 更新 domain/models/__init__.py**

```python
"""领域模型"""

from melodyi_web.domain.models.search_request import (
    UnifiedSearchRequest,
    TimeRange,
    TimeRangeType,
)
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.domain.models.error import ProviderError
from melodyi_web.domain.models.provider_config import ProviderConfig

__all__ = [
    "UnifiedSearchRequest",
    "TimeRange",
    "TimeRangeType",
    "SearchResultItem",
    "ProviderError",
    "ProviderConfig",
]
```

- [ ] **Step 2: 更新 domain/models/search_request.py import**

```python
from melodyi_web.domain.models.error import ProviderError
```

- [ ] **Step 3: 更新 domain/models/search_result.py import**

```python
from melodyi_web.domain.models.error import ProviderError
```

- [ ] **Step 4: 更新 domain/services/__init__.py**

```python
"""领域服务"""

from melodyi_web.domain.services.parameter_adapter import ParameterAdapter
from melodyi_web.domain.services.provider_factory import ProviderFactory
from melodyi_web.domain.services.execution_strategy import ExecutionStrategy
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder

__all__ = [
    "ParameterAdapter",
    "ProviderFactory",
    "ExecutionStrategy",
    "ComparisonRecorder",
]
```

- [ ] **Step 5: 更新 domain/services/parameter_adapter.py import**

```python
from melodyi_web.domain.models.search_request import UnifiedSearchRequest, TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

- [ ] **Step 6: 更新 domain/services/provider_factory.py import**

```python
from melodyi_web.domain.models.provider_config import ProviderConfig
from melodyi_web.providers.search.minimax_cn_provider import MiniMaxCNProvider
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.providers.search.exa_provider import ExaProvider
from melodyi_web.providers.search.searxng_provider import SearXNGProvider
from melodyi_web.providers.search.firecrawl_provider import FirecrawlProvider
```

- [ ] **Step 7: 更新 domain/services/execution_strategy.py import**

```python
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
```

- [ ] **Step 8: 更新 domain/services/comparison_recorder.py import**

```python
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.providers.search.base_provider import ProviderSearchResult
from melodyi_web.domain.models.search_request import UnifiedSearchRequest
```

---

## Task 9: 更新 infrastructure 层所有文件

**Files:**
- Modify: `melodyi_web/infrastructure/config/config_schema.py`
- Modify: `melodyi_web/infrastructure/config/config_loader.py`
- Modify: `melodyi_web/infrastructure/database/database_manager.py`
- Modify: `melodyi_web/infrastructure/logging/search_logger.py`

- [ ] **Step 1: 更新 infrastructure/config/config_schema.py import**

```python
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 2: 更新 infrastructure/config/config_loader.py import**

```python
from melodyi_web.infrastructure.config.config_schema import Config
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 3: 更新 infrastructure/database/database_manager.py import**

```python
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
```

- [ ] **Step 4: 更新 database_manager.py 日志 logger 名称**

```python
self._logger = logging.getLogger("melodyi_web.database")
```

- [ ] **Step 5: 更新 infrastructure/logging/search_logger.py logger 名称**

```python
"""搜索日志记录器"""

import logging
from pathlib import Path

logger = logging.getLogger("melodyi_web.search")
```

---

## Task 10: 更新 application/cli.py 所有 import

**Files:**
- Modify: `melodyi_web/application/cli.py`

- [ ] **Step 1: 更新 CLI 所有 import 路径**

```python
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
```

---

## Task 11: 更新 __main__.py

**Files:**
- Modify: `melodyi_web/__main__.py`

- [ ] **Step 1: 更新 import 路径**

```python
"""CLI 入口点 (python -m melodyi_web)"""

from melodyi_web.application.cli import main

if __name__ == "__main__":
    main()
```

---

## Task 12: 更新所有测试文件的 import

**Files:**
- Modify: `tests/__init__.py`
- Modify: `tests/providers/search/__init__.py`
- Modify: `tests/providers/search/test_base_provider.py`
- Modify: `tests/providers/search/test_tavily_provider.py`
- Modify: `tests/providers/search/test_brave_provider.py`
- Modify: `tests/providers/search/test_exa_provider.py`
- Modify: `tests/providers/search/test_minimax_cn_provider.py`
- Modify: `tests/providers/search/test_searxng_provider.py`
- Modify: `tests/providers/search/test_firecrawl_provider.py`
- Modify: `tests/domain/models/test_search_request.py`
- Modify: `tests/domain/models/test_error.py`
- Modify: `tests/domain/models/test_provider_config.py`
- Modify: `tests/domain/models/test_search_result.py`
- Modify: `tests/domain/services/test_parameter_adapter.py`
- Modify: `tests/domain/services/test_provider_factory.py`
- Modify: `tests/domain/services/test_execution_strategy.py`
- Modify: `tests/domain/services/test_comparison_recorder.py`
- Modify: `tests/infrastructure/config/test_config_schema.py`
- Modify: `tests/infrastructure/config/test_config_loader.py`
- Modify: `tests/infrastructure/database/test_database_manager.py`
- Modify: `tests/infrastructure/logging/test_search_logger.py`
- Modify: `tests/infrastructure/http/test_http_client.py`
- Modify: `tests/application/test_cli.py`
- Modify: `tests/integration/test_tavily_e2e.py`
- Modify: `tests/integration/test_exa_e2e.py`
- Modify: `tests/integration/test_brave_e2e.py`
- Modify: `tests/integration/test_minimax_cn_e2e.py`
- Modify: `tests/integration/test_comparison_e2e.py`
- Modify: `tests/integration/test_cli_comparison_e2e.py`

- [ ] **Step 1: 更新 tests/__init__.py**

```python
"""melodyi-web 测试"""
```

- [ ] **Step 2: 更新 tests/providers/search/__init__.py**

```python
"""搜索提供商测试"""
```

- [ ] **Step 3: 更新 tests/providers/search/test_base_provider.py import**

```python
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
from melodyi_web.domain.models.search_request import TimeRange, TimeRangeType
from melodyi_web.domain.models.search_result import SearchResultItem
```

- [ ] **Step 4: 更新 tests/providers/search/test_tavily_provider.py import**

```python
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 5: 更新 tests/providers/search/test_brave_provider.py import**

```python
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 6: 更新 tests/providers/search/test_exa_provider.py import**

```python
from melodyi_web.providers.search.exa_provider import ExaProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 7: 更新 tests/providers/search/test_minimax_cn_provider.py import**

```python
from melodyi_web.providers.search.minimax_cn_provider import MiniMaxCNProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 8: 更新 tests/providers/search/test_searxng_provider.py import**

```python
from melodyi_web.providers.search.searxng_provider import SearXNGProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 9: 更新 tests/providers/search/test_firecrawl_provider.py import**

```python
from melodyi_web.providers.search.firecrawl_provider import FirecrawlProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 10: 更新 tests/domain/models/test_search_request.py import**

```python
from melodyi_web.domain.models.search_request import (
    UnifiedSearchRequest,
    TimeRange,
    TimeRangeType,
)
```

- [ ] **Step 11: 更新 tests/domain/models/test_error.py import**

```python
from melodyi_web.domain.models.error import ProviderError
```

- [ ] **Step 12: 更新 tests/domain/models/test_provider_config.py import**

```python
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 13: 更新 tests/domain/models/test_search_result.py import**

```python
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.domain.models.error import ProviderError
```

- [ ] **Step 14: 更新 tests/domain/services/test_parameter_adapter.py import**

```python
from melodyi_web.domain.services.parameter_adapter import ParameterAdapter
from melodyi_web.domain.models.search_request import UnifiedSearchRequest, TimeRange
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 15: 更新 tests/domain/services/test_provider_factory.py import**

```python
from melodyi_web.domain.services.provider_factory import ProviderFactory
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 16: 更新 tests/domain/services/test_execution_strategy.py import**

```python
from melodyi_web.domain.services.execution_strategy import ExecutionStrategy
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.provider_config import ProviderConfig
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
```

- [ ] **Step 17: 更新 tests/domain/services/test_comparison_recorder.py import**

```python
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
from melodyi_web.providers.search.base_provider import ProviderSearchResult
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.domain.models.search_request import UnifiedSearchRequest
```

- [ ] **Step 18: 更新 tests/infrastructure/config/test_config_schema.py import**

```python
from melodyi_web.infrastructure.config.config_schema import (
    Config,
    ModeConfig,
    FallbackConfig,
    DatabaseConfig,
)
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 19: 更新 tests/infrastructure/config/test_config_loader.py import**

```python
from melodyi_web.infrastructure.config.config_loader import load_config
from melodyi_web.infrastructure.config.config_schema import Config
```

- [ ] **Step 20: 更新 tests/infrastructure/database/test_database_manager.py import**

```python
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
```

- [ ] **Step 21: 更新 tests/infrastructure/logging/test_search_logger.py**

检查是否有 import 需更新（通常是 logger 名称测试）

- [ ] **Step 22: 更新 tests/application/test_cli.py import**

```python
from click.testing import CliRunner
from melodyi_web.application.cli import cli
```

并更新测试断言中的 CLI 名称：

```python
# 将所有 "melodyi-search" 改为 "melodyi-web"
assert "melodyi-web" in result.output
```

- [ ] **Step 23: 更新 tests/integration/test_tavily_e2e.py import**

```python
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 24: 更新 tests/integration/test_exa_e2e.py import**

```python
from melodyi_web.providers.search.exa_provider import ExaProvider
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 25: 更新 tests/integration/test_brave_e2e.py import**

```python
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 26: 更新 tests/integration/test_minimax_cn_e2e.py import**

```python
from melodyi_web.providers.search.minimax_cn_provider import MiniMaxCNProvider
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 27: 更新 tests/integration/test_comparison_e2e.py import**

```python
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.domain.models.provider_config import ProviderConfig
from melodyi_web.domain.services.execution_strategy import ExecutionStrategy
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
```

- [ ] **Step 28: 更新 tests/integration/test_cli_comparison_e2e.py import**

```python
from click.testing import CliRunner
from melodyi_web.application.cli import cli
```

---

## Task 13: 更新配置文件

**Files:**
- Modify: `melodyi_web/infrastructure/config/default_config.yaml`

- [ ] **Step 1: 更新数据目录路径**

```yaml
# melodyi-web 默认配置

mode:
  comparison: false
  log_dir: ${HOME}/.melodyi-web/logs

fallback:
  retry_count: 2
  retry_delay_ms: 1000

database:
  database_path: ${HOME}/.melodyi-web/data/compare.db
```

---

## Task 14: 更新文档文件

**Files:**
- Modify: `CLAUDE.md`
- Modify: `skill.md`
- Modify: `.env.example`
- Modify: `.planning/PROJECT.md`
- Modify: `.planning/ROADMAP.md`
- Modify: `.planning/STATE.md`

- [ ] **Step 1: 更新 CLAUDE.md 项目名**

```markdown
# melodyi-web Project Instructions

此项目使用 Get Shit Done (GSD) 工作流管理。

## Project Context

- **Core Value:** Compare 模式的完整结果记录与持久化 + 网页抓取能力
- **架构:** Search 和 Fetch 两个独立领域，各有多供应商实现
...
```

- [ ] **Step 2: 更新 skill.md**

```markdown
---
name: melodyi-web
description: 多提供商搜索与网页抓取工具，支持 search 和 fetch 两种能力
---

<melodyi-web>
...
```

- [ ] **Step 3: 更新 .env.example**

```bash
# melodyi-web 环境变量模板
...
```

- [ ] **Step 4: 更新 .planning/PROJECT.md 标题**

```markdown
# melodyi-web
...
```

- [ ] **Step 5: 更新 .planning/ROADMAP.md 标题**

```markdown
# ROADMAP: melodyi-web Enhancement
...
```

- [ ] **Step 6: 更新 .planning/STATE.md 项目名**

```markdown
**Project:** melodyi-web Enhancement
...
```

---

## Task 15: 删除旧目录并验证

**Files:**
- Delete: `melodyi_search/` (目录)
- Delete: `tests/providers/test_*.py` (已移动的文件)

- [ ] **Step 1: 删除旧的 melodyi_search 目录**

```bash
rm -rf melodyi_search/
```

- [ ] **Step 2: 删除 tests/providers 目录下的旧文件（已移动到 search/）**

```bash
# 如果 tests/providers 下还有残留的 test_*.py，删除它们
rm tests/providers/test_*.py 2>/dev/null || true
```

- [ ] **Step 3: 运行 pytest 验证所有测试通过**

```bash
pytest tests/ -v
```

Expected: 所有测试通过

- [ ] **Step 4: 验证 CLI 命令可用**

```bash
pip install -e .
melodyi-web --version
```

Expected: 输出 `melodyi-web, version 0.1.0`

- [ ] **Step 5: 验证 search 命令功能正常**

```bash
melodyi-web --help
melodyi-web search --help
melodyi-web config show --help
```

Expected: 所有命令显示正确帮助信息

---

## Task 16: 提交变更

- [ ] **Step 1: 添加所有变更到 git**

```bash
git add -A
git status
```

- [ ] **Step 2: 提交变更**

```bash
git commit -m "$(cat <<'EOF'
refactor: rename melodyi-search to melodyi-web

- Rename package: melodyi_search -> melodyi_web
- Rename CLI command: melodyi-search -> melodyi-web
- Reorganize providers: add search/ and fetch/ subdirectories
- Update all imports from melodyi_search to melodyi_web
- Update data directory: .melodyi-search -> .melodyi-web
- Update documentation and config files

This refactor prepares the project to support both search and fetch
capabilities as independent domains with their own provider implementations.
EOF
)"
```

---

## 验证清单

完成所有 Task 后验证：

- [ ] `pytest tests/ -v` 全部通过
- [ ] `melodyi-web --version` 输出 `melodyi-web, version 0.1.0`
- [ ] `melodyi-web search <query>` 功能正常（使用真实 API Key 测试）
- [ ] `melodyi-web config show` 功能正常
- [ ] 数据目录使用 `~/.melodyi-web/`
- [ ] Git commit 已提交

---

*Created: 2026-05-11*