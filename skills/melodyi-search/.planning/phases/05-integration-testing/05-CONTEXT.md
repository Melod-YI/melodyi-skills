# Phase 5: Integration & Testing - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

## Phase Boundary

系统集成验证，确保 Compare 模式增强不影响现有功能。

此 Phase 仅负责：
- 回归测试验证 Normal Search 模式正常工作
- 验证 Agent 集成点（skill.md）不变
- 验证 Provider API 连通性
- 确认数据库作为新增组件不影响现有路径

**不包含：**
- 新功能开发（Phase 01-03 已完成）
- 性能优化（v2 需求）
- Analysis 功能（Phase 4，用户已跳过）

**核心约束：回归验证为主**
Phase 01-03 已实现所有功能并通过测试（446 tests），此 Phase 主要是验证性回归。

## Implementation Decisions

### 回归测试范围

- **D-01:** 完整回归测试覆盖
  - Normal Search 模式（不启用 comparison）输出格式、执行策略、回退逻辑
  - Provider API 连通性（Tavily, Brave, Exa, MiniMax CN）
  - **Why:** 确保现有功能不受 Compare 模式增强影响
  - **How to apply:** 运行现有 E2E tests + 手动验证关键场景

### 集成点确认

- **D-02:** Agent 集成点不变
  - skill.md 格式不变，参数定义不变
  - Compare 模式后台静默执行，Agent 无感知
  - **Why:** Agent 使用方式完全不变，无需更新 skill 文件
  - **How to apply:** 验证 skill.md 无需修改即可工作

- **D-03:** 数据库为新增组件
  - 不影响现有 CLI/API 调用路径
  - 配置可选，默认 ./data/compare.db
  - **Why:** 数据库是 Compare 模式的持久化层，独立于主体功能
  - **How to apply:** 配置关闭 comparison 时，数据库不初始化

### Claude's Discretion

基于用户明确"回归验证为主"的设计理念，以下决策由 Claude 决定：
- 回归测试的具体执行方式（pytest + 手动验证）
- Provider E2E 测试是否需要真实 API Key（依赖测试环境）
- 验证通过的标准（所有现有测试通过 + 关键场景手动确认）

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Prior Phase Decisions
- `.planning/phases/01-database-infrastructure/01-CONTEXT.md` — D-01~05 数据库基础设施决策
- `.planning/phases/02-compare-mode-enhancement/02-CONTEXT.md` — D-01~04 Compare 模式持久化决策
- `.planning/phases/03-cli-commands/03-CONTEXT.md` — D-01~08 CLI 输出不变决策

### Project Requirements
- `.planning/PROJECT.md` — 项目愿景、核心价值、约束条件
- `.planning/REQUIREMENTS.md` — INT-01~04 集成需求定义
- `.planning/ROADMAP.md` — Phase 5 任务列表和成功标准

### Architecture & Testing Context
- `.planning/codebase/TESTING.md` — pytest 配置、测试结构、命令
- `.planning/codebase/ARCHITECTURE.md` — DDD 分层架构
- `.planning/codebase/CONCERNS.md` — 已知问题和技术债务

### Agent Integration
- `skill.md` — Agent 使用接口，格式不变

## Existing Code Insights

### Reusable Assets
- `tests/integration/test_comparison_e2e.py` — Compare E2E 测试已存在
- `tests/integration/test_cli_comparison_e2e.py` — CLI E2E 测试已存在
- `tests/integration/test_*_e2e.py` — Provider E2E 测试已存在
- `tests/application/test_cli.py` — CLI 单元测试已存在

### Established Patterns
- **pytest 结构**: tests/ 镜像源码目录结构
- **E2E 测试**: tests/integration/ 存放真实 API 调用测试
- **回归验证**: 运行 pytest tests/ -v 确认全部通过

### Integration Points
- CLI 入口: `melodyi_search/application/cli.py` — search 命令
- skill.md: Agent 调用接口 — 参数定义不变
- 配置: `default_config.yaml` — 结构向后兼容
- 数据库: `./data/compare.db` — 新增，不影响现有功能

## Specific Ideas

核心设计理念："回归验证为主"
- 现有 446 tests 已覆盖核心功能
- 此 Phase 确保所有测试继续通过
- 不新增功能，只验证集成

## Deferred Ideas

None — 讨论保持在 Phase 范围内。

---

*Phase: 05-integration-testing*
*Context gathered: 2026-05-09*