# Phase 5: Integration & Testing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 05-integration-testing
**Areas discussed:** 回归测试范围, 集成点确认

---

## Gray Areas Selection

| Option | Description | Selected |
|--------|-------------|----------|
| 回归测试范围 | 确定哪些关键场景必须通过回归测试 | ✓ |
| skill.md 定义 | 明确 skill.md 允许的变更范围 | |
| 集成点确认 | 检查是否有遗漏的集成点 | ✓ |
| 无需讨论 | 现有测试已覆盖，直接进入计划 | |

**User's choice:** 回归测试范围, 集成点确认
**Notes:** 用户跳过 skill.md 定义讨论，认为已确认不变

---

## 回归测试范围

| Option | Description | Selected |
|--------|-------------|----------|
| Normal Search 模式 | 确保普通 search（不启用 comparison）的现有功能不受影响 | |
| Provider API 连通性 | 确保各 Provider E2E 调用正常（需真实 API Key） | |
| 完整回归（Normal + Providers） | 盖以上所有场景的完整回归 | ✓ |

**User's choice:** 完整回归（Normal + Providers）
**Notes:** 用户选择覆盖所有场景的完整回归测试

---

## 集成点确认

| Option | Description | Selected |
|--------|-------------|----------|
| Agent 集成（已确认） | skill.md 格式不变，Compare 模式后台静默执行，Agent 无感知 | |
| 数据库集成（新增） | 数据库为新增组件，不影响现有 CLI/API 调用路径 | |
| 全部已确认 | 以上两个集成点均已确认，无需额外讨论 | ✓ |

**User's choice:** 全部已确认
**Notes:** Agent 集成点和数据库集成点均已确认，无需额外讨论

---

## Claude's Discretion

用户明确以下决策由 Claude 决定：
- 回归测试的具体执行方式（pytest + 手动验证）
- Provider E2E 测试是否需要真实 API Key（依赖测试环境）
- 验证通过的标准（所有现有测试通过 + 关键场景手动确认）

## Deferred Ideas

None — 讨论保持在 Phase 范围内。

---

*Discussion completed: 2026-05-09*