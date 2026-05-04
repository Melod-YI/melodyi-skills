# Requirements: melodyi-search Compare Enhancement

**Defined:** 2026-05-04
**Core Value:** Compare 模式的完整结果记录与持久化 — 供应商质量分析的基础

## v1 Requirements

### Database (持久化基础设施)

- [ ] **DB-01**: 创建 SQLite 数据库文件，路径可配置（默认 `./data/compare.db`）
- [ ] **DB-02**: 设计 `comparison_sessions` 表存储每次对比执行（session_id, query, params, timestamp）
- [ ] **DB-03**: 设计 `provider_results` 表存储各供应商结果（session_id, provider, response_time, results_count, error_type, status）
- [ ] **DB-04**: 设计 `search_results` 表存储完整搜索结果（session_id, provider, rank, title, url, description, published_date, source_domain）
- [ ] **DB-05**: 实现数据库初始化脚本，创建表结构和索引

### Compare Mode (对比模式增强)

- [ ] **COMP-01**: Compare 模式执行时，记录所有供应商的完整搜索结果（而非仅元数据）
- [ ] **COMP-02**: 执行完成后，将对比数据持久化到 SQLite（而非内存）
- [ ] **COMP-03**: 记录请求参数：query、max_results、time_range、include_domains、exclude_domains、language
- [ ] **COMP-04**: 记录各供应商结果的排序位置（rank 字段），用于相关性对比分析
- [ ] **COMP-05**: 记录元数据指标：response_time_ms、results_count、error_type、error_message
- [ ] **COMP-06**: 修改 `ExecutionStrategy.execute_comparison()` 返回包含 session_id 的结果
- [ ] **COMP-07**: 后台线程执行完成后，确保数据库写入完成（修复 daemon thread 问题）

### CLI Commands (命令行扩展)

- [ ] **CLI-01**: 新增 `melodyi-search compare <query>` 命令，强制启用对比模式
- [ ] **CLI-02**: 新增 `melodyi-search history list` 命令，列出历史对比记录
- [ ] **CLI-03**: 新增 `melodyi-search history show <session-id>` 命令，查看单次对比详情
- [ ] **CLI-04**: 新增 `melodyi-search history export` 命令，导出对比数据为 JSON/CSV
- [ ] **CLI-05**: 支持按时间范围筛选历史记录（--from, --to）
- [ ] **CLI-06**: 支持按供应商筛选历史记录（--provider）

### Analysis (质量分析)

- [ ] **ANAL-01**: 新增 `melodyi-search analyze providers` 命令，生成供应商质量报告
- [ ] **ANAL-02**: 报告包含各供应商成功率、平均响应时间、平均结果数
- [ ] **ANAL-03**: 报告包含各供应商域名覆盖分析（哪些域名只有某供应商能返回）
- [ ] **ANAL-04**: 支持按域名查看各供应商表现对比

### Integration (与现有系统集成)

- [ ] **INT-01**: 保持现有 `search` 命令正常模式不变，Compare 作为可选增强
- [ ] **INT-02**: skill.md 保持不变，Agent 使用方式不变
- [ ] **INT-03**: 配置文件无需修改，沿用现有 YAML + 环境变量格式
- [ ] **INT-04**: 新增数据库路径配置项（可选，默认 ./data/compare.db）

## v2 Requirements

### Advanced Analysis

- **ANAL-05**: 结果相关性评分（同一 URL 在多家供应商出现的位置对比）
- **ANAL-06**: 时效性分析（各供应商返回结果的发布日期分布）
- **ANAL-07**: 去重分析（同一 URL 在多家供应商重复出现）

### Performance Optimization

- **PERF-01**: 批量插入优化（大量结果时使用事务）
- **PERF-02**: 数据库索引优化（按时间、供应商、域名查询加速）
- **PERF-03**: 历史数据清理策略（保留最近 N 天或 N 次对比）

## Out of Scope

| Feature | Reason |
|---------|--------|
| Fetch 系统 | 未来独立项目，共用架构思路和存储介质 |
| 实时监控告警 | 当前聚焦于对比分析和事后查询 |
| 多用户/权限 | 单用户 CLI 工具 |
| Web UI | CLI + 数据导出足够，Web UI 可后续添加 |
| 外部数据库 | SQLite 足够，小团队规模无需 PostgreSQL |
| 分布式部署 | 单机工具，无需分布式 |

## Traceability

更新于 Roadmap 创建时。

---

*Requirements defined: 2026-05-04*