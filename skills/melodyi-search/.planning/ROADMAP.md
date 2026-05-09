# ROADMAP: melodyi-search Compare Enhancement

**Created:** 2026-05-04
**Phases:** 5
**Mode:** YOLO (auto-approve)

---

## Phase Overview

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Database Infrastructure | 建立 SQLite 持久化基础设施 | DB-01~05 | 3 criteria |
| 2 | Compare Mode Enhancement | 对比模式完整结果记录与持久化 | COMP-01~07 | 3 criteria |
| 3 | CLI Commands | 验证 compare 模式数据持久化 | CLI-01 (modified) | 4 criteria |
| 4 | Analysis Features | 供应商质量分析报告 | ANAL-01~04 | 3 criteria |
| 5 | Integration & Testing | 系统集成与 E2E 测试 | INT-01~04 | 4 criteria |

---

## Phase 1: Database Infrastructure

**Goal:** 建立 SQLite 久化基础设施，为对比数据存储提供基础

**Status:** ✓ Complete (2026-05-06)

**Plans:** 2 plans in 2 waves

Plans:
- [x] 01-01-PLAN.md — 配置扩展与数据库管理器实现 (Wave 1) ✓
- [x] 01-02-PLAN.md — 数据库管理器单元测试 (Wave 2, TDD) ✓

### Requirements Mapped

- DB-01: 创建 SQLite 数据库文件 (Plan 01)
- DB-02: `comparison_sessions` 表 (Plan 01)
- DB-03: `provider_results` 表 (Plan 01)
- DB-04: `search_results` 表 (Plan 01)
- DB-05: 数据库初始化脚本 (Plan 01, Plan 02)

### Success Criteria

1. 数据库文件在配置路径创建成功
2. 表结构符合设计，索引建立正确
3. 初始化脚本可独立运行，幂等操作

### Tasks

1. 创建 `melodyi_search/infrastructure/database/` 目录
2. 实现 `database_manager.py` — 数据库连接和表创建
3. 设计表结构 SQL schema
4. 创建索引（session_id, provider, timestamp, source_domain）
5. 单元测试 `test_database_manager.py`

---

## Phase 2: Compare Mode Enhancement

**Goal:** 对比模式完整结果记录与持久化，为供应商质量分析提供数据基础

**Status:** ✓ Complete (2026-05-09)

**Plans:** 3 plans in 3 waves

Plans:
- [x] 02-01-PLAN.md — ComparisonRecorder 服务实现 (Wave 1) — COMP-01, COMP-03, COMP-04, COMP-05 ✓
- [x] 02-02-PLAN.md — ExecutionStrategy 修改 (Wave 2) — COMP-02, COMP-07 ✓
- [x] 02-03-PLAN.md — UnifiedSearchResult 扩展 + 测试覆盖 (Wave 3) — COMP-06 ✓

### Requirements Mapped

- COMP-01: 记录完整搜索结果 (Plan 01)
- COMP-02: 持久化到 SQLite (Plan 02)
- COMP-03: 记录请求参数 (Plan 01)
- COMP-04: 记录排序位置 (Plan 01)
- COMP-05: 记录元数据指标 (Plan 01)
- COMP-06: 返回 session_id (Plan 03)
- COMP-07: 修复 daemon thread 问题 (Plan 02)

### Success Criteria

1. Compare 模式执行后，所有供应商结果写入数据库
2. `search_results` 表包含完整结果（title, url, description 等）
3. session_id 在响应中返回，可追溯

### Key Decisions (from CONTEXT.md)

- D-01: daemon=False + thread.join(timeout=10)
- D-02: 每个供应商完成后立即写入数据库
- D-03: Session ID 格式 YYYYMMDD-HHMMSS-XXXX
- D-04: 持久化失败时日志记录继续执行

### Tasks

1. 创建 `melodyi_search/domain/services/comparison_recorder.py`
2. 修改 `ExecutionStrategy.execute_comparison()` 调用 recorder
3. 修复 daemon thread：使用 `daemon=False` + `thread.join(timeout=10)`
4. 修改 `UnifiedSearchResult` 添加 `session_id` 字段
5. 单元测试 `test_comparison_recorder.py`
6. 集成测试验证完整流程

---

## Phase 3: CLI Commands

**Goal:** 验证 compare 模式数据持久化功能，确保 search --comparison 参数正确工作

**Status:** Planned

**Plans:** 2 plans in 2 waves

Plans:
- [ ] 03-01-PLAN.md — CLI comparison 模式修复 + 配置覆盖实现 (Wave 1)
- [ ] 03-02-PLAN.md — E2E 验证测试 (Wave 2, checkpoint)

### Requirements Mapped

- CLI-01: `search --comparison` 参数覆盖配置开关 (Plan 01) — **Modified by D-01**
- D-05: CLI --comparison 参数覆盖配置开关 (Plan 01)
- D-07: 持久化静默执行，不显示提示信息 (Plan 01)
- D-08: 通过测试验证数据持久化 (Plan 02)

**Note:** CLI-02~06 (history 命令) 已明确抛弃，不实现 (see D-02 in CONTEXT.md)

### Success Criteria

1. `search --comparison` 数据正确持久化到数据库
2. 配置开启时自动启用持久化（无需 CLI 参数）
3. CLI 输出格式不变，不显示 session_id
4. 所有 E2E 测试通过，数据库记录正确

### Key Decisions (from CONTEXT.md)

- D-01: 不新增独立 compare 命令，仅使用 search --comparison
- D-02: 抛弃 history 命令（CLI-02~06），不实现
- D-05: CLI 参数覆盖配置开关
- D-06: CLI 不输出 session_id
- D-07: 持久化静默执行
- D-08: 通过测试验证数据持久化

### Tasks

1. 修复 CLI bug：传递 recorder 参数给 execute_comparison
2. 实现配置覆盖逻辑：`use_comparison = comparison or config.mode.comparison`
3. 创建 DatabaseManager 和 ComparisonRecorder
4. 单元测试 CLI comparison 模式
5. E2E 测试验证完整流程
6. 验证数据库记录正确性

---

## Phase 4: Analysis Features

**Goal:** 供应商质量分析报告

### Requirements Mapped

- ANAL-01: `melodyi-search analyze providers` 命令
- ANAL-02: 成功率、响应时间、结果数统计
- ANAL-03: 域名覆盖分析
- ANAL-04: 按域名查看各供应商表现对比

### Success Criteria

1. `analyze providers` 输出质量报告表格
2. 报告包含各供应商关键指标
3. 域名覆盖分析正确统计

### Tasks

1. 创建 `melodyi_search/application/cli_analyze.py`
2. 创建 `melodyi_search/domain/services/analyzer.py`
3. 实现供应商统计查询（成功率、响应时间均值）
4. 实现域名覆盖分析查询
5. 单元测试 `test_analyzer.py`

---

## Phase 5: Integration & Testing

**Goal:** 系统集成验证，确保现有功能不受影响

### Requirements Mapped

- INT-01: 正常模式不变
- INT-02: skill.md 不变
- INT-03: 配置文件不变
- INT-04: 数据库路径配置项

### Success Criteria

1. 现有 `search` 命令正常模式功能不变
2. E2E 测试覆盖 compare → history → analyze 流程
3. skill.md 格式不变，Agent 集成测试通过
4. 所有单元测试 + 集成测试通过

### Tasks

1. 回归测试现有 `search` 命令
2. E2E 测试：compare → history list → history show → analyze
3. 验证 skill.md 无需修改
4. 添加数据库路径配置项到 `default_config.yaml`
5. 更新 `skill.md` 文档说明 compare/history/analyze 命令（可选）
6. 最终集成测试全部通过

---

## Requirement Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DB-01 | Phase 1 | ✓ Complete |
| DB-02 | Phase 1 | ✓ Complete |
| DB-03 | Phase 1 | ✓ Complete |
| DB-04 | Phase 1 | ✓ Complete |
| DB-05 | Phase 1 | ✓ Complete |
| COMP-01 | Phase 2 | ✓ Complete |
| COMP-02 | Phase 2 | ✓ Complete |
| COMP-03 | Phase 2 | ✓ Complete |
| COMP-04 | Phase 2 | ✓ Complete |
| COMP-05 | Phase 2 | ✓ Complete |
| COMP-06 | Phase 2 | ✓ Complete |
| COMP-07 | Phase 2 | ✓ Complete |
| CLI-01 | Phase 3 | Pending — Modified (D-01: search --comparison) |
| CLI-02 | — | Deferred (D-02: history 命令抛弃) |
| CLI-03 | — | Deferred (D-02: history 命令抛弃) |
| CLI-04 | — | Deferred (D-02: history 命令抛弃) |
| CLI-05 | — | Deferred (D-02: history 命令抛弃) |
| CLI-06 | — | Deferred (D-02: history 命令抛弃) |
| ANAL-01 | Phase 4 | Pending |
| ANAL-02 | Phase 4 | Pending |
| ANAL-03 | Phase 4 | Pending |
| ANAL-04 | Phase 4 | Pending |
| INT-01 | Phase 5 | Pending |
| INT-02 | Phase 5 | Pending |
| INT-03 | Phase 5 | Pending |
| INT-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 16 (CLI-02~06 deferred)
- Deferred: 5 (CLI-02~06 by D-02)
- Unmapped: 0 ✓

---

*Roadmap created: 2026-05-04*
*Phase 1 plans added: 2026-05-06*
*Phase 1 complete: 2026-05-06*
*Phase 2 plans added: 2026-05-09*
*Phase 2 complete: 2026-05-09*
*Phase 3 plans added: 2026-05-09*