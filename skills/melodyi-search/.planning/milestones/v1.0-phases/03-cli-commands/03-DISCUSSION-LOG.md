# Phase 3: CLI Commands - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 03-cli-commands
**Areas discussed:** compare 输出设计, history 命令, 配置开关, session_id 输出

---

## compare 输出设计

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 session_id | compare 命令返回 session_id，不显示搜索结果 | |
| session_id + 结果 | 返回 session_id + 首选供应商的搜索结果 | |
| 完整汇总 | 返回 session_id + 所有供应商结果汇总 | |

**User's choice:** compare 不需要独立命令，而是配置开关。后台静默执行，输出与普通 search 完全一致。

**Notes:** 用户期望 compare 是后台行为：
- 配置开关打开后，普通 search 命令后台自动变成 compare 模式
- CLI --comparison 参数可覆盖配置开关
- 输出格式不变，无论是否开启 compare 都一致

---

## CLI 命令设计 (REQUIREMENTS.md CLI-01)

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 search + --comparison | search + --comparison 参数覆盖配置，无需独立命令 | ✓ |
| search + compare 别名 | 既有 search --comparison，也有 compare 命令作为别名 | |
| 保留独立 compare 命令 | 按 REQUIREMENTS.md 保留 compare <query> 独立命令 | |

**User's choice:** 仅 search + --comparison
**Notes:** 不新增独立 compare 命令，REQUIREMENTS.md 的 CLI-01 理解调整为参数覆盖

---

## history 命令 (CLI-02~06)

| Option | Description | Selected |
|--------|-------------|----------|
| 紧凑单行 | session_id 截断、query 截断、时间、供应商数 | |
| 表格格式 | 使用 click-tabulate 或 rich 显示表格 | |
| 详细列表 | 完整字段，占用空间大 | |

**User's choice:** 不需要 history 命令，数据正确保存在数据库即可
**Notes:** 用户反馈："暂时没有构建分析能力的诉求"

---

## Phase 3 需求范围确认

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 3 不需要 | 持久化已完成，Phase 3 可跳过 | |
| 保留调试工具 | history 仅用于开发调试 | |
| 延后 history 命令 | 保留但延后实现 | |

**User's choice:** 抛弃 history 命令，Phase 3 需要确保数据正确持久化
**Notes:** Phase 3 简化为验证阶段，确保 compare 模式数据持久化正确工作

---

## 持久化验证方式

| Option | Description | Selected |
|--------|-------------|----------|
| 通过测试/手动验证 | 检查数据库写入，不需要 CLI 输出变化 | ✓ |
| CLI 输出 session_id | 显示 session_id 让用户知道数据已记录 | |
| 静默 + session_id 提示 | 输出 session_id + "数据已持久化" 提示 | |

**User's choice:** 通过测试/手动验证
**Notes:** CLI 输出不变，不显示 session_id 或持久化提示

---

## session_id 输出

| Option | Description | Selected |
|--------|-------------|----------|
| 不输出 session_id | 仅数据库记录，CLI 不显示 | ✓ |
| 仅 JSON 格式输出 | JSON 输出包含字段，text 不显示 | |
| 所有格式输出 | 所有格式都输出 session_id | |

**User's choice:** 不输出 session_id
**Notes:** session_id 仅数据库记录，用户暂时不需要追溯功能

---

## 配置开关位置

| Option | Description | Selected |
|--------|-------------|----------|
| 复用现有配置 | config.mode.comparison 字段已存在 | ✓ |
| 新增独立配置项 | 新增 comparison.enabled 配置 | |

**User's choice:** 复用现有配置
**Notes:** 配置模型已有 ModeConfig.comparison 字段，无需新增

---

## Claude's Discretion

基于用户明确的"后台静默行为"设计理念，Phase 3 为轻量级验证阶段：
- 核心持久化逻辑已在 Phase 2 完成
- Phase 3 主要是验证性测试
- 不新增 CLI 命令，不改变输出格式

## Deferred Ideas

- **CLI-02~06 (history 命令)** — 已明确抛弃，不实现
  - 用户反馈："暂时没有构建分析能力的诉求，数据正确保存在数据库即可"