# Phase 1: Database Infrastructure - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

## Phase Boundary

建立 SQLite 持久化基础设施，为对比数据存储提供底层数据库支持。

此 Phase 仅负责：
- 数据库文件创建和连接管理
- 表结构设计（comparison_sessions, provider_results, search_results）
- 索引创建（session_id, provider, timestamp, source_domain）
- 初始化脚本

**不包含：**
- 数据写入逻辑（Phase 2）
- CLI 命令（Phase 3）
- 分析功能（Phase 4）

## Implementation Decisions

### Claude's Discretion

用户跳过讨论，技术实现细节由 Claude 决定：

- **D-01: 数据库初始化时机** — CLI 启动时自动检查并创建数据库（lazy initialization），无需独立 init 命令
- **D-02: 连接管理模式** — 使用 sqlite3 标准库，每次操作新建连接（SQLite 轻量级场景无需连接池）
- **D-03: 事务策略** — 单条插入默认 autocommit，批量写入时显式事务（Phase 2 实现）
- **D-04: 数据库文件位置** — 默认 `./data/compare.db`，通过配置文件可自定义路径
- **D-05: 表命名规范** — 使用 snake_case，与现有代码风格一致

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements
- `.planning/PROJECT.md` — 项目愿景、核心价值、约束条件
- `.planning/REQUIREMENTS.md` — DB-01~05 详细需求定义
- `.planning/ROADMAP.md` — Phase 1 任务列表和成功标准

### Architecture Context
- `.planning/codebase/ARCHITECTURE.md` — DDD 分层架构、数据流
- `.planning/codebase/STACK.md` — Python >=3.10, Pydantic V2, pytest

### Existing Code Patterns
- `melodyi_search/infrastructure/config/` — 配置管理模式（YAML + 环境变量）
- `melodyi_search/domain/services/execution_strategy.py` — Compare 模式实现（Phase 2 的写入触发点）

## Existing Code Insights

### Reusable Assets
- `melodyi_search/infrastructure/config/config_schema.py` — 配置 Pydantic 模型，可扩展添加 `database_path` 字段
- `melodyi_search/infrastructure/config/default_config.yaml` — 默认配置文件，可添加数据库配置节

### Established Patterns
- **DDD 分层**: 数据库管理器应放在 `infrastructure/database/` 目录
- **Pydantic 验证**: 配置项使用 Pydantic 模型验证
- **日志规范**: 核心操作需记录日志（初始化、表创建、错误）

### Integration Points
- Phase 2 的 `comparison_recorder.py` 将调用数据库管理器写入数据
- CLI 启动时需确保数据库已初始化（可在 `cli.py` 入口检查）

## Specific Ideas

无特定要求 — 采用标准 SQLite 实现模式。

## Deferred Ideas

None — 讨论保持在 Phase 范围内。

---

*Phase: 01-database-infrastructure*
*Context gathered: 2026-05-06*