# INTEGRATIONS.md

**Last mapped:** 2026-05-04

## 外部 API 集成

melodyi-search 作为搜索聚合工具，集成多个外部搜索 API 提供商。

### 搜索提供商

| 提供商 | API 类型 | 认证方式 | 区域 | 文件 |
|--------|----------|----------|------|------|
| **MiniMax CN** | Coding Plan Search | API Key | 中国大陆 | `melodyi_search/providers/minimax_cn_provider.py` |
| **Tavily** | Search API | API Key | 全球 | `melodyi_search/providers/tavily_provider.py` |
| **Brave** | Search API | API Key | 全球 | `melodyi_search/providers/brave_provider.py` |
| **Exa** | Search API | API Key | 全球 | `melodyi_search/providers/exa_provider.py` |
| **SearXNG** | 本地部署 | Optional Key | 本地 | `melodyi_search/providers/searxng_provider.py` |
| **Firecrawl** | 本地部署 | API Key | 本地 | `melodyi_search/providers/firecrawl_provider.py` |

### API 配置管理

配置通过 YAML 文件 + 环境变量组合：

```yaml
# default_config.yaml
providers:
  - name: minimax-cn
    api_key: ${MINIMAX_API_KEY}  # 从环境变量读取
    timeout_ms: 10000
    max_results: 10
```

环境变量映射：

| 提供商 | 环境变量 |
|--------|----------|
| MiniMax CN | `MINIMAX_API_KEY` |
| Tavily | `TAVILY_API_KEY` |
| Brave | `BRAVE_API_KEY` |
| Exa | `EXA_API_KEY` |

### HTTP 客户端

统一 HTTP 客户端封装：

```
melodyi_search/infrastructure/http/http_client.py
```

- 使用 `httpx` 库
- 支持超时配置
- 记录响应时间

## 认证方式

| 认证类型 | 使用位置 |
|----------|----------|
| API Key Header | MiniMax, Tavily, Brave, Exa, Firecrawl |
| Query Param | SearXNG (可选) |

## 无数据库

项目当前不使用数据库，所有配置通过文件和环境变量管理。

## 无消息队列

项目为同步/简单异步架构，不使用消息队列。后台执行使用 `threading.Thread(daemon=True)`。

---

*Mapped by sequential codebase analysis on 2026-05-04*