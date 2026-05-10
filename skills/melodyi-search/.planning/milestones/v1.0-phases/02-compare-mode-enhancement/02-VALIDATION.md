---
phase: 02
slug: compare-mode-enhancement
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | None - pytest 自动发现 |
| **Quick run command** | `pytest tests/domain/services/test_comparison_recorder.py -x` |
| **Full suite command** | `pytest tests/domain/services/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/domain/services/test_comparison_recorder.py -x`
- **After every plan wave:** Run `pytest tests/domain/services/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | COMP-01, COMP-03, COMP-04, COMP-05 | - | N/A | unit | `pytest tests/domain/services/test_comparison_recorder.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | COMP-06 | - | N/A | unit | `pytest tests/domain/models/test_search_result.py -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | COMP-02, COMP-07 | - | N/A | integration | `pytest tests/domain/services/test_execution_strategy.py::TestComparisonPersistence -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | COMP-06 | - | N/A | unit | `pytest tests/domain/services/test_execution_strategy.py::TestComparisonSessionId -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 3 | COMP-01~07 | - | N/A | integration | `pytest tests/domain/services/ -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/domain/services/test_comparison_recorder.py` — stubs for COMP-01, COMP-03, COMP-04, COMP-05
- [ ] `tests/domain/services/test_execution_strategy.py` 修改 — 添加 COMP-02, COMP-06, COMP-07 测试
- [ ] `tests/domain/models/test_search_result.py` 修改 — 添加 session_id 字段测试

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 后台线程等待超时日志 | COMP-07 | 需手动触发超时场景 | 设置 timeout=1s，运行 compare，检查 WARNING 日志 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---
*Phase: 02-compare-mode-enhancement*
*Created: 2026-05-09*