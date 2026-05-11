---
name: melodyi-web 重命名与 fetch 功能设计
description: 将 melodyi-search 重命名为 melodyi-web，并规划 fetch 网页抓取功能的供应商调研与实现
type: design
created: 2026-05-11
---

# melodyi-web 重命名与 fetch 功能设计

## 项目背景

### 当前状态

- **项目名**: `melodyi-search`
- **定位**: 多提供商搜索聚合工具
- **架构**: DDD 分层 + 多供应商代理模式
- **现有供应商**: MiniMaxCN, Tavily, Brave, Exa, SearXNG, Firecrawl (共 6 个搜索供应商)

### 目标

将项目扩展为"搜索 + 网页抓取"的综合工具：

1. **重命名**: `melodyi-search` → `melodyi-web`，体现更广泛的 web 能力
2. **新增 fetch 功能**: 添加网页全文抓取能力，作为独立领域与 search 并存
3. **供应商调研**: 调研云端 web-fetch SaaS 供应商，为后续实现提供选型依据

### 设计原则

- **保持代理模式**: melodyi-web 本身不实现抓取能力，而是聚合各供应商 API
- **领域独立**: Search 和 Fetch 是两个独立领域，各自有独立抽象和供应商实现
- **共用服务商特例**: Firecrawl 同时提供 search 和 fetch 服务，但两端实现独立

---

## 阶段一：重命名

### 1.1 重命名范围

| 改动项 | 当前值 | 新值 | 涉及文件 |
|--------|--------|------|----------|
| 项目名 | `melodyi-search` | `melodyi-web` | `pyproject.toml` |
| CLI 命令 | `melodyi-search` | `melodyi-web` | `pyproject.toml` (scripts), `cli.py` |
| Python 包目录 | `melodyi_search/` | `melodyi_web/` | 整个目录重命名 |
| 数据目录 | `~/.melodyi-search/` | `~/.melodyi-web/` | `default_config.yaml` |
| 模块描述 | "多提供商搜索工具" | "多提供商搜索与网页抓取工具" | `__init__.py`, `cli.py`, `skill.md` |

### 1.2 目录结构调整

为体现 search 和 fetch 两个独立领域，调整 providers 目录结构：

**当前结构:**
```
melodyi_search/
  providers/
    base_provider.py
    tavily_provider.py
    brave_provider.py
    exa_provider.py
    minimax_cn_provider.py
    searxng_provider.py
    firecrawl_provider.py
    __init__.py
```

**调整后结构:**
```
melodyi_web/
  providers/
    search/
      __init__.py
      base_provider.py              # Search 基类 (原 base_provider.py)
      tavily_provider.py
      brave_provider.py
      exa_provider.py
      minimax_cn_provider.py
      searxng_provider.py
      firecrawl_provider.py         # Firecrawl Search 实现
    fetch/
      __init__.py                   # 空文件，阶段三填充
```

### 1.3 测试目录调整

```
tests/
  providers/
    search/                         # 新增子目录
      __init__.py
      test_base_provider.py
      test_tavily_provider.py
      test_brave_provider.py
      test_exa_provider.py
      test_minimax_cn_provider.py
      test_searxng_provider.py
      test_firecrawl_provider.py
    fetch/
      __init__.py                   # 空文件，阶段三填充
```

### 1.4 Import 路径更新

所有 Python 文件需更新 import:

```python
# 当前
from melodyi_search.domain.models import ...
from melodyi_search.providers.tavily_provider import TavilyProvider

# 新
from melodyi_web.domain.models import ...
from melodyi_web.providers.search.tavily_provider import TavilyProvider
```

### 1.5 文档更新

| 文件 | 更新内容 |
|------|----------|
| `CLAUDE.md` | 项目名引用 |
| `PROJECT.md` | 项目定位描述 |
| `ROADMAP.md` | Roadmap 标题 |
| `skill.md` | skill name: `melodyi-search` → `melodyi-web` |
| `.env.example` | 注释中的项目名 |
| `.planning/` 目录下文档 | 所有项目名引用 |

### 1.6 验证清单

重命名完成后需验证：

- [ ] `pytest` 全部测试通过
- [ ] `melodyi-web --version` 输出正确
- [ ] `melodyi-web search <query>` 功能正常
- [ ] `melodyi-web config show` 功能正常
- [ ] 数据目录使用 `~/.melodyi-web/`

---

## 阶段二：供应商调研

### 2.1 调研目标

调研云端 web-fetch SaaS 供应商，输出调研报告，为阶段三设计提供依据。

### 2.2 调研范围

**仅调研云端 SaaS 服务**，不调研需要自托管的方案。

候选供应商（待调研确认）：

| 供应商 | 类型 | 备注 |
|--------|------|------|
| Jina Reader | 云端 API | 专注网页内容提取 |
| Firecrawl Scrape | 云端 API | 已有 search，检查 scrape 端点 |
| Browserless | 云端 API | 浏览器渲染服务 |
| ScrapingBee | 云端 API | 网页抓取服务 |
| ZenRows | 云端 API | 网页抓取服务 |

### 2.3 调研内容

每个供应商需调研：

1. **API 设计**
   - 端点 URL
   - 请求参数（URL、格式选项、渲染模式等）
   - 响应格式（Markdown、HTML、JSON 等）

2. **能力特性**
   - 是否支持 JS 渲染
   - 是否支持输出格式选择
   - 是否有速率限制

3. **定价模型**
   - 免费额度
   - 付费方案

4. **集成难度**
   - 认证方式（API Key 等）
   - SDK 或直接 HTTP 调用

### 2.4 输出产物

调研报告保存至 `docs/fetch-providers-research.md`，包含：

- 供应商列表及对比表
- 各供应商详细 API 分析
- 推荐优先集成的供应商（Top 2-3）

---

## 阶段三：Fetch 功能设计

### 3.1 领域抽象设计

基于供应商调研结果，设计 fetch 领域的抽象：

```
melodyi_web/
  domain/
    models/
      fetch_request.py       # FetchRequest, FetchResult 等
      fetch_result.py        # 抓取结果模型
    services/
      fetch_executor.py      # Fetch 执行逻辑
  providers/
    fetch/
      base_fetch_provider.py # Fetch 基类
      jina_provider.py       # Jina Reader 实现 (示例)
      firecrawl_provider.py  # Firecrawl Scrape 实现
```

### 3.2 CLI 命令设计

```bash
melodyi-web fetch <url>                 # 单 URL 抓取
melodyi-web fetch <url1> <url2> ...     # 多 URL 批量抓取
melodyi-web fetch --file urls.txt       # 从文件读取 URL 列表
```

可选参数（待调研后确定）：

- `--format`: 输出格式（markdown、html、text）
- `--provider`: 指定供应商
- `--output`: 输出到文件

### 3.3 与 Search 的共用部分

以下基础设施可共用：

- `infrastructure/http/http_client.py` — HTTP 客户端
- `infrastructure/config/` — 配置加载机制
- `infrastructure/logging/` — 日志系统
- `infrastructure/database/` — 数据库（可选扩展 fetch 结果存储）

---

## 阶段四：实现

### 4.1 实现顺序

1. 实现 fetch 领域模型和基类
2. 实现第一个 fetch provider（基于调研推荐）
3. 实现 fetch CLI 命令
4. 添加 fetch 相关测试
5. 集成验证

### 4.2 验证标准

- [ ] fetch 单 URL 功能正常
- [ ] fetch 多 URL 功能正常
- [ ] pytest 全部测试通过
- [ ] skill.md 支持 fetch 调用

---

## 附录

### A. 现有项目文件统计

| 类型 | 数量 | 备注 |
|------|------|------|
| Python 源文件 | 28 个 | `melodyi_search/` 目录 |
| 测试文件 | 35 个 | `tests/` 目录 |
| 文档文件 | 约 40 个 | `.planning/` + `docs/` |

### B. Firecrawl 双端点说明

Firecrawl 提供两个独立端点：

| 端点 | 用途 | 归属领域 |
|------|------|----------|
| `/v1/search` | 网络搜索 | Search |
| `/v1/scrape` | 网页抓取 | Fetch |

当前项目只使用了 `/v1/search`。阶段三可添加 `/v1/scrape` 的 fetch 实现。

---

*Created: 2026-05-11*