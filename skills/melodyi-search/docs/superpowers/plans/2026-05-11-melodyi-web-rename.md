# melodyi-web Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename melodyi-search to melodyi-web and restructure providers directory for search/fetch separation.

**Architecture:** Rename Python package directory, create search/fetch subdirectories under providers, update all imports and references.

**Tech Stack:** Python 3.10+, pytest, click CLI

---

## Task 1: Rename Package Directory

**Files:**
- Rename: `melodyi_search/` → `melodyi_web/`

- [ ] **Step 1: Rename the main package directory**

Run:
```bash
cd C:/workspace/melodyi-skills/skills/melodyi-search
mv melodyi_search melodyi_web
```

Expected: Directory `melodyi_web/` exists, `melodyi_search/` removed

- [ ] **Step 2: Verify directory structure**

Run:
```bash
ls melodyi_web/
```

Expected output:
```
__init__.py
__main__.py
application/
domain/
infrastructure/
providers/
```

---

## Task 2: Create Providers Subdirectories

**Files:**
- Create: `melodyi_web/providers/search/`
- Create: `melodyi_web/providers/fetch/`
- Create: `tests/providers/search/`
- Create: `tests/providers/fetch/`

- [ ] **Step 1: Create search subdirectory under providers**

Run:
```bash
cd C:/workspace/melodyi-skills/skills/melodyi-search
mkdir melodyi_web/providers/search
mkdir melodyi_web/providers/fetch
mkdir tests/providers/search
mkdir tests/providers/fetch
```

- [ ] **Step 2: Create __init__.py files for new directories**

Run:
```bash
touch melodyi_web/providers/search/__init__.py
touch melodyi_web/providers/fetch/__init__.py
touch tests/providers/search/__init__.py
touch tests/providers/fetch/__init__.py
```

---

## Task 3: Move Provider Files to search Subdirectory

**Files:**
- Move: All provider files from `melodyi_web/providers/` to `melodyi_web/providers/search/`

Files to move:
- `base_provider.py`
- `tavily_provider.py`
- `brave_provider.py`
- `exa_provider.py`
- `minimax_cn_provider.py`
- `searxng_provider.py`
- `firecrawl_provider.py`

- [ ] **Step 1: Move all provider files to search subdirectory**

Run:
```bash
cd C:/workspace/melodyi-skills/skills/melodyi-search
mv melodyi_web/providers/base_provider.py melodyi_web/providers/search/
mv melodyi_web/providers/tavily_provider.py melodyi_web/providers/search/
mv melodyi_web/providers/brave_provider.py melodyi_web/providers/search/
mv melodyi_web/providers/exa_provider.py melodyi_web/providers/search/
mv melodyi_web/providers/minimax_cn_provider.py melodyi_web/providers/search/
mv melodyi_web/providers/searxng_provider.py melodyi_web/providers/search/
mv melodyi_web/providers/firecrawl_provider.py melodyi_web/providers/search/
```

- [ ] **Step 2: Remove old providers/__init__.py (will be replaced)**

Run:
```bash
rm melodyi_web/providers/__init__.py
```

- [ ] **Step 3: Verify provider files moved correctly**

Run:
```bash
ls melodyi_web/providers/search/
```

Expected output:
```
__init__.py
base_provider.py
tavily_provider.py
brave_provider.py
exa_provider.py
minimax_cn_provider.py
searxng_provider.py
firecrawl_provider.py
```

---

## Task 4: Move Provider Test Files to search Subdirectory

**Files:**
- Move: All provider test files from `tests/providers/` to `tests/providers/search/`

Files to move:
- `test_base_provider.py`
- `test_tavily_provider.py`
- `test_brave_provider.py`
- `test_exa_provider.py`
- `test_minimax_cn_provider.py`
- `test_searxng_provider.py`
- `test_firecrawl_provider.py`

- [ ] **Step 1: Move all provider test files to search subdirectory**

Run:
```bash
cd C:/workspace/melodyi-skills/skills/melodyi-search
mv tests/providers/test_base_provider.py tests/providers/search/
mv tests/providers/test_tavily_provider.py tests/providers/search/
mv tests/providers/test_brave_provider.py tests/providers/search/
mv tests/providers/test_exa_provider.py tests/providers/search/
mv tests/providers/test_minimax_cn_provider.py tests/providers/search/
mv tests/providers/test_searxng_provider.py tests/providers/search/
mv tests/providers/test_firecrawl_provider.py tests/providers/search/
```

- [ ] **Step 2: Remove old tests/providers/__init__.py**

Run:
```bash
rm tests/providers/__init__.py
```

- [ ] **Step 3: Verify test files moved correctly**

Run:
```bash
ls tests/providers/search/
```

Expected output:
```
__init__.py
test_base_provider.py
test_tavily_provider.py
test_brave_provider.py
test_exa_provider.py
test_minimax_cn_provider.py
test_searxng_provider.py
test_firecrawl_provider.py
```

---

## Task 5: Update providers/search/__init__.py

**Files:**
- Modify: `melodyi_web/providers/search/__init__.py`

- [ ] **Step 1: Write the new __init__.py content**

Write to `melodyi_web/providers/search/__init__.py`:
```python
"""Search provider implementations"""

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

## Task 6: Update providers/fetch/__init__.py

**Files:**
- Modify: `melodyi_web/providers/fetch/__init__.py`

- [ ] **Step 1: Write placeholder __init__.py for fetch providers**

Write to `melodyi_web/providers/fetch/__init__.py`:
```python
"""Fetch provider implementations

This module will contain web page fetch/scrape providers.
Currently empty - to be implemented in Phase 3.
"""

__all__ = []
```

---

## Task 7: Update Package __init__.py

**Files:**
- Modify: `melodyi_web/__init__.py`

- [ ] **Step 1: Update module description**

Edit `melodyi_web/__init__.py`:
```python
"""melodyi-web: 多提供商搜索与网页抓取工具"""

__version__ = "0.1.0"
```

---

## Task 8: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update project name and description**

Edit `pyproject.toml`, change lines 2-4 and 21:
```toml
[project]
name = "melodyi-web"
version = "0.1.0"
description = "多提供商搜索与网页抓取工具"

# ... rest unchanged until scripts ...

[project.scripts]
melodyi-web = "melodyi_web.application.cli:main"

# ... rest unchanged ...

[tool.hatch.build.targets.wheel]
packages = ["melodyi_web"]
```

Full updated file content:
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

## Task 9: Update CLI Module

**Files:**
- Modify: `melodyi_web/application/cli.py`

- [ ] **Step 1: Update imports in cli.py**

Edit `melodyi_web/application/cli.py`, update all imports from `melodyi_search` to `melodyi_web`:

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


@click.group()
@click.version_option(version=__version__, prog_name="melodyi-web")
def cli():
    """melodyi-web: 多提供商搜索与网页抓取工具"""
    pass
```

- [ ] **Step 2: Update example commands in docstrings**

Edit the docstrings in cli.py to change `melodyi-search` to `melodyi-web`:

In `search` command docstring (around line 100-107):
```python
    """执行搜索

    QUERY 是搜索关键词，必填参数。

    示例:
        melodyi-web search "Python教程"
        melodyi-web search "AI新闻" --max-results 20 --time-range day
        melodyi-web search "技术博客" --include-domains blog.csdn.net -i juejin.cn
    """
```

In `config_show` command docstring (around line 217-221):
```python
    """显示当前配置

    示例:
        melodyi-web config show
        melodyi-web config show --output json
    """
```

---

## Task 10: Update Domain Models Imports

**Files:**
- Modify: `melodyi_web/domain/models/*.py`
- Modify: `melodyi_web/domain/services/*.py`

- [ ] **Step 1: Update imports in search_request.py**

Check and update if there are internal imports. Run:
```bash
grep -l "melodyi_search" melodyi_web/domain/models/*.py
```

Expected: No files found (domain models should not have internal imports to providers)

- [ ] **Step 2: Update imports in search_result.py**

Run:
```bash
grep "melodyi_search" melodyi_web/domain/models/search_result.py
```

Expected: No imports found (standalone model)

---

## Task 11: Update Domain Services Imports

**Files:**
- Modify: `melodyi_web/domain/services/*.py`

- [ ] **Step 1: Update imports in parameter_adapter.py**

Edit `melodyi_web/domain/services/parameter_adapter.py`:
```python
"""参数适配器 - 将统一请求转换为各提供商特定请求"""

from melodyi_web.domain.models.search_request import UnifiedSearchRequest, TimeRange
from melodyi_web.providers.search.base_provider import ProviderSearchRequest, BaseProvider
```

- [ ] **Step 2: Update imports in provider_factory.py**

Edit `melodyi_web/domain/services/provider_factory.py`:
```python
"""提供商工厂 - 根据配置创建提供商实例"""

from typing import List

from melodyi_web.domain.models.provider_config import ProviderConfig
from melodyi_web.providers.search.minimax_cn_provider import MiniMaxCNProvider
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.providers.search.exa_provider import ExaProvider
from melodyi_web.providers.search.searxng_provider import SearXNGProvider
from melodyi_web.providers.search.firecrawl_provider import FirecrawlProvider
from melodyi_web.providers.search.base_provider import BaseProvider
```

- [ ] **Step 3: Update imports in comparison_recorder.py**

Edit `melodyi_web/domain/services/comparison_recorder.py`:
```python
"""对比记录器 - 记录对比执行结果到数据库"""

import json
import logging
import time
from typing import List

from melodyi_web.domain.models.search_result import ProviderSearchResult
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
```

- [ ] **Step 4: Update imports in execution_strategy.py**

Edit `melodyi_web/domain/services/execution_strategy.py`:
```python
"""执行策略 - 管理搜索执行方式和对比模式"""

import logging
import threading
from typing import List

from melodyi_web.providers.search.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
```

---

## Task 12: Update Infrastructure Modules

**Files:**
- Modify: `melodyi_web/infrastructure/config/*.py`
- Modify: `melodyi_web/infrastructure/database/*.py`
- Modify: `melodyi_web/infrastructure/logging/*.py`

- [ ] **Step 1: Update imports in config_schema.py**

Edit `melodyi_web/infrastructure/config/config_schema.py`:
```python
"""全局配置模型"""

from typing import List
from pydantic import BaseModel, Field
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 2: Update imports in database_manager.py**

Edit `melodyi_web/infrastructure/database/database_manager.py`:
```python
"""数据库管理器 - SQLite 连接和表管理"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig


class DatabaseManager:
    """SQLite 数据库管理器"""
    ...

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.database_path = Path(config.database_path)
        self._logger = logging.getLogger("melodyi_web.database")
        ...
```

- [ ] **Step 3: Update logger name in search_logger.py**

Edit `melodyi_web/infrastructure/logging/search_logger.py`:
```python
"""搜索日志记录器"""

import logging
from pathlib import Path
from typing import Optional

from melodyi_web.domain.models.search_result import ProviderSearchResult


class SearchLogger:
    """搜索日志记录器"""

    def __init__(self, log_dir: str):
        self.log_dir = Path(log_dir)
        self.logger = logging.getLogger("melodyi_web.search")
        ...
```

---

## Task 13: Update Provider Imports

**Files:**
- Modify: All provider files in `melodyi_web/providers/search/*.py`

- [ ] **Step 1: Update imports in base_provider.py**

Edit `melodyi_web/providers/search/base_provider.py`:
```python
"""搜索提供商基类"""

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
```

- [ ] **Step 2: Update imports in minimax_cn_provider.py**

Edit `melodyi_web/providers/search/minimax_cn_provider.py`:
```python
"""MiniMax CN 提供商实现"""

import time
from typing import List, Optional

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

- [ ] **Step 3: Update imports in tavily_provider.py**

Edit `melodyi_web/providers/search/tavily_provider.py`:
```python
"""Tavily 提供商实现"""

import time
from typing import List, Optional

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

- [ ] **Step 4: Update imports in brave_provider.py**

Edit `melodyi_web/providers/search/brave_provider.py`:
```python
"""Brave 提供商实现"""

import time
from typing import List, Optional

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

- [ ] **Step 5: Update imports in exa_provider.py**

Edit `melodyi_web/providers/search/exa_provider.py`:
```python
"""Exa 提供商实现"""

import time
from typing import List, Optional

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

- [ ] **Step 6: Update imports in searxng_provider.py**

Edit `melodyi_web/providers/search/searxng_provider.py`:
```python
"""SearXNG 提供商实现"""

import time
from typing import List, Optional

from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem
from melodyi_web.infrastructure.http.http_client import HttpClient
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
```

- [ ] **Step 7: Update imports in firecrawl_provider.py**

Edit `melodyi_web/providers/search/firecrawl_provider.py`:
```python
"""Firecrawl 提供商实现

Firecrawl 是搜索+抓取服务：
- 支持云服务 (api.firecrawl.dev) 和自托管
- api_key 必填
- host 可选（自托管地址）
- POST 请求到 {host}/v1/search
- 不支持时间过滤和域名过滤
- 返回格式包含 web、images、news 三种结果
"""

import time
from typing import List, Optional
from datetime import datetime

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

## Task 14: Update Provider Config Model

**Files:**
- Modify: `melodyi_web/domain/models/provider_config.py`

- [ ] **Step 1: Check if provider_config.py has internal imports**

Run:
```bash
grep "melodyi_search" melodyi_web/domain/models/provider_config.py
```

Expected: No imports (standalone model using pydantic)

---

## Task 15: Update Test Files - Domain

**Files:**
- Modify: `tests/domain/models/*.py`
- Modify: `tests/domain/services/*.py`

- [ ] **Step 1: Update imports in all domain model tests**

Run to find files needing update:
```bash
grep -l "melodyi_search" tests/domain/models/*.py tests/domain/services/*.py
```

Update each file's imports:
```python
# Change
from melodyi_search.domain.models.xxx import ...

# To
from melodyi_web.domain.models.xxx import ...
```

- [ ] **Step 2: Update imports in test_search_request.py**

Edit `tests/domain/models/test_search_request.py`:
```python
"""SearchRequest 模型测试"""

import pytest
from melodyi_web.domain.models.search_request import UnifiedSearchRequest, TimeRange
```

- [ ] **Step 3: Update imports in test_error.py**

Edit `tests/domain/models/test_error.py`:
```python
"""Error 模型测试"""

import pytest
from melodyi_web.domain.models.error import SearchError
```

- [ ] **Step 4: Update imports in test_provider_config.py**

Edit `tests/domain/models/test_provider_config.py`:
```python
"""ProviderConfig 模型测试"""

import pytest
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 5: Update imports in test_search_result.py**

Edit `tests/domain/models/test_search_result.py`:
```python
"""SearchResult 模型测试"""

import pytest
from melodyi_web.domain.models.search_result import SearchResultItem, ProviderSearchResult
```

- [ ] **Step 6: Update imports in test_parameter_adapter.py**

Edit `tests/domain/services/test_parameter_adapter.py`:
```python
"""参数适配器测试"""

import pytest
from melodyi_web.domain.models.search_request import UnifiedSearchRequest, TimeRange
from melodyi_web.domain.services.parameter_adapter import ParameterAdapter
from melodyi_web.providers.search.base_provider import BaseProvider
from melodyi_web.domain.models.provider_config import ProviderConfig
```

- [ ] **Step 7: Update imports in test_provider_factory.py**

Edit `tests/domain/services/test_provider_factory.py`:
```python
"""提供商工厂测试"""

import pytest
from melodyi_web.domain.models.provider_config import ProviderConfig
from melodyi_web.domain.services.provider_factory import ProviderFactory
from melodyi_web.providers.search.base_provider import BaseProvider
```

- [ ] **Step 8: Update imports in test_comparison_recorder.py**

Edit `tests/domain/services/test_comparison_recorder.py`:
```python
"""对比记录器测试"""

import pytest
import tempfile
import os

from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
from melodyi_web.domain.models.search_result import ProviderSearchResult, SearchResultItem
```

- [ ] **Step 9: Update imports in test_execution_strategy.py**

Edit `tests/domain/services/test_execution_strategy.py`:
```python
"""执行策略测试"""

import pytest
from unittest.mock import Mock, patch

from melodyi_web.domain.services.execution_strategy import ExecutionStrategy
from melodyi_web.providers.search.base_provider import ProviderSearchRequest, ProviderSearchResult
```

---

## Task 16: Update Test Files - Infrastructure

**Files:**
- Modify: `tests/infrastructure/config/*.py`
- Modify: `tests/infrastructure/database/*.py`
- Modify: `tests/infrastructure/http/*.py`
- Modify: `tests/infrastructure/logging/*.py`

- [ ] **Step 1: Update imports in test_config_loader.py**

Edit `tests/infrastructure/config/test_config_loader.py`:
```python
"""配置加载器测试"""

import pytest
import tempfile
import os

from melodyi_web.infrastructure.config.config_loader import load_config
from melodyi_web.infrastructure.config.config_schema import Config
```

- [ ] **Step 2: Update imports in test_config_schema.py**

Edit `tests/infrastructure/config/test_config_schema.py`:
```python
"""配置模型测试"""

import pytest
from melodyi_web.infrastructure.config.config_schema import Config, ModeConfig, FallbackConfig, DatabaseConfig
```

- [ ] **Step 3: Update imports in test_database_manager.py**

Edit `tests/infrastructure/database/test_database_manager.py`:
```python
"""数据库管理器测试"""

import pytest
import tempfile
import os

from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
```

- [ ] **Step 4: Update imports in test_http_client.py**

Edit `tests/infrastructure/http/test_http_client.py`:
```python
"""HTTP 客户端测试"""

import pytest
from melodyi_web.infrastructure.http.http_client import HttpClient
```

- [ ] **Step 5: Update imports in test_search_logger.py**

Edit `tests/infrastructure/logging/test_search_logger.py`:
```python
"""搜索日志记录器测试"""

import pytest
import tempfile
import os

from melodyi_web.infrastructure.logging.search_logger import SearchLogger
from melodyi_web.domain.models.search_result import ProviderSearchResult, SearchResultItem
```

---

## Task 17: Update Test Files - Providers

**Files:**
- Modify: `tests/providers/search/*.py`

- [ ] **Step 1: Update imports in test_base_provider.py**

Edit `tests/providers/search/test_base_provider.py`:
```python
"""BaseProvider 测试"""

import pytest
from melodyi_web.providers.search.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 2: Update imports in test_minimax_cn_provider.py**

Edit `tests/providers/search/test_minimax_cn_provider.py`:
```python
"""MiniMaxCNProvider 测试"""

import pytest
from unittest.mock import Mock, patch

from melodyi_web.providers.search.minimax_cn_provider import MiniMaxCNProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 3: Update imports in test_tavily_provider.py**

Edit `tests/providers/search/test_tavily_provider.py`:
```python
"""TavilyProvider 测试"""

import pytest
from unittest.mock import Mock, patch

from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 4: Update imports in test_brave_provider.py**

Edit `tests/providers/search/test_brave_provider.py`:
```python
"""BraveProvider 测试"""

import pytest
from unittest.mock import Mock, patch

from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 5: Update imports in test_exa_provider.py**

Edit `tests/providers/search/test_exa_provider.py`:
```python
"""ExaProvider 测试"""

import pytest
from unittest.mock import Mock, patch

from melodyi_web.providers.search.exa_provider import ExaProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 6: Update imports in test_searxng_provider.py**

Edit `tests/providers/search/test_searxng_provider.py`:
```python
"""SearXNGProvider 测试"""

import pytest
from unittest.mock import Mock, patch

from melodyi_web.providers.search.searxng_provider import SearXNGProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

- [ ] **Step 7: Update imports in test_firecrawl_provider.py**

Edit `tests/providers/search/test_firecrawl_provider.py`:
```python
"""FirecrawlProvider 测试"""

import pytest
from unittest.mock import Mock, patch

from melodyi_web.providers.search.firecrawl_provider import FirecrawlProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
from melodyi_web.domain.models.search_request import TimeRange
```

---

## Task 18: Update Test Files - Application

**Files:**
- Modify: `tests/application/*.py`

- [ ] **Step 1: Update imports in test_cli.py**

Edit `tests/application/test_cli.py`:
```python
"""CLI 测试"""

import pytest
from click.testing import CliRunner

from melodyi_web.application.cli import cli
```

- [ ] **Step 2: Update CLI name assertions in test_cli.py**

Find and update assertions that check for "melodyi-search":
```python
# Change
assert "melodyi-search" in result.output

# To
assert "melodyi-web" in result.output
```

---

## Task 19: Update Test Files - Integration

**Files:**
- Modify: `tests/integration/*.py`

- [ ] **Step 1: Update imports in all integration tests**

Run to find files needing update:
```bash
grep -l "melodyi_search" tests/integration/*.py
```

- [ ] **Step 2: Update imports in test_tavily_e2e.py**

Edit `tests/integration/test_tavily_e2e.py`:
```python
"""Tavily E2E 测试"""

import pytest
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
```

- [ ] **Step 3: Update imports in test_exa_e2e.py**

Edit `tests/integration/test_exa_e2e.py`:
```python
"""Exa E2E 测试"""

import pytest
from melodyi_web.providers.search.exa_provider import ExaProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
```

- [ ] **Step 4: Update imports in test_minimax_cn_e2e.py**

Edit `tests/integration/test_minimax_cn_e2e.py`:
```python
"""MiniMax CN E2E 测试"""

import pytest
from melodyi_web.providers.search.minimax_cn_provider import MiniMaxCNProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
```

- [ ] **Step 5: Update imports in test_brave_e2e.py**

Edit `tests/integration/test_brave_e2e.py`:
```python
"""Brave E2E 测试"""

import pytest
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.providers.search.base_provider import ProviderSearchRequest
```

- [ ] **Step 6: Update imports in test_comparison_e2e.py**

Edit `tests/integration/test_comparison_e2e.py`:
```python
"""Comparison E2E 测试"""

import pytest
import tempfile
import os

from melodyi_web.domain.services.execution_strategy import ExecutionStrategy
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
```

- [ ] **Step 7: Update imports in test_cli_comparison_e2e.py**

Edit `tests/integration/test_cli_comparison_e2e.py`:
```python
"""CLI Comparison E2E 测试"""

import pytest
import tempfile
import os

from click.testing import CliRunner
from melodyi_web.application.cli import cli
```

---

## Task 20: Update Test __init__.py Files

**Files:**
- Modify: `tests/__init__.py`

- [ ] **Step 1: Update tests/__init__.py**

Edit `tests/__init__.py`:
```python
"""melodyi-web 测试"""
```

---

## Task 21: Update Default Config

**Files:**
- Modify: `melodyi_web/infrastructure/config/default_config.yaml`

- [ ] **Step 1: Update data directory path**

Edit `melodyi_web/infrastructure/config/default_config.yaml`:

Change:
```yaml
# melodyi-search 默认配置
# ...

mode:
  log_dir: ${HOME}/.melodyi-search/logs

database:
  database_path: ${HOME}/.melodyi-search/data/compare.db
```

To:
```yaml
# melodyi-web 默认配置
# ...

mode:
  log_dir: ${HOME}/.melodyi-web/logs

database:
  database_path: ${HOME}/.melodyi-web/data/compare.db
```

---

## Task 22: Update Documentation Files

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.planning/PROJECT.md`
- Modify: `.planning/ROADMAP.md`
- Modify: `.planning/STATE.md`
- Modify: `skill.md`
- Modify: `.env.example`

- [ ] **Step 1: Update CLAUDE.md**

Edit `CLAUDE.md`, change project name:
```markdown
# melodyi-web Project Instructions

此项目使用 Get Shit Done (GSD) 工作流管理。

## Project Context

- **Core Value:** Compare 模式的完整结果记录与持久化 + 网页抓取能力 — 供应商质量分析的基础
- **Current Phase:** Phase 1 — Rename to melodyi-web
- **Roadmap:** `.planning/ROADMAP.md`
```

- [ ] **Step 2: Update .planning/PROJECT.md**

Edit `.planning/PROJECT.md`:
```markdown
# melodyi-web

## What This Is

一个**供应商质量分析基础设施**，通过 Compare 模式同时调用多家搜索供应商，记录完整结果和元数据到 SQLite，用于数据驱动的供应商择优决策。

同时提供**网页抓取能力**，聚合多家 fetch 供应商 API，获取网页全文内容。

为 Agent 提供统一的 `skill.md`，无需关心各 Agent 内置工具的供应商差异。
```

- [ ] **Step 3: Update skill.md**

Edit `skill.md`:
```markdown
---
name: melodyi-web
description: 使用 melodyi-web 进行网络搜索和网页抓取
---

# melodyi-web Skill

多提供商搜索与网页抓取工具。

## Search 功能

...
```

- [ ] **Step 4: Update .env.example**

Edit `.env.example`:
```markdown
# melodyi-web 环境变量模板
```

---

## Task 23: Create fetch test placeholder

**Files:**
- Create: `tests/providers/fetch/__init__.py`

- [ ] **Step 1: Write placeholder __init__.py**

Write to `tests/providers/fetch/__init__.py`:
```python
"""Fetch provider tests

Tests for web page fetch/scrape providers.
Currently empty - to be implemented in Phase 3.
"""
```

---

## Task 24: Run Tests to Verify Rename

**Files:**
- None (verification step)

- [ ] **Step 1: Run all tests**

Run:
```bash
cd C:/workspace/melodyi-skills/skills/melodyi-search
pytest -v
```

Expected: All tests pass

- [ ] **Step 2: If tests fail, check for missed imports**

Run to find any remaining old imports:
```bash
grep -r "melodyi_search" melodyi_web/ tests/ --include="*.py"
```

Expected: No matches found

---

## Task 25: Verify CLI Works

**Files:**
- None (verification step)

- [ ] **Step 1: Verify CLI entry point works**

Run:
```bash
cd C:/workspace/melodyi-skills/skills/melodyi-search
python -m melodyi_web --version
```

Expected output:
```
melodyi-web, version 0.1.0
```

- [ ] **Step 2: Verify CLI search command help**

Run:
```bash
python -m melodyi_web search --help
```

Expected: Shows help text with "melodyi-web search" examples

---

## Task 26: Commit Rename Changes

**Files:**
- None (commit step)

- [ ] **Step 1: Stage all renamed files**

Run:
```bash
cd C:/workspace/melodyi-skills/skills/melodyi-search
git add -A
```

- [ ] **Step 2: Verify staged changes**

Run:
```bash
git status
```

Expected: Shows renamed files and modifications

- [ ] **Step 3: Commit with descriptive message**

Run:
```bash
git commit -m "$(cat <<'EOF'
refactor: rename melodyi-search to melodyi-web

Changes:
- Rename package directory: melodyi_search/ → melodyi_web/
- Rename CLI command: melodyi-search → melodyi-web
- Restructure providers: flat → search/ + fetch/ subdirectories
- Update all imports from melodyi_search to melodyi_web
- Update data directory: ~/.melodyi-search/ → ~/.melodyi-web/
- Update documentation and skill.md

This prepares the project for adding fetch functionality
while maintaining existing search capabilities.
EOF
)"
```

---

## Verification Summary

After completing all tasks:

- [ ] `pytest` - all tests pass
- [ ] `python -m melodyi_web --version` - shows "melodyi-web, version 0.1.0"
- [ ] `python -m melodyi_web search --help` - shows correct command name
- [ ] `python -m melodyi_web config show` - works correctly
- [ ] No remaining `melodyi_search` imports in codebase

---

*Plan created: 2026-05-11*