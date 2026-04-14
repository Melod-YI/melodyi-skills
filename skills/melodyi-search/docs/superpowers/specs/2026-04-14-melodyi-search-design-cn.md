---
name: melodyi-search-design
description: melodyi-search 多提供商搜索工具设计规范
type: project
---

# melodyi-search 设计规范

## 概述

一个基于 Python 的多提供商搜索工具，通过多个搜索 API 提供商提供统一的搜索能力。采用 DDD 架构设计，支持 CLI 使用、skill.md 用于 Agent 集成，以及提供商隔离便于二次开发。

---

## 架构

### 领域驱动设计分层

```
melodyi-search/
├── domain/                 # 核心领域层
│   ├── models/             # 统一数据模型
│   │   ├── search_request.py    # 统一搜索请求
│   │   ├── search_result.py     # 统一搜索结果
│   │   ├── provider_config.py   # 提供商配置
│   │   └── error.py             # 带指导的错误类型
│   └── services/           # 领域服务
│       ├── search_service.py    # 核心搜索编排
│       ├── execution_strategy.py # 执行策略（正常/比对模式）
│       └── parameter_adapter.py # 参数适配
│
├── providers/              # 提供商实现（隔离）
│   ├── base_provider.py    # 抽象基类
│   ├── brave_provider.py   # Brave Search 实现
│   ├── tavily_provider.py  # Tavily 实现
│   ├── exa_provider.py     # Exa 实现
│   ├── searxng_provider.py # SearXNG 实现
│   ├── firecrawl_provider.py # Firecrawl 实现
│   └── minimax_cn_provider.py # MiniMax-CN（中国大陆）实现
│
├── application/            # 应用层
│   └── cli.py              # CLI 入口
│
├── skill.md                # Agent 集成描述文件（静态）
│
├── infrastructure/         # 基础设施层
│   ├── config/             # 配置管理
│   │   ├── config_loader.py    # 支持 .env + yaml 加载
│   │   ├── config_schema.py
│   │   └── default_config.yaml
│   ├── logging/            # 带指标的日志
│   │   └── search_logger.py
│   └── http/               # HTTP 客户端抽象
│       └── http_client.py
│
├── .env.example            # 环境变量模板（不提交到 git）
├── skill.md                # Agent 集成描述文件（静态）
│
└── tests/                  # 测试
    ├── providers/          # 单元测试（mock）
    └── integration/        # 端到端测试（真实 API）
```

### 提供商隔离原则

`providers/` 目录中的每个提供商实现完全独立：
- 可提取并独立使用
- 具有自己的原生参数处理
- 实现基础提供商接口
- 包含提供商特定的错误处理

---

## 核心模型

### UnifiedSearchRequest（统一搜索请求）

```python
class UnifiedSearchRequest:
    """暴露给 Agent/CLI 的请求模型"""

    query: str                          # 必填 - 搜索查询
    max_results: int = 10               # 期望最大结果数
    time_range: Optional[TimeRange]     # 时间过滤
    include_domains: Optional[List[str]] # 包含特定域名
    exclude_domains: Optional[List[str]] # 排除特定域名
    language: Optional[str]             # ISO 语言代码

    # 提供商覆盖（可选）
    preferred_provider: Optional[str]   # 指定使用某个提供商
```

**注**：比对模式对 Agent 完全透明，不在请求参数中体现。Agent 只需正常调用，系统根据配置决定是否并发执行所有提供商。

### TimeRange（时间范围）

```python
class TimeRange:
    """统一时间范围规范"""

    # 简单范围类型
    range_type: Optional[Literal["day", "week", "month", "year"]]

    # 或精确日期范围
    start_date: Optional[datetime]
    end_date: Optional[datetime]

    # 对于不支持时间过滤的提供商
    # 适配器将在查询中注入关键词
```

### UnifiedSearchResult（统一搜索结果）

```python
class UnifiedSearchResult:
    """暴露给 Agent/CLI 的结果模型"""

    # 提供商信息（在 skill.md 输出中隐藏）
    provider: str                        # 响应的提供商
    response_time_ms: int                # 响应时间

    # 结果
    results: List[SearchResultItem]

    # 用于比对模式 - 所有提供商结果日志
    comparison_log: Optional[dict]       # 内部比对数据

    # 错误及指导（如有）
    error: Optional[SearchError]
```

### SearchResultItem（搜索结果项）

```python
class SearchResultItem:
    """单个搜索结果"""

    title: str
    url: str
    description: str                     # 摘要/片段
    published_date: Optional[datetime]   # 如可用
    source_domain: str                   # 从 URL 提取

    # 提供商特定字段（在核心层保留）
    provider_extra: Optional[dict]       # 原始提供商数据
```

### SearchError（带 Agent 指导的搜索错误）

```python
class SearchError:
    """带 Agent 补救指导的错误"""

    error_type: str                      # 错误分类
    original_message: str                # 提供商原始错误
    guidance: str                        # 指导 Agent 行为的提示

    # 示例：
    # - API_KEY_INVALID: "检查您的 API 密钥配置。密钥应从 [提供商仪表板 URL] 获取。"
    # - RATE_LIMITED: "请求被限流。请等待后重试或切换提供商。"
    # - DOMAIN_FILTER_UNSUPPORTED: "此提供商不支持域名过滤。适配器将使用搜索操作符。"
```

---

## 提供商配置

### 配置规范（YAML）

```yaml
# config.yaml
# providers: 有序数组，决定启用顺序和优先级
# 数组顺序 = 调用优先级（第一个为默认首选）
# 无论是否开启 comparison_mode，此配置都生效

providers:
  - name: minimax-cn              # MiniMax 中国大陆
    api_key: ${MINIMAX_API_KEY}   # 默认使用 https://api.minimaxi.com
    timeout_ms: 10000
    max_results: 10

  - name: tavily
    api_key: ${TAVILY_API_KEY}
    timeout_ms: 10000
    max_results: 20
    default_depth: basic          # Tavily 特定参数

  - name: brave
    api_key: ${BRAVE_API_KEY}
    timeout_ms: 10000
    max_results: 20

  - name: exa
    api_key: ${EXA_API_KEY}
    timeout_ms: 30000             # 深度搜索需要更长超时
    max_results: 10
    default_type: auto            # Exa 特定参数

  - name: searxng                 # 自托管，需要配置 host
    host: http://localhost:8888
    timeout_ms: 15000

  - name: firecrawl               # 自托管或云服务
    api_key: ${FIRECRAWL_API_KEY}
    host: http://localhost:3002   # 自托管地址（可选）
    timeout_ms: 10000

# 运行模式配置
mode:
  comparison: false               # 是否开启比对模式
  log_dir: ./logs                 # 日志目录

# 回退/重试配置
fallback:
  retry_count: 2                  # 同一提供商重试次数
  retry_delay_ms: 1000            # 重试间隔
```

### 配置说明

| 字段 | 说明 |
|------|------|
| `providers` | 有序数组，数组顺序即为调用优先级 |
| `providers[].name` | 提供商名称，支持：`minimax-cn`, `tavily`, `brave`, `exa`, `searxng`, `firecrawl` |
| `providers[].api_key` | API 密钥，支持环境变量引用 `${VAR_NAME}` |
| `providers[].host` | 自托管服务的地址（searxng/firecrawl 必填） |
| `mode.comparison` | 比对模式开关，详见下方"比对模式"章节 |

### 提供商特定配置

- **minimax-cn**：默认使用中国大陆地址 `https://api.minimaxi.com`，无需配置 host
- **searxng**：必须配置 `host` 指向本地实例
- **firecrawl**：可选配置 `host`，不配置则使用云服务
- **tavily**：可选 `default_depth`（basic/advanced）
- **exa**：可选 `default_type`（auto/neural/keyword）

### 环境变量与配置加载

**加载顺序**：
1. 加载 `.env` 文件（使用 `python-dotenv`）
2. 加载 `config.yaml`
3. yaml 中的 `${VAR_NAME}` 被环境变量值替换

**.env.example 模板**：
```bash
# API Keys（测试前填写真实值）
MINIMAX_API_KEY=your_minimax_key
TAVILY_API_KEY=your_tavily_key
BRAVE_API_KEY=your_brave_key
EXA_API_KEY=your_exa_key
FIRECRAWL_API_KEY=your_firecrawl_key
```

**config_loader.py 实现**：
```python
from dotenv import load_dotenv
import os

def load_config(config_path: str = "config.yaml") -> dict:
    # 1. 先加载 .env 到环境变量
    load_dotenv()
    
    # 2. 加载 yaml
    config = yaml.load(config_path)
    
    # 3. 替换 ${VAR_NAME} 为实际环境变量值
    for provider in config["providers"]:
        if "api_key" in provider:
            # ${MINIMAX_API_KEY} -> os.environ["MINIMAX_API_KEY"]
            provider["api_key"] = resolve_env_var(provider["api_key"])
    
    return config
```

---

## 提供商实现模式

### 基础提供商接口

```python
class BaseProvider(ABC):
    """所有提供商的抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """提供商标识符"""

    @abstractmethod
    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        """
        使用提供商原生参数执行搜索。

        注：此方法接收 ProviderSearchRequest，包含
        统一参数和提供商特定参数。
        """

    @abstractmethod
    def supports_time_filter(self) -> bool:
        """是否支持时间过滤"""

    @abstractmethod
    def supports_domain_filter(self) -> bool:
        """是否支持域名过滤"""

    @abstractmethod
    def get_max_results_limit(self) -> int:
        """此提供商可返回的最大结果数"""

    def adapt_parameters(self, unified: UnifiedSearchRequest) -> ProviderSearchRequest:
        """
        将统一请求转换为提供商原生请求。
        处理参数适配策略。
        """
```

### 提供商原生请求（保留差异）

```python
class ProviderSearchRequest:
    """
    保留所有提供商特定参数的提供商原生请求。
    每个提供商实现接收此对象。
    """

    # 核心查询（始终存在）
    query: str

    # 统一参数（已适配）
    max_results: int
    time_range: Optional[TimeRange]
    include_domains: Optional[List[str]]
    exclude_domains: Optional[List[str]]
    language: Optional[str]

    # 提供商特定的原生参数
    native_params: dict                # 原始提供商参数

    # 对于需要修改查询的提供商
    modified_query: Optional[str]      # 注入关键词/操作符的查询
```

---

## 参数适配策略

### 接口层 → 核心层映射

| 统一参数 | Brave | Tavily | Exa | SearXNG | Firecrawl | MiniMax-CN |
|----------|-------|--------|-----|---------|-----------|---------|
|----------|-------|--------|-----|---------|-----------|---------|
| `query` | `q` | `query` | `query` | `q` | `query` | `query` |
| `max_results` | `count` | `max_results` | `numResults` | (受限) | `limit` | (固定) |
| `time_range.day` | `freshness=pd` | `time_range=day` | `startPublishedDate` | `time_range=day` | `tbs=qdr:d` | 注入"今天"关键词 |
| `time_range.week` | `freshness=pw` | `time_range=week` | 计算日期 | `time_range=month` | `tbs=qdr:w` | 注入"本周"关键词 |
| `include_domains` | `site:` 操作符 | `include_domains` | `includeDomains` | `site:` 操作符 | `site:` 操作符 | 后过滤结果 |
| `exclude_domains` | `-site:` 操作符 | `exclude_domains` | `excludeDomains` | `-site:` 操作符 | `-site:` 操作符 | 后过滤结果 |

### MiniMax-CN 特殊处理

MiniMax-CN 参数支持有限：
- **时间过滤**：在查询中注入中文时间关键词
  - Day → "今天 最新"
  - Week → "本周 最新"
  - Month → "本月 最新"
- **域名过滤**：检索后对结果进行后过滤
- **API 地址**：默认使用 `https://api.minimaxi.com`（中国大陆），无需配置

---

## 执行策略

### 领域服务：ExecutionStrategy

`domain/services/execution_strategy.py` 定义两种执行模式（同步实现）：

```python
class ExecutionStrategy:
    """提供商执行策略（同步）"""

    def execute_normal(self, providers: List[Provider], request) -> Result:
        """正常模式：按顺序串行执行，失败时回退"""
        for provider in providers:
            try:
                result = provider.search(request)  # 同步调用
                return result
            except RetryableError:
                continue  # 尝试下一个
        return Error("所有提供商失败")

    def execute_comparison(self, providers: List[Provider], request) -> Result:
        """比对模式：串行执行第一个，其余在后台线程执行
        
        流程：
        1. 执行第一个 provider → 立即返回给调用方
        2. 启动后台线程 → 执行剩余 providers → 记录结果
        """
        # 第一个 provider 正常执行并返回
        result = providers[0].search(request)
        
        # 剩余 provider 在后台线程执行并记录
        def background_task():
            for p in providers[1:]:
                r = p.search(request)
                logger.log_provider_result(...)
        
        threading.Thread(target=background_task, daemon=True).start()
        
        return result  # 立即返回
```

### CLI 调用方式

CLI 根据配置选择策略（同步调用）：

```python
# cli.py
config = load_config()
strategy = ExecutionStrategy()

if config.mode.comparison:
    result = strategy.execute_comparison(enabled_providers, request)
else:
    result = strategy.execute_normal(enabled_providers, request)
```

### 用于回退决策的错误分类

| 错误类型 | 回退？ | 重试？ | 指导 |
|----------|--------|--------|------|
| API_KEY_INVALID | 否 | 否 | "检查 API 密钥配置" |
| RATE_LIMITED | 是 | 否 | "被限流，切换提供商" |
| QUOTA_EXCEEDED | 是 | 否 | "配额耗尽，切换提供商" |
| NETWORK_ERROR | 是 | 是 | "临时网络错误，重试中" |
| TIMEOUT | 是 | 是 | "超时，用更长超时重试" |
| INVALID_REQUEST | 否 | 否 | "修正请求参数" |

---

## 比对模式

### 核心原则：对 Agent 完全透明

比对模式是系统内部行为，Agent 无感知：
- Agent 只需正常调用 `search(query="...")` 或 CLI `melodyi-search "query"`
- 系统根据配置中的 `mode.comparison` 决定执行策略
- Agent 始终收到统一的搜索结果格式

### 执行行为

**正常模式**（`comparison: false`）：
- 按配置数组顺序，从第一个提供商开始
- 失败时自动切换到下一个提供商
- 所有执行过程完整记录到日志

**比对模式**（`comparison: true`）：
- **串行执行第一个提供商**，立即返回给 Agent
- **后台线程执行剩余提供商**，完成后记录结果
- 第一个提供商通常是配置中最高优先级的，成功率本身就高
- Agent 无感知延迟，响应速度等于第一个提供商的响应时间

### 日志记录（无论是否比对模式）

每次搜索都完整记录：

```
[SEARCH] 2026-04-14 10:30:00 | Query: "machine learning tutorials"
[SEARCH] Provider: minimax-cn | Status: success | Time: 850ms | Results: 8
[SEARCH] Result 1: title="..." url="https://..." description="..."
[SEARCH] Result 2: title="..." url="https://..." description="..."
...
[SEARCH] Provider: tavily | Status: success | Time: 1200ms | Results: 15
[SEARCH] Result 1: ...
...
```

比对模式额外汇总：

```
[COMPARISON] Query: "machine learning tutorials"
[COMPARISON] First provider: minimax-cn (850ms) → returned to agent
[COMPARISON] Background providers executing...
[COMPARISON] Summary:
[COMPARISON]   minimax-cn: success, 850ms, 8 results (returned to agent)
[COMPARISON]   tavily: success, 1200ms, 15 results (background)
[COMPARISON]   brave: success, 1500ms, 10 results (background)
[COMPARISON]   exa: timeout, 30000ms (background)
[COMPARISON] Full details: logs/comparison_2026-04-14_10-30-00.json
```

### 比对数据存储

比对模式下，所有提供商的完整结果存储到 JSON 文件：
- 文件位置：`{log_dir}/comparison_{timestamp}.json`
- 内容：每个提供商的完整结果、耗时、状态、错误信息

---

## 带 Agent 指导的错误处理

### 错误类型与指导提示

```python
ERROR_GUIDANCE = {
    "API_KEY_INVALID": """
此提供商的 API 密钥无效或缺失。
操作：检查您的配置，确保 API 密钥设置正确。
提供商仪表板：[提供商特定 URL]
""",

    "RATE_LIMITED": """
请求被此提供商限流。
操作：请等待后重试，或系统将自动切换到另一个提供商。
""",

    "QUOTA_EXCEEDED": """
此提供商的 API 配额已耗尽。
操作：系统将切换到另一个提供商。考虑升级此提供商的计划。
""",

    "DOMAIN_FILTER_UNSUPPORTED": """
此提供商不支持原生域名过滤。
操作：适配器将在查询中使用搜索操作符（site:）或后过滤结果。
""",

    "TIME_FILTER_UNSUPPORTED": """
此提供商不支持时间过滤。
操作：适配器将在查询中注入时间关键词（如"最新"、"今天"）。
""",

    "REGION_MISMATCH": """
API 密钥与主机区域不匹配（MiniMax 特定）。
操作：中国大陆密钥使用 api.minimaxi.com，全球密钥使用 api.minimax.io。
"""
}
```

---

## 日志与可观测能力

### 设计原则

**可观测能力是核心需求**，日志必须满足：
- 仅通过日志即可快速定位 bug 或问题
- 开发阶段依赖日志进行调试和验证
- 生产环境依赖日志进行问题排查

### 必须记录的内容

**每次搜索请求**：
```
[SEARCH] {timestamp} | Query: "{query}"
[SEARCH] Request params: max_results={n}, time_range={range}, domains={domains}
```

**每个提供商执行**：
```
[SEARCH] Provider: {name} | Start: {timestamp}
[SEARCH] Provider: {name} | Status: {success/error} | Time: {ms}ms | Results: {count}
```

**完整结果内容**（无论成功或失败）：
```
[SEARCH] Result 1: title="{title}" url="{url}" description="{desc}"
[SEARCH] Result 2: ...
[SEARCH] Result N: ...
```

**错误详情**：
```
[SEARCH] Provider: {name} | Error: {type} | Message: {original_msg}
[SEARCH] Provider: {name} | Guidance: {agent_guidance}
```

### 日志层级

| 级别 | 用途 |
|------|------|
| INFO | 正常搜索流程、结果记录 |
| DEBUG | 详细参数、适配过程 |
| WARN | 回退触发、重试 |
| ERROR | 提供商失败、配置问题 |

### 日志输出目标

- **控制台**：实时显示（开发阶段）
- **文件**：`{log_dir}/search_{date}.log`（持久存储）
- **JSON**：比对模式完整数据 `{log_dir}/comparison_{timestamp}.json`

### 关键指标

- 每提供商响应时间（毫秒）
- 每提供商成功率
- 每提供商错误类型分布
- 查询结果数量分布

---

## CLI 接口

### 安装

```bash
# 开发环境：使用 venv 避免与其他 Python 应用冲突
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

pip install -e .           # 开发模式安装

# 生产环境：通过 pip
pip install melodyi-search

# 或通过 uv/uvx
uvx install melodyi-search
```

### 命令

```bash
# 基本搜索
melodyi-search "machine learning tutorials"

# 带参数
melodyi-search "AI news" --max-results 20 --time-range week

# 域名过滤
melodyi-search "python tutorials" --include-domains github.com,stackoverflow.com

# 指定提供商（调试用）
melodyi-search "query" --provider minimax-cn

# 配置查看
melodyi-search config show
melodyi-search config set providers.brave.enabled false
```

---

## Skill.md（Agent 集成）

### 关键原则

- **不暴露提供商信息**：skill.md 描述搜索能力，不提及具体提供商
- **嵌入指导**：错误包含 Agent 可执行指导
- **Sources 格式**：结果包含 Sources 部分，供 Agent 引用

### Skill.md 模板

```markdown
---
name: melodyi-search
description: 搜索网络获取知识截止日期之外的信息
---

## 描述

允许搜索网络以获取当前、实时的信息。
返回包含标题、URL 和描述的搜索结果。

## 使用

```python
search(query="machine learning tutorials", max_results=10)
```

## 参数

- query（必填）：搜索查询
- max_results：结果数量（默认 10）
- time_range："day"、"week"、"month"、"year" 或日期范围
- include_domains：要包含的域名列表
- exclude_domains：要排除的域名列表

## 输出格式

返回的搜索结果包含：
- 标题
- URL
- 描述/片段
- 发布日期（如可用）

## 重要说明

- 回答后，请包含 Sources 部分，将所有 URL 作为 markdown 链接
- 查询时使用当前年份（2026）以获取最新信息
- 如发生错误，请按照错误消息中的指导操作

## 错误处理

错误包含可执行的指导。请按照建议解决问题。
```

---

## 测试策略

### 单元测试（tests/providers/）

使用 mock 响应：
- 每个提供商的参数适配测试
- 错误处理测试（模拟各类错误响应）
- 基础提供商接口测试

### 端到端测试（tests/integration/）

**当前版本验证范围**：

| 提供商 | 测试状态 | API Key 来源 |
|--------|----------|--------------|
| minimax-cn | 真实 API 测试 | 用户预制 |
| tavily | 真实 API 测试 | 用户预制 |
| brave | 真实 API 测试 | 用户预制 |
| exa | 真实 API 测试 | 用户预制 |
| searxng | 单元测试（mock） | 自托管，暂不测试 |
| firecrawl | 单元测试（mock） | 暂不提供 |

**测试用例**：
```python
# tests/integration/test_minimax_e2e.py
async def test_minimax_cn_real_search():
    """真实 API 测试，需 MINIMAX_API_KEY"""
    result = await search("python tutorial", provider="minimax-cn")
    assert result.results > 0
    assert result.error is None

# tests/integration/test_brave_e2e.py
async def test_brave_real_search():
    """真实 API 测试，需 BRAVE_API_KEY"""
    result = await search("AI news", provider="brave")
    assert result.results > 0

# tests/integration/test_tavily_e2e.py
async def test_tavily_real_search():
    """真实 API 测试，需 TAVILY_API_KEY"""
    result = await search("machine learning", provider="tavily")
    assert result.results > 0

# tests/integration/test_exa_e2e.py
async def test_exa_real_search():
    """真实 API 测试，需 EXA_API_KEY"""
    result = await search("neural networks", provider="exa")
    assert result.results > 0

# tests/integration/test_fallback_e2e.py
async def test_provider_fallback():
    """测试回退机制"""
    result = await search("test query")
    assert result.provider in ["minimax-cn", "tavily", "brave", "exa"]
```

**运行端到端测试**：
```bash
# 确保 .env 中已填写四个 API Key
pytest tests/integration/ -v
```

### 提供商隔离验证

- 每个提供商可独立导入和使用
- 提供商提取测试：验证提供商模块无需完整包即可工作

---

## 实现优先级

### 第一阶段：核心基础
1. 领域模型（请求/结果/错误）
2. 基础提供商接口
3. 配置规范与加载器
4. 日志基础设施

### 第二阶段：提供商实现
1. MiniMax-CN 提供商（中国区最高调用优先级，参数最简单）
2. Tavily 提供商（功能丰富）
3. Brave 提供商（标准网页搜索）
4. SearXNG 提供商（自托管）

### 第三阶段：编排
1. 执行策略（正常模式 + 比对模式）
2. 参数适配服务
3. 回退/重试机制

### 第四阶段：应用层
1. CLI 实现
2. skill.md 文件

### 第五阶段：完善
1. Exa 提供商（深度搜索功能）
2. Firecrawl 提供商（搜索+抓取）
3. 错误指导细化
4. 文档

---

## 为什么这样设计

**为什么**：项目需要支持具有不同能力的多个搜索提供商，同时为 Agent 提供统一接口，并允许轻松提取单个提供商用于二次开发。

**如何应用**：
- 严格遵循 DDD 分层结构
- `providers/` 中的每个提供商必须独立且可单独导入
- 参数适配发生在服务层，而非提供商层
- 错误指导必须具体且可执行，以便 Agent 自我纠正