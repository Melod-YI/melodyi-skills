# Phase 2: Compare Mode Enhancement - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

## Phase Boundary

对比模式完整结果记录与持久化，为供应商质量分析提供数据基础。

此 Phase 仅负责：
- 记录所有供应商的完整搜索结果（title, url, description, published_date）
- 持久化到 SQLite（comparison_sessions, provider_results, search_results）
- 返回 session_id 用于追溯
- 修复 daemon thread 后台写入问题

**不包含：**
- CLI 命令扩展（Phase 3）
- 供应商质量分析报告（Phase 4）
- 系统集成验证（Phase 5）

**核心约束：优先保障 CLI 主体功能可用**
Agent 调用搜索的能力必须正确、及时返回，持久化是次要功能，不能阻塞主流程。

## Implementation Decisions

### Daemon Thread 修复方案

- **D-01:** 使用 `thread.join(timeout)` 等待后台线程完成
  - 设置 `daemon=False`，主进程退出前等待
  - timeout = 10 秒，超时后继续退出
  - **Why:** daemon=True 导致进程退出时后台线程未完成写入，数据丢失
  - **How to apply:** 修改 `execution_strategy.py` 的 `execute_comparison()` 方法

### 数据写入时机

- **D-02:** 每个供应商完成后立即写入数据库
  - 单条 autocommit（Phase 1 决策）
  - 错误隔离，失败不影响其他供应商
  - **Why:** 批量写入增加事务复杂度，单个写入更简单
  - **How to apply:** 在 `_execute_background_providers()` 循环中逐个写入

### Session ID 生成策略

- **D-03:** 时间戳前缀 + 随机数
  - 格式：`YYYYMMDD-HHMMSS-XXXX`（如 `20260509-143052-a1b2`）
  - 8 位随机字符（十六进制）
  - **Why:** UUID4 不可读，时间戳前缀便于历史查询和日志追溯
  - **How to apply:** 在 `comparison_recorder.py` 中生成

### 持久化失败处理

- **D-04:** 日志记录继续执行，不中断 CLI 返回
  - 后台写入失败：记录 ERROR 日志
  - 不抛出异常，保障主体功能
  - **Why:** 持久化是次要功能，不能阻塞主流程
  - **How to apply:** 写入操作捕获异常，记录日志后继续

### Claude's Discretion

基于用户核心约束"优先保障 CLI 主体功能可用"，以下决策由 Claude 自行决定：
- 后台线程等待时长（10 秒 timeout）
- Session ID 格式（时间戳 + 随机数）
- 写入失败时的处理策略（日志记录继续）

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements
- `.planning/PROJECT.md` — 项目愿景、核心价值、核心约束
- `.planning/REQUIREMENTS.md` — COMP-01~07 详细需求定义
- `.planning/ROADMAP.md` — Phase 2 任务列表和成功标准

### Phase 1 Locked Decisions
- `.planning/phases/01-database-infrastructure/01-CONTEXT.md` — D-01~05 数据库基础设施决策

### Architecture Context
- `.planning/codebase/ARCHITECTURE.md` — DDD 分层架构、数据流
- `.planning/codebase/STRUCTURE.md` — 目录布局、关键文件位置

### Existing Code Patterns
- `melodyi_search/domain/services/execution_strategy.py` — Compare 模式实现（修改点）
- `melodyi_search/infrastructure/database/database_manager.py` — 数据库管理器（调用点）
- `melodyi_search/domain/models/search_result.py` — UnifiedSearchResult（添加 session_id）

## Existing Code Insights

### Reusable Assets
- `database_manager.py`: 数据库连接和表管理已实现，可直接调用
- `config_schema.py`: DatabaseConfig 配置模型已定义
- `UnifiedSearchResult.comparison_log`: 已有字段存储对比元数据

### Established Patterns
- **DDD 分层**: comparison_recorder.py 应放在 `domain/services/`
- **错误处理**: 使用 `SearchError.guidance` 提供补救提示
- **日志规范**: 核心操作记录 INFO/WARNING/ERROR 日志

### Integration Points
- `execution_strategy.py:execute_comparison()` — 调用 comparison_recorder 写入数据
- `execution_strategy.py:_execute_background_providers()` — 后台供应商逐个写入
- `UnifiedSearchResult` — 添加 `session_id` 字段返回给用户

## Specific Ideas

无特定要求 — 基于核心约束"优先保障主体功能可用"做技术决策。

## Deferred Ideas

None — 讨论保持在 Phase 范围内。

---

*Phase: 02-compare-mode-enhancement*
*Context gathered: 2026-05-09*