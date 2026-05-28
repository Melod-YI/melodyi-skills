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
- `ParameterAdapter` (统一参数适配) → `domain/services/parameter_adapter.py`
- `ProviderFactory` → `domain/services/provider_factory.py`

## 开发规范

- Python >=3.10，Pydantic V2
- 中文文档字符串
- 测试镜像源码结构 (`tests/` 目录)
- 集成测试位于 `tests/integration/`
- 错误携带 `guidance` 字段指导 Agent 行为