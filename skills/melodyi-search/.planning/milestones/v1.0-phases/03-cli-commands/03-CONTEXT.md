# Phase 3: CLI Commands - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

## Phase Boundary

验证 compare 模式数据正确持久化，确保后台静默行为正常工作。

此 Phase 仅负责：
- 确保 search --comparison 参数正确覆盖配置开关
- 验证数据持久化逻辑正确（对比数据写入数据库）
- 通过测试验证持久化功能

**不包含：**
- 独立 compare 命令（已明确不新增）
- history 命令（CLI-02~06，已明确抛弃）
- CLI 输出变化（输出格式与普通 search 一致）

**核心设计：compare 模式为后台静默行为**
用户使用 search 命令时无需关心 compare 是否开启，输出体验完全一致。

## Implementation Decisions

### CLI 命令设计

- **D-01:** 不新增独立 compare 命令，仅使用 search + --comparison 参数
  - **Why:** 用户期望 compare 是后台静默行为，不影响 CLI 使用体验
  - **How to apply:** REQUIREMENTS.md 的 CLI-01 理解调整为"通过参数覆盖配置开关"

- **D-02:** 抛弃 history 命令（CLI-02~06），不实现
  - **Why:** 暂时没有构建分析能力的诉求，数据正确保存在数据库即可
  - **How to apply:** REQUIREMENTS.md 的 CLI-02~06 标记为"不实现"

- **D-03:** compare 模式输出与普通 search 完全一致
  - 指定 provider 时返回该 provider 结果
  - 不指定 provider 时按原有优先级排序
  - 格式不变（text/json）

### 配置设计

- **D-04:** 复用现有 config.mode.comparison 字段
  - **Why:** 配置模型已有此字段，无需新增
  - **How to apply:** 在 default_config.yaml 中设置默认值

- **D-05:** CLI --comparison 参数覆盖配置开关
  - 配置关闭时，CLI 指定 --comparison 则启用
  - 配置开启时，CLI 不指定则默认启用

### 输出设计

- **D-06:** CLI 不输出 session_id
  - **Why:** 用户暂时不需要追溯功能，session_id 仅数据库记录
  - **How to apply:** UnifiedSearchResult.session_id 不在 CLI 输出中显示

- **D-07:** 持久化静默执行，不显示提示信息
  - **Why:** 后台行为不应干扰用户体验
  - **How to apply:** CLI 输出格式与普通 search 一致

### 验证方式

- **D-08:** 通过测试/手动验证数据持久化
  - 不依赖 CLI 输出确认
  - 可通过 sqlite3 查询验证数据正确写入

### Claude's Discretion

基于用户明确的"后台静默行为"设计理念，Phase 3 实现为轻量级验证阶段：
- 核心持久化逻辑已在 Phase 2 完成
- Phase 3 主要是验证性测试，确保数据正确写入
- 不新增 CLI 命令，不改变输出格式

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements
- `.planning/PROJECT.md` — 项目愿景、核心价值、设计约束
- `.planning/REQUIREMENTS.md` — CLI-01~06 定义（注意：CLI-02~06 已明确抛弃）
- `.planning/ROADMAP.md` — Phase 3 任务列表和成功标准（需调整）

### Prior Phase Decisions
- `.planning/phases/01-database-infrastructure/01-CONTEXT.md` — D-01~05 数据库基础设施决策
- `.planning/phases/02-compare-mode-enhancement/02-CONTEXT.md` — D-01~04 Compare 模式持久化决策

### Architecture Context
- `.planning/codebase/ARCHITECTURE.md` — DDD 分层架构、数据流
- `.planning/codebase/STACK.md` — Python >=3.10, Pydantic V2, click CLI 框架

### Existing Code Patterns
- `melodyi_search/application/cli.py` — 现有 CLI 入口，已有 --comparison 参数
- `melodyi_search/domain/services/execution_strategy.py` — Compare 模式执行逻辑
- `melodyi_search/infrastructure/database/database_manager.py` — 数据库管理器
- `melodyi_search/infrastructure/config/config_schema.py` — 配置模型（含 mode.comparison 字段）

## Existing Code Insights

### Reusable Assets
- `cli.py` — 现有 search 命令已支持 --comparison 参数
- `execution_strategy.py` — execute_comparison() 已实现后台执行和持久化
- `database_manager.py` — 数据库连接和表管理已实现
- `config_schema.py` — ModeConfig.comparison 字段已定义

### Established Patterns
- **DDD 分层**: CLI 调用 domain/services，不直接访问 database
- **click 参数**: 使用 `is_flag=True` 定义 boolean 参数
- **配置覆盖**: CLI 参数可覆盖配置文件默认值

### Integration Points
- `cli.py:search()` — 现有命令已判断 comparison 参数，调用 execute_comparison()
- `execution_strategy.py` — 已调用 ComparisonRecorder 写入数据
- `UnifiedSearchResult` — 已包含 session_id 字段（CLI 不输出）

## Specific Ideas

核心设计理念："compare 是后台静默行为"
- 用户使用 search 命令时无需关心 compare 是否开启
- 输出体验完全一致，数据在后台静默持久化
- 通过测试验证功能正确，不依赖 CLI 输出确认

## Deferred Ideas

### CLI-02~06 (history 命令) — 已明确抛弃，不实现
用户反馈："暂时没有构建分析能力的诉求，数据正确保存在数据库即可"

---

*Phase: 03-cli-commands*
*Context gathered: 2026-05-09*