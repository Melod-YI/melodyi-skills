# melodyi-search

## What This Is

一个**供应商质量分析基础设施**，而非简单的搜索聚合工具。通过 Compare 模式同时调用多家搜索供应商，记录完整结果和元数据，用于数据驱动的供应商择优决策。

为 Agent 提供统一的 `skill.md`，无需关心各 Agent 内置搜索工具的供应商差异。后续将扩展 Fetch 系统采用类似架构。

## Core Value

**Compare 模式的完整结果记录与持久化** — 这是分析供应商质量的基础，让择优选取有数据支撑。

## Requirements

### Validated

现有代码已实现的功能：

- ✓ **多提供商架构** — DDD 分层设计，6 家供应商适配 (MiniMax CN, Tavily, Brave, Exa, SearXNG, Firecrawl)
- ✓ **统一请求/响应模型** — `UnifiedSearchRequest` → 提供商适配 → `UnifiedSearchResult`
- ✓ **CLI 命令行工具** — `melodyi-search search` 命令，支持 text/json 输出
- ✓ **正常执行模式** — 串行执行提供商，成功即返回，失败则回退
- ✓ **基础 Compare 模式** — 第一个提供商返回，其余后台执行
- ✓ **配置管理** — YAML 配置 + 环境变量，支持超时、重试设置
- ✓ **错误处理与指导** — `SearchError.guidance` 为 Agent 提供补救提示
- ✓ **测试覆盖** — 单元测试 + E2E 集成测试

### Active

待实现的核心需求：

- [ ] **Compare 模式完整结果记录** — 记录所有供应商的搜索结果（标题、URL、摘要、发布时间），而非仅元数据
- [ ] **SQLite 持久化** — 对比数据存储到本地数据库，支持事后查询分析
- [ ] **元数据指标记录** — 响应时间、结果数量、错误类型、排序位置
- [ ] **请求参数记录** — query、time_range、domains 等，确保可复现
- [ ] **结果排序差异分析** — 记录各家供应商的排序位置，用于相关性对比
- [ ] **对比数据查询接口** — CLI 命令查询历史对比数据，支持按时间/供应商/域名筛选
- [ ] **质量分析报告** — 生成供应商质量报告（成功率、响应时间、结果相关性）

### Out of Scope

- **Fetch 系统** — 未来独立项目，共用架构思路和存储介质，松耦合
- **实时监控告警** — 当前聚焦于对比分析，不提供实时监控
- **多用户/权限管理** — 单用户 CLI 工具
- **大规模分布式部署** — 小团队数据规模，单机 SQLite

## Context

### 技术环境

- Python >=3.10
- DDD 架构：`domain/` `infrastructure/` `providers/` `application/` 分层
- Pydantic V2 数据验证
- httpx HTTP 客户端
- pytest 测试框架

### 现有代码状态

- 6 个搜索提供商已实现
- Compare 模式仅记录元数据（状态、时间、数量），缺失完整结果记录
- 无持久化机制，对比数据仅存内存

### 用户需求背景

用户预感 Agent 行业对搜索/网页抓取服务的依赖会越来越高，需要：
1. 分析各供应商服务质量（相关度、时效性、稳定性）
2. 择优选取供应商
3. 得到"某域名需特定供应商才能抓取"的信息
4. 得到"某域名所有供应商都抓不了"的信息，在搜索阶段就排除

## Constraints

- **Python 版本**: >=3.10 — 使用现代 Python 特性
- **架构**: DDD 分层 — 保持领域层纯净，便于扩展新提供商
- **持久化**: SQLite — 小团队规模，单文件易管理
- **Agent 集成**: skill.md 格式 — 复制到各 Agent 无需修改

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQLite 持久化 | 小团队数据规模，单文件易管理，无需外部部署 | — Pending |
| Compare 模式后台执行 | 使用 threading.Thread(daemon=True) | ⚠️ Revisit — daemon 线程可能未完成写入 |
| 错误带 Agent 指导 | `SearchError.guidance` 引导 Agent 补救行为 | ✓ Good |
| 统一请求模型 | 隔离提供商差异，便于添加新供应商 | ✓ Good |

## Evolution

此文档在 Phase 过渡和 Milestone 边界时演进。

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-04 after initialization*