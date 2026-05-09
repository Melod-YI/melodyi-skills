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
| 3 | CLI Commands | 对比历史查询与分析命令 | CLI-01~06 | 3 criteria |
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

**Goal:** 对比历史查询与分析命令行工具

### Requirements Mapped

- CLI-01: `melodyi-search compare <query>`
- CLI-02: `melodyi-search history list`
- CLI-03: `melodyi-search history show <session-id>`
- CLI-04: `melodyi-search history export`
- CLI-05: 时间范围筛选
- CLI-06: 供应商筛选

### Success Criteria

1. `compare` 命令成功执行对比并返回 session_id
2. `history list` 显示历史记录列表
3. `history show` 显示单次对比详情

### Tasks

1. 创建 `melodyi_search/application/cli_history.py`
2. 实现 `compare` 命令（重用现有 search 但强制 comparison=True）
3. 实现 `history` group 及子命令
4. 添加筛选参数支持（--from, --to, --provider）
5. 单元测试 `test_cli_history.py`

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
| CLI-01 | Phase 3 | Pending |
| CLI-02 | Phase 3 | Pending |
| CLI-03 | Phase 3 | Pending |
| CLI-04 | Phase 3 | Pending |
| CLI-05 | Phase 3 | Pending |
| CLI-06 | Phase 3 | Pending |
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
- Mapped to phases: 22
- Unmapped: 0 ✓

---

*Roadmap created: 2026-05-04*
*Phase 1 plans added: 2026-05-06*
*Phase 1 complete: 2026-05-06*
*Phase 2 plans added: 2026-05-09*
*Phase 2 complete: 2026-05-09*