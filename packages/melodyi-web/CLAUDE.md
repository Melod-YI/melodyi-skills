# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# melodyi-web Project Instructions

多提供商搜索与网页抓取工具，采用 DDD 架构。

## 常用命令

| 命令 | 用途 |
|------|------|
| `pip install -e .` | 安装开发模式 |
| `pip install -e ".[dev]"` | 安装含开发依赖 |
| `pytest` | 运行所有测试 |
| `pytest tests/domain/` | 运行领域层测试 |
| `pytest tests/integration/ -v` | 运行集成测试（需 API Key） |
| `pytest -k "test_name"` | 按名称过滤 |
| `python -m melodyi_web` | CLI 入口 |
| `melodyi-web search "query"` | 搜索命令 |
| `melodyi-web fetch <url>` | 抓取命令 |
| `melodyi-web config init` | 创建默认配置文件 |
| `melodyi-web config show` | 显示当前配置 |

## 配置文件

**查找优先级**：
1. CLI `--config` 参数指定路径
2. `~/.melodyi-web/config.yaml`（用户配置）
3. 内置默认值（无需配置文件）

**用户配置目录**: `~/.melodyi-web/`

| 文件 | 说明 |
|------|------|
| `config.yaml` | 主配置文件（`config init` 创建） |
| `.env` | API Key 等敏感信息 |

**Fetch 默认供应商**（无需配置）：
- `jina-reader` — 无需 API Key，支持 JS 渲染
- `markdown-new` — 无需 API Key

## 架构

```
melodyi_web/
├── application/           # 应用层 — CLI (click)
├── domain/
│   ├── models/            # 领域模型 (Pydantic)
│   └── services/          # 领域服务
├── infrastructure/
│   ├── config/            # YAML 配置加载
│   ├── database/          # SQLite 数据库
│   ├── http/              # httpx 客户端
│   └── logging/           # 日志系统
└── providers/
    ├── search/            # 搜索提供商实现
    └── fetch/             # 抓取提供商实现
```

**核心模型:**
- `UnifiedSearchRequest` → `domain/models/search_request.py`
- `FetchRequest` → `domain/models/fetch_request.py`
- `SearchError` (带 Agent 指导) → `domain/models/error.py`

**核心服务:**
- `ExecutionStrategy` (正常/比对模式) → `domain/services/execution_strategy.py`
- `FetchExecutionStrategy` (fetch 侧同模式) → `domain/services/fetch_executor.py`
- `ParameterAdapter` (统一参数适配) → `domain/services/parameter_adapter.py`
- `ProviderFactory` / `FetchProviderFactory` → `domain/services/`

## 关键设计决策

| ID | 决策 |
|----|------|
| D-01 | 比对模式后台线程 `daemon=False` + `thread.join(timeout=10)` |
| D-02 | 每个提供商结果完成后立即写入 SQLite（单条 autocommit） |
| D-03 | Session ID 格式: `YYYYMMDD-HHMMSS-XXXX` |
| D-04 | 持久化失败只记 ERROR 日志，**不抛异常**，执行继续 |
| D-05 | CLI `--comparison` 覆盖配置文件 `mode.comparison` |

**比对模式执行流**: 第一个提供商同步执行并立即返回结果；其余提供商在后台线程执行用于数据收集。所有结果通过 `ComparisonRecorder` 写入 SQLite。

**提供商错误处理模式**: 所有提供商的 `search()`/`fetch()` 方法内部捕获全部异常，返回 `error=...` 结果字符串，**永不向上抛出异常**。策略层收集错误，全部失败时返回 `ALL_PROVIDERS_FAILED`。

**错误指导系统**: `error.py` 中 `ErrorType` 枚举映射到中文 `guidance` 文本，指导 AI Agent 如何恢复（如"检查 API Key"、"等待重试"、"系统已切换提供商"）。

## 提供商注意事项

- **MiniMax CN**: API 不支持时间过滤，通过注入中文关键词（"今天 最新"）模拟；域名过滤通过 `urlparse` 后处理
- **FetchProviderFactory**: 存在遗留名称映射 `"jina-reader"` → `"jina"`
- **Config 向后兼容**: 旧 `providers` 字段自动迁移到 `search_providers`（使用 `object.__setattr__` 绕过 Pydantic frozen）

## 测试模式

- **无 conftest.py**，无共享 fixture — 每个测试类自行定义
- 单元测试大量使用 `unittest.mock`（`MagicMock`、`patch`、`Mock`）
- 集成测试位于 `tests/integration/`，命名 `*_e2e.py`，需真实 API Key
- 比对/持久化测试使用 `tempfile.NamedTemporaryFile` 创建临时 SQLite
- 构建工具: Hatchling（`pyproject.toml`）

## 开发规范

- Python >=3.10，Pydantic V2（使用 `model_validator`、`field_validator`）
- 中文文档字符串
- 测试镜像源码结构 (`tests/` 目录)
- 错误携带 `guidance` 字段指导 Agent 行为
- 所有提供商方法为同步调用（无 async/await），`HttpClient` 封装同步 `httpx.Client`