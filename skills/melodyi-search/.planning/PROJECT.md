# melodyi-search

## What This Is

一个**供应商质量分析基础设施**，通过 Compare 模式同时调用多家搜索供应商，记录完整结果和元数据到 SQLite，用于数据驱动的供应商择优决策。

为 Agent 提供统一的 `skill.md`，无需关心各 Agent 内置搜索工具的供应商差异。

## Core Value

**Compare 模式的完整结果记录与持久化** — 这是分析供应商质量的基础，让择优选取有数据支撑。

## Requirements

### Validated (v1.0 — 2026-05-10)

- ✓ **SQLite 持久化基础设施** — DB-01~05
  - DatabaseConfig 配置模型、DatabaseManager 管理器
  - comparison_sessions/provider_results/search_results 三张业务表
  - 六个查询索引（session_id, provider, timestamp, source_domain）
  
- ✓ **Compare 模式完整结果记录** — COMP-01~07
  - 所有供应商完整结果写入数据库（而非仅元数据）
  - 请求参数记录（query, max_results, time_range, domains 等）
  - 排序位置记录（rank 字段）
  - 元数据指标（response_time_ms, results_count, error_type）
  - daemon thread 修复（daemon=False + join(timeout=10））

- ✓ **CLI comparison 参数** — CLI-01 (modified)
  - search --comparison 参数覆盖配置开关
  - 持久化静默执行，输出格式不变

- ✓ **集成验证** — INT-01~04
  - Normal Search 模式不变
  - skill.md 参数定义不变
  - 配置向后兼容
  - 数据库为可选组件

### Active (v2 Candidates)

- [ ] **ANAL-01~04: 供应商质量分析报告** — Phase 4 deferred
  - 成功率、响应时间、结果数统计
  - 域名覆盖分析
  - 按域名查看各供应商表现对比

- [ ] **PERF-01~03: 性能优化**
  - 批量插入优化
  - 索引优化
  - 历史数据清理策略

### Out of Scope

| Feature | Reason | Status |
|---------|--------|--------|
| Fetch 系统 | 未来独立项目，共用架构思路 | Planned |
| 实时监控告警 | 当前聚焦于对比分析 | — |
| 多用户/权限 | 单用户 CLI 工具 | — |
| Web UI | CLI + 数据导出足够 | — |
| 外部数据库 | SQLite 足够 | — |
| CLI-02~06 History 命令 | D-02: 抛弃，不实现 | Dropped v1.0 |

## Context

### 技术环境

- Python >=3.10
- DDD 架构：`domain/` `infrastructure/` `providers/` `application/` 分层
- Pydantic V2 数据验证
- httpx HTTP 客户端
- pytest 测试框架
- SQLite 持久化（v1.0 新增）

### Shipped v1.0 Status

- **LOC:** 3,483 Python
- **Tests:** 446 pytest tests, 全部通过
- **Timeline:** 27 天 (2026-04-13 → 2026-05-10)
- **Phases:** 4 phases completed (Phase 4 skipped)
- **Plans:** 8 plans executed

### Known Technical Debt

- Phase 4 (Analysis Features) deferred to v2
- PERF-01~03 性能优化未实现

## Key Decisions

| Decision | Rationale | Outcome | Phase |
|----------|-----------|---------|-------|
| SQLite 持久化 | 小团队规模，单文件易管理 | ✓ Good | 01 |
| Lazy initialization | CLI 启动时自动创建数据库 | ✓ Good | 01 |
| 连接管理: 每次操作新建连接 | 简化事务边界 | ✓ Good | 01 |
| daemon=False + join(timeout=10) | 修复后台线程写入丢失 | ✓ Good | 02 |
| 每个供应商完成后立即写入 | 减少数据丢失风险 | ✓ Good | 02 |
| Session ID: YYYYMMDD-HHMMSS-XXXX | 可追溯且唯一 | ✓ Good | 02 |
| CLI 仅 search --comparison | 无独立 compare 命令 | ✓ Good | 03 |
| History 命令抛弃 | 不实现 CLI-02~06 | ✓ Good | 03 |
| Compare 静默执行 | 输出格式不变 | ✓ Good | 03 |
| 数据库为可选组件 | 不影响现有路径 | ✓ Good | 05 |

## Constraints

- **Python 版本**: >=3.10 — 使用现代 Python 特性
- **架构**: DDD 分层 — 保持领域层纯净
- **持久化**: SQLite — 小团队规模，单文件易管理
- **Agent 集成**: skill.md 格式 — 复制到各 Agent 无需修改

## Evolution

此文档在 Phase 过渡和 Milestone 边界时演进。

---
*Last updated: 2026-05-10 after v1.0 milestone completion*