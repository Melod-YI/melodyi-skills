# STRUCTURE.md

**Last mapped:** 2026-05-04

## 目录布局

```
melodyi-search/
├── melodyi_search/                    # 主包
│   ├── __init__.py                    # 包入口，版本定义
│   ├── __main__.py                    # python -m 入口
│   │
│   ├── application/                   # 应用层
│   │   ├── __init__.py
│   │   └ cli.py                       # CLI 命令定义 (click)
│   │
│   ├── domain/                        # 领域层
│   │   ├── __init__.py
│   │   ├── models/                    # 领域模型
│   │   │   ├── __init__.py
│   │   │   ├── search_request.py      # UnifiedSearchRequest, TimeRange
│   │   │   ├── search_result.py       # SearchResultItem, SearchError
│   │   │   ├── provider_config.py     # ProviderConfig (配置模型)
│   │   │   └ error.py                 # ErrorType 枚举, ERROR_GUIDANCE
│   │   │
│   │   └── services/                  # 领域服务
│   │   │   ├── __init__.py
│   │   │   ├── provider_factory.py    # 创建提供商实例
│   │   │   ├── parameter_adapter.py   # 请求参数适配
│   │   │   ├── execution_strategy.py  # 执行策略 (正常/比对)
│   │   │
│   ├── infrastructure/                # 基础设施层
│   │   ├── __init__.py
│   │   ├── config/                    # 配置加载
│   │   │   ├── __init__.py
│   │   │   ├── config_schema.py       # 配置 Pydantic 模型
│   │   │   ├── config_loader.py       # YAML 加载逻辑
│   │   │   ├── default_config.yaml    # 默认配置文件
│   │   │
│   │   ├── http/                      # HTTP 客户端
│   │   │   ├── __init__.py
│   │   │   ├── http_client.py         # httpx 封装
│   │   │
│   │   ├── logging/                   # 日志系统
│   │   │   ├── __init__.py
│   │   │   ├── search_logger.py       # 搜索日志器
│   │   │
│   ├── providers/                     # 提供商实现
│   │   ├── __init__.py
│   │   ├── base_provider.py           # 抽象基类
│   │   ├── minimax_cn_provider.py     # MiniMax CN 提供商
│   │   ├── tavily_provider.py         # Tavily 提供商
│   │   ├── brave_provider.py          # Brave 提供商
│   │   ├── exa_provider.py            # Exa 提供商
│   │   ├── searxng_provider.py        # SearXNG 提供商
│   │   ├── firecrawl_provider.py      # Firecrawl 提供商
│   │
├── tests/                             # 测试目录 (镜像结构)
│   ├── __init__.py
│   ├── application/
│   │   └ test_cli.py
│   ├── domain/
│   │   ├── models/
│   │   │   ├── test_search_request.py
│   │   │   ├── test_search_result.py
│   │   │   ├── test_provider_config.py
│   │   │   ├── test_error.py
│   │   │   ├── services/
│   │   │   ├── test_provider_factory.py
│   │   │   ├── test_parameter_adapter.py
│   │   │   ├── test_execution_strategy.py
│   │   │
│   ├── infrastructure/
│   │   ├── config/
│   │   │   ├── test_config_schema.py
│   │   │   ├── test_config_loader.py
│   │   ├── http/
│   │   │   ├── test_http_client.py
│   │   ├── logging/
│   │   │   ├── test_search_logger.py
│   │   │
│   ├── providers/
│   │   ├── test_base_provider.py
│   │   ├── test_tavily_provider.py
│   │   ├── test_exa_provider.py
│   │   ├── test_searxng_provider.py
│   │   ├── test_firecrawl_provider.py
│   │   ├── test_minimax_cn_provider.py
│   │   ├── test_brave_provider.py
│   │
│   ├── integration/                   # 集成测试
│   │   ├── test_tavily_e2e.py
│   │   ├── test_exa_e2e.py
│   │   ├── test_brave_e2e.py
│   │   ├── test_minimax_cn_e2e.py
│   │
├── pyproject.toml                     # 项目配置
├── skill.md                           # Agent 使用文档
├── 需求.md                            # 需求设计文档
└─────────────────────────────────────┘
```

## 关键文件位置

| 功能 | 文件路径 |
|------|----------|
| CLI 入口 | `melodyi_search/application/cli.py` |
| 统一请求模型 | `melodyi_search/domain/models/search_request.py` |
| 统一响应模型 | `melodyi_search/domain/models/search_result.py` |
| 错误类型 | `melodyi_search/domain/models/error.py` |
| 提供商工厂 | `melodyi_search/domain/services/provider_factory.py` |
| 执行策略 | `melodyi_search/domain/services/execution_strategy.py` |
| 参数适配 | `melodyi_search/domain/services/parameter_adapter.py` |
| 提供商基类 | `melodyi_search/providers/base_provider.py` |
| 配置加载 | `melodyi_search/infrastructure/config/config_loader.py` |
| 默认配置 | `melodyi_search/infrastructure/config/default_config.yaml` |
| HTTP 客户端 | `melodyi_search/infrastructure/http/http_client.py` |
| 日志系统 | `melodyi_search/infrastructure/logging/search_logger.py` |

## 命名约定

| 类型 | 约定 |
|------|------|
| 目录 | snake_case |
| 文件 | snake_case (如 `search_request.py`) |
| 类 | PascalCase (如 `UnifiedSearchRequest`) |
| 函数 | snake_case (如 `load_config`) |
| 测试文件 | `test_{module}.py` |

---

*Mapped by sequential codebase analysis on 2026-05-04*