# ARCHITECTURE.md

**Last mapped:** 2026-05-04

## 架构模式

项目采用 **DDD (领域驱动设计)** 架构，分层清晰：

```
┌─────────────────────────────────────────────┐
│           Application Layer                 │  ← CLI 入口
│  (melodyi_search/application/)              │
├─────────────────────────────────────────────┤
│           Domain Layer                      │  ← 核心业务逻辑
│  (melodyi_search/domain/)                   │
│    ├── models/                              │  ← 领域模型
│    └── services/                            │  ← 领域服务
├─────────────────────────────────────────────┤
│           Infrastructure Layer              │  ← 技术实现
│  (melodyi_search/infrastructure/)           │
│    ├── config/                              │  ← 配置加载
│    ├── http/                                │  ← HTTP 客户端
│    └── logging/                             │  ← 日志系统
├─────────────────────────────────────────────┤
│           Providers Layer                   │  ← 外部适配
│  (melodyi_search/providers/)                │
│    ├── base_provider.py                     │  ← 抽象接口
│    ├── minimax_cn_provider.py               │  ← MiniMax 实现
│    ├── tavily_provider.py                   │  ← Tavily 实现
│    ├── brave_provider.py                    │  ← Brave 实现
│    ├── exa_provider.py                      │  ← Exa 实现
│    ├── searxng_provider.py                  │  ← SearXNG 实现
│    └── firecrawl_provider.py                │  ← Firecrawl 实现
└─────────────────────────────────────────────┘
```

## 核心概念

### 1. 统一请求/响应模型

领域模型定义统一的输入输出结构，隔离提供商差异：

- `UnifiedSearchRequest` — 统一搜索请求（`melodyi_search/domain/models/search_request.py`）
- `UnifiedSearchResult` — 统一搜索结果（`melodyi_search/domain/models/search_result.py`）
- `SearchError` — 带指导的错误模型（`melodyi_search/domain/models/search_result.py`）

### 2. 提供商抽象

`BaseProvider` 定义提供商接口（`melodyi_search/providers/base_provider.py`）：

```python
class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def search(self, request: ProviderSearchRequest) -> ProviderSearchResult: ...

    @abstractmethod
    def supports_time_filter(self) -> bool: ...

    @abstractmethod
    def supports_domain_filter(self) -> bool: ...
```

### 3. 参数适配器

`ParameterAdapter` 将统一请求适配为提供商原生请求：

```
melodyi_search/domain/services/parameter_adapter.py
```

功能：
- 时间范围适配（提供商不支持时注入时间关键词）
- 域名过滤适配（提供商不支持时使用 site: 操作符或后过滤）

### 4. 执行策略

`ExecutionStrategy` 提供两种执行模式（`melodyi_search/domain/services/execution_strategy.py`）：

- **正常模式**: 串行执行提供商，成功即返回，失败则回退
- **比对模式**: 第一个提供商立即返回，其余后台执行记录对比数据

### 5. 工厂模式

`ProviderFactory` 根据配置创建提供商实例：

```
melodyi_search/domain/services/provider_factory.py
```

## 数据流

```
CLI (click) → UnifiedSearchRequest → ProviderFactory → ParameterAdapter
    ↓
ExecutionStrategy → BaseProvider.search() → ProviderSearchResult
    ↓
UnifiedSearchResult → CLI 输出 (text/json)
```

## 设计决策

| 决策 | 选择 | 环境变量/文件 |
|------|------|--------------|
| 配置管理 | YAML + 环境变量 | `default_config.yaml` + `.env` |
| 错误处理 | 带指导的错误 | `SearchError.guidance` |
| 后台执行 | threading.Thread | daemon=True |
| 日志 | 文件 + 控制台 | `logs/search_{date}.log` |

---

*Mapped by sequential codebase analysis on 2026-05-04*