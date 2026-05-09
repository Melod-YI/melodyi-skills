# Phase 2: Compare Mode Enhancement - Research

**Researched:** 2026-05-09
**Domain:** Compare 模式数据持久化与后台线程管理
**Confidence:** HIGH

## Summary

Phase 2 的核心任务是修改 Compare 模式，使其能够记录所有供应商的完整搜索结果并持久化到 SQLite 数据库。关键挑战在于修复 daemon thread 问题（确保后台线程写入完成）和设计数据写入流程（不阻塞主流程）。

研究发现现有 `execution_strategy.py` 使用 `daemon=True` 的后台线程，这会导致进程退出时后台线程可能未完成写入，造成数据丢失。根据 CONTEXT.md 的决策 D-01，需要改用 `daemon=False` 并配合 `thread.join(timeout=10)` 等待写入完成。

**Primary recommendation:** 创建 `ComparisonRecorder` 服务类处理数据写入，修改 `ExecutionStrategy.execute_comparison()` 调用 recorder 并等待后台线程完成。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 使用 `thread.join(timeout)` 等待后台线程完成
  - 设置 `daemon=False`，主进程退出前等待
  - timeout = 10 秒，超时后继续退出
  - **Why:** daemon=True 导致进程退出时后台线程未完成写入，数据丢失

- **D-02:** 每个供应商完成后立即写入数据库
  - 单条 autocommit（Phase 1 决策）
  - 错误隔离，失败不影响其他供应商
  - **Why:** 批量写入增加事务复杂度，单个写入更简单

- **D-03:** 时间戳前缀 + 随机数生成 Session ID
  - 格式：`YYYYMMDD-HHMMSS-XXXX`（如 `20260509-143052-a1b2`）
  - 8 位随机字符（十六进制）
  - **Why:** UUID4 不可读，时间戳前缀便于历史查询和日志追溯

- **D-04:** 持久化失败时日志记录继续执行，不中断 CLI 返回
  - 后台写入失败：记录 ERROR 日志
  - 不抛出异常，保障主体功能
  - **Why:** 持久化是次要功能，不能阻塞主流程

### Claude's Discretion

基于用户核心约束"优先保障 CLI 主体功能可用"，以下由 Claude 自行决定：
- 后台线程等待时长（10 秒 timeout）
- Session ID 格式（时间戳 + 随机数）
- 写入失败时的处理策略（日志记录继续）

### Deferred Ideas (OUT OF SCOPE)

None - 讨论保持在 Phase 范围内。
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMP-01 | Compare 模式执行时，记录所有供应商的完整搜索结果（而非仅元数据） | comparison_recorder.py 实现完整结果写入 |
| COMP-02 | 执行完成后，将对比数据持久化到 SQLite（而非内存） | database_manager.py 表结构已就绪 |
| COMP-03 | 记录请求参数：query、max_results、time_range、include_domains、exclude_domains、language | comparison_sessions 表 params 字段（JSON） |
| COMP-04 | 记录各供应商结果的排序位置（rank 字段） | search_results 表 rank 字段 |
| COMP-05 | 记录元数据指标：response_time_ms、results_count、error_type、error_message | provider_results 表结构 |
| COMP-06 | 修改 `ExecutionStrategy.execute_comparison()` 返回包含 session_id 的结果 | UnifiedSearchResult 新增 session_id 字段 |
| COMP-07 | 后台线程执行完成后，确保数据库写入完成（修复 daemon thread 问题） | daemon=False + thread.join(timeout=10) |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Session ID 生成 | Domain | - | 业务逻辑，应属于领域服务 |
| 数据写入编排 | Domain | Infrastructure | ComparisonRecorder 协调写入逻辑 |
| 数据库操作 | Infrastructure | - | 技术实现，基础设施层职责 |
| 线程管理 | Domain | - | 执行策略控制，领域服务职责 |
| 结果返回 | Application | Domain | CLI 入口组装返回结果 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11.5 | 运行环境 | [VERIFIED: python --version] |
| SQLite | 3.41.2 | 数据持久化 | [VERIFIED: sqlite3.sqlite_version] - 足够小团队规模 |
| threading | stdlib | 后台执行 | [CITED: Python docs] - daemon=False + join(timeout) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | 测试框架 | [VERIFIED: pip show pytest] - 单元/集成测试 |
| Pydantic V2 | 2.x | 数据验证 | [ASSUMED] - 模型验证和配置 |
| json (stdlib) | - | 参数序列化 | params 字段 JSON 存储 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| threading.Thread | asyncio | asyncio 更现代但现有代码用 threading，改造成本高 |
| join(timeout=10) | join() 无限等待 | 无限等待可能阻塞主流程，timeout 保障可用性 |

**Installation:**
无需额外安装 - 全部使用 Python 标准库和现有依赖。

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLI Entry Point (Application)                      │
│                           melodyi_search/application/cli.py                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Execution Strategy (Domain)                           │
│                    melodyi_search/domain/services/execution_strategy.py       │
│                                                                              │
│  execute_comparison()                                                        │
│    ├── 1. 生成 session_id (via ComparisonRecorder)                           │
│    ├── 2. 执行第一个 provider → 立即返回                                      │
│    ├── 3. 创建后台线程 (daemon=False)                                         │
│    │     └── _execute_background_providers()                                 │
│    │           ├── 调用 provider.search()                                    │
│    │           ├── 调用 ComparisonRecorder.write_provider_result()           │
│    │           └── 调用 ComparisonRecorder.write_search_results()            │
│    ├── 4. 等待后台线程完成 (thread.join(timeout=10))                          │
│    └── 5. 返回 UnifiedSearchResult (含 session_id)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Comparison Recorder (Domain)                           │
│               melodyi_search/domain/services/comparison_recorder.py           │
│                                                                              │
│  ├── generate_session_id() → "20260509-143052-a1b2"                          │
│  ├── write_session() → INSERT comparison_sessions                            │
│  ├── write_provider_result() → INSERT provider_results                       │
│  └── write_search_results() → INSERT search_results (batch)                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Database Manager (Infrastructure)                      │
│           melodyi_search/infrastructure/database/database_manager.py           │
│                                                                              │
│  ├── get_connection() → sqlite3.Connection                                   │
│  ├── init_database() → 表创建（已完成 Phase 1）                               │
│  └── 未来：insert_session(), insert_provider_result(), insert_search_results │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SQLite Database                                     │
│                           ./data/compare.db                                   │
│                                                                              │
│  comparison_sessions ──┬── provider_results ──┬── search_results             │
│  (session_id, query,   │  (session_id,        │  (session_id, provider,      │
│   params, timestamp)   │   provider,          │   rank, title, url, ...)     │
│                        │   response_time_ms,  │                              │
│                        │   error_type, ...)   │                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
melodyi_search/
├── domain/
│   ├── models/
│   │   └ search_result.py       # [MODIFY] 添加 session_id 字段
│   └── services/
│       ├── execution_strategy.py  # [MODIFY] 调用 recorder, 等待线程
│       └ comparison_recorder.py   # [NEW] 数据写入服务
│
├── infrastructure/
│   └ database/
│       ├── database_manager.py    # [EXTEND] 添加写入方法（可选）
│
└── tests/
    └── domain/
        └ services/
            ├── test_execution_strategy.py  # [MODIFY] 添加持久化测试
            └ test_comparison_recorder.py   # [NEW] recorder 单元测试
```

### Pattern 1: ComparisonRecorder 服务类

**What:** 领域服务，负责协调数据写入逻辑，隔离数据库操作细节

**When to use:** Compare 模式下每次供应商执行完成后调用

**Example:**
```python
# Source: [设计基于 CONTEXT.md D-02, D-03]
# melodyi_search/domain/services/comparison_recorder.py

import json
import logging
import random
import string
from datetime import datetime
from typing import List, Optional
from melodyi_search.infrastructure.database.database_manager import DatabaseManager
from melodyi_search.providers.base_provider import ProviderSearchRequest, ProviderSearchResult

logger = logging.getLogger(__name__)


class ComparisonRecorder:
    """对比数据记录服务
    
    负责:
    - Session ID 生成 (D-03)
    - 数据写入编排 (D-02)
    - 错误处理 (D-04)
    """
    
    def __init__(self, database_manager: DatabaseManager):
        self._db = database_manager
    
    def generate_session_id(self) -> str:
        """生成 Session ID (D-03)
        
        格式: YYYYMMDD-HHMMSS-XXXX (时间戳 + 4位十六进制随机数)
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        random_suffix = ''.join(random.choices('0123456789abcdef', k=4))
        return f"{timestamp}-{random_suffix}"
    
    def write_session(
        self,
        session_id: str,
        request: ProviderSearchRequest
    ) -> None:
        """写入 session 元数据
        
        Args:
            session_id: 会话 ID
            request: 搜索请求参数
        
        持久化失败时记录日志继续 (D-04)
        """
        try:
            params_json = json.dumps({
                "max_results": request.max_results,
                "time_range": request.time_range.range_type if request.time_range else None,
                "include_domains": request.include_domains,
                "exclude_domains": request.exclude_domains,
                "language": request.language
            }, ensure_ascii=False)
            
            conn = self._db.get_connection()
            conn.execute(
                """INSERT INTO comparison_sessions 
                   (session_id, query, params, timestamp) 
                   VALUES (?, ?, ?, ?)""",
                (session_id, request.query, params_json, datetime.now().timestamp())
            )
            conn.commit()
            conn.close()
            logger.info(f"Session written: {session_id}")
        except Exception as e:
            logger.error(f"Failed to write session {session_id}: {e}")
            # D-04: 不抛出异常，继续执行
    
    def write_provider_result(
        self,
        session_id: str,
        result: ProviderSearchResult
    ) -> None:
        """写入供应商结果 (D-02)
        
        Args:
            session_id: 会话 ID
            result: 供应商执行结果
        
        持久化失败时记录日志继续 (D-04)
        """
        try:
            status = "success" if result.error is None else "error"
            error_type = None
            error_message = result.error
            
            conn = self._db.get_connection()
            conn.execute(
                """INSERT INTO provider_results 
                   (session_id, provider, response_time_ms, results_count, 
                    error_type, error_message, status) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, result.provider, result.response_time_ms,
                 len(result.results), error_type, error_message, status)
            )
            conn.commit()
            conn.close()
            logger.info(f"Provider result written: {session_id}/{result.provider}")
        except Exception as e:
            logger.error(f"Failed to write provider result {session_id}/{result.provider}: {e}")
            # D-04: 不抛出异常，继续执行
    
    def write_search_results(
        self,
        session_id: str,
        provider: str,
        results: List['SearchResultItem']
    ) -> None:
        """写入搜索结果详情 (COMP-01, COMP-04)
        
        Args:
            session_id: 会话 ID
            provider: 供应商名称
            results: 搜索结果列表（含 rank）
        
        持久化失败时记录日志继续 (D-04)
        """
        try:
            conn = self._db.get_connection()
            for rank, item in enumerate(results, start=1):
                conn.execute(
                    """INSERT INTO search_results 
                       (session_id, provider, rank, title, url, description, 
                        published_date, source_domain) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (session_id, provider, rank, item.title, item.url,
                     item.description, 
                     item.published_date.isoformat() if item.published_date else None,
                     item.source_domain)
                )
            conn.commit()
            conn.close()
            logger.info(f"Search results written: {session_id}/{provider} ({len(results)} items)")
        except Exception as e:
            logger.error(f"Failed to write search results {session_id}/{provider}: {e}")
            # D-04: 不抛出异常，继续执行
```

### Pattern 2: 修改 ExecutionStrategy

**What:** 在 execute_comparison() 中集成 ComparisonRecorder

**When to use:** Compare 模式执行时

**Example:**
```python
# Source: [设计基于 CONTEXT.md D-01]
# melodyi_search/domain/services/execution_strategy.py 修改

def execute_comparison(
    self,
    providers: List[BaseProvider],
    request: ProviderSearchRequest,
    recorder: ComparisonRecorder,  # 新增参数
    on_provider_complete: Optional[Callable[[ProviderSearchResult], None]] = None
) -> UnifiedSearchResult:
    """比对模式执行
    
    D-01: daemon=False + thread.join(timeout=10)
    COMP-06: 返回包含 session_id 的结果
    """
    if not providers:
        return self._create_empty_error_result("NO_PROVIDERS", "没有可用的提供商")
    
    # D-03: 生成 session_id
    session_id = recorder.generate_session_id()
    
    # 写入 session 元数据
    recorder.write_session(session_id, request)
    
    first_provider = providers[0]
    remaining_providers = providers[1:]
    
    # 执行第一个供应商
    first_result = first_provider.search(request)
    
    # D-02: 立即写入第一个供应商结果
    recorder.write_provider_result(session_id, first_result)
    recorder.write_search_results(session_id, first_provider.name, first_result.results)
    
    if on_provider_complete:
        on_provider_complete(first_result)
    
    # 后台线程执行剩余供应商
    background_thread = None
    if remaining_providers:
        # D-01: daemon=False
        background_thread = threading.Thread(
            target=self._execute_background_providers,
            args=(remaining_providers, request, recorder, session_id, on_provider_complete),
            daemon=False  # 关键修改
        )
        background_thread.start()
    
    # D-01: 等待后台线程完成 (timeout=10)
    if background_thread:
        background_thread.join(timeout=10)
        if background_thread.is_alive():
            logger.warning(f"Background thread still alive after 10s timeout, proceeding anyway")
    
    # COMP-06: 返回包含 session_id 的结果
    unified_result = self._convert_to_unified_result(first_result)
    unified_result.session_id = session_id  # 新增字段
    
    return unified_result

def _execute_background_providers(
    self,
    providers: List[BaseProvider],
    request: ProviderSearchRequest,
    recorder: ComparisonRecorder,
    session_id: str,
    on_provider_complete: Optional[Callable[[ProviderSearchResult], None]] = None
) -> None:
    """后台执行剩余供应商
    
    D-02: 每个供应商完成后立即写入
    D-04: 失败时日志记录继续
    """
    for provider in providers:
        try:
            result = provider.search(request)
            
            # D-02: 立即写入
            recorder.write_provider_result(session_id, result)
            recorder.write_search_results(session_id, provider.name, result.results)
            
            if on_provider_complete:
                on_provider_complete(result)
            
            logger.info(f"[Comparison] Background {provider.name}: {result.response_time_ms}ms")
        except Exception as e:
            logger.error(f"[Comparison] Background {provider.name} exception: {e}")
            # D-04: 继续执行下一个供应商
```

### Pattern 3: UnifiedSearchResult 扩展

**What:** 添加 session_id 字段用于追溯

**Example:**
```python
# Source: [设计基于 COMP-06]
# melodyi_search/domain/models/search_result.py 修改

class UnifiedSearchResult(BaseModel):
    """统一搜索结果，暴露给 Agent/CLI"""
    
    provider: str = Field(..., description="响应的提供商")
    response_time_ms: int = Field(..., ge=0, description="响应时间(毫秒)")
    results: List[SearchResultItem] = Field(default_factory=list, description="搜索结果列表")
    comparison_log: Optional[dict] = Field(default=None, description="比对模式内部数据")
    error: Optional[SearchError] = Field(default=None, description="错误及指导")
    session_id: Optional[str] = Field(default=None, description="对比会话 ID (COMP-06)")  # 新增
```

### Anti-Patterns to Avoid

- **Anti-pattern: 在 CLI 入口等待后台线程**
  - Why bad: CLI 应快速返回结果，等待应在 execute_comparison() 内部完成
  - Alternative: 在 ExecutionStrategy 内部处理等待逻辑

- **Anti-pattern: 批量写入所有供应商结果**
  - Why bad: 增加事务复杂度，一个失败可能影响全部
  - Alternative: D-02 每个供应商完成后立即写入（单条 autocommit）

- **Anti-pattern: 持久化失败时抛出异常**
  - Why bad: 阻塞主流程，违反"优先保障主体功能可用"约束
  - Alternative: D-04 日志记录后继续执行

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session ID 生成 | 自定义 UUID 或 hash | 时间戳 + 随机数 (D-03) | 可读性强，便于追溯 |
| 线程等待逻辑 | signal 或 asyncio | threading.Thread.join(timeout) | 简单可靠，兼容现有代码 |
| 数据库连接池 | 自定义池化 | sqlite3 原生连接 | SQLite 轻量级场景无需池化 |

**Key insight:** 现有 threading 模块足够满足需求，无需引入 asyncio 改造。Phase 1 的 DatabaseManager 已实现连接管理，直接调用即可。

## Common Pitfalls

### Pitfall 1: Daemon Thread 数据丢失

**What goes wrong:** 使用 `daemon=True` 时，进程退出可能杀死未完成的后台线程，导致数据未写入数据库

**Why it happens:** Python daemon 线程在主线程结束时会被强制终止，不保证执行完成

**How to avoid:**
1. 设置 `daemon=False`（CONTEXT.md D-01）
2. 调用 `thread.join(timeout=10)` 等待完成
3. 超时后记录 WARNING 日志继续退出

**Warning signs:**
- 数据库中部分供应商结果缺失
- 后台供应商日志不完整
- 进程退出过快（< 1 秒）

### Pitfall 2: 持久化阻塞主流程

**What goes wrong:** 数据写入耗时过长或失败抛出异常，导致 CLI 返回延迟或失败

**Why it happens:** 未遵循"优先保障主体功能可用"约束

**How to avoid:**
1. 写入操作捕获所有异常（CONTEXT.md D-04）
2. 记录 ERROR 日志后继续执行
3. 设置合理的 timeout（10 秒）

**Warning signs:**
- CLI 响应时间 > 15 秒
- 用户看到持久化错误而非搜索结果

### Pitfall 3: Session ID 不唯一

**What goes wrong:** 高并发时 Session ID 可能重复（纯随机数或纯时间戳）

**Why it happens:** 时间戳精度不够或随机数范围太小

**How to avoid:**
1. 使用秒级时间戳 + 4 位十六进制随机数（CONTEXT.md D-03）
2. 单进程单线程场景足够（CLI 工具非高并发）

**Warning signs:**
- 数据库 session_id 主键冲突
- 历史查询返回多条记录

### Pitfall 4: Rank 字段缺失或错误

**What goes wrong:** 搜索结果未记录排序位置，后续相关性分析无法进行

**Why it happens:** 结果写入时忽略 rank 字段

**How to avoid:**
1. 使用 `enumerate(results, start=1)` 生成 rank（COMP-04）
2. 每个供应商的结果独立排序
3. 测试验证 rank 字段写入正确

**Warning signs:**
- search_results 表 rank 字段为空或全为 0
- Phase 4 分析报告相关性数据缺失

## Code Examples

Verified patterns from existing code:

### DatabaseManager 写入模式（Phase 1 已验证）

```python
# Source: [VERIFIED: tests/infrastructure/database/test_database_manager.py]
# 单条插入 autocommit 模式

conn = manager.get_connection()
conn.execute(
    "INSERT INTO comparison_sessions (session_id, query, params, timestamp) VALUES (?, ?, ?, ?)",
    ("test-session-1", "test query", "{}", 1700000000.0)
)
conn.commit()
conn.close()
```

### threading.Thread 非 daemon 模式

```python
# Source: [CITED: Python threading docs]
# daemon=False 确保线程完成

import threading

def background_task():
    # 执行后台任务
    pass

thread = threading.Thread(target=background_task, daemon=False)
thread.start()
thread.join(timeout=10)  # 等待最多 10 秒
if thread.is_alive():
    # 超时处理
    pass
```

### ProviderSearchRequest 参数提取

```python
# Source: [VERIFIED: melodyi_search/providers/base_provider.py]
# COMP-03 需记录的参数

request = ProviderSearchRequest(
    query="test",
    max_results=10,
    time_range=TimeRange(range_type="week"),
    include_domains=["example.com"],
    exclude_domains=None,
    language="zh"
)

# 序列化为 JSON 存储
params_json = json.dumps({
    "max_results": request.max_results,
    "time_range": request.time_range.range_type if request.time_range else None,
    "include_domains": request.include_domains,
    "exclude_domains": request.exclude_domains,
    "language": request.language
})
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| daemon=True 后台线程 | daemon=False + join(timeout) | Phase 2 (D-01) | 确保数据写入完成 |
| 内存存储对比结果 | SQLite 持久化 | Phase 2 (COMP-02) | 支持历史查询和分析 |
| 仅元数据记录 | 完整结果记录 | Phase 2 (COMP-01) | 支持相关性分析 |
| 无 session_id | 时间戳+随机数 session_id | Phase 2 (COMP-06) | 可追溯对比记录 |

**Deprecated/outdated:**
- `daemon=True`: 已确认导致数据丢失，必须改为 daemon=False
- `_comparison_results` 内存字典: 仅用于临时日志，数据应写入数据库

## Assumptions Log

> 所有核心技术决策均已在 CONTEXT.md 中锁定，以下为实现细节假设：

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pydantic V2 版本为 2.x | Standard Stack | 低风险 - 现有代码已验证兼容 |
| A2 | 单进程 CLI 无需考虑 session_id 高并发冲突 | Pattern 3 | 低风险 - CLI 工具非高并发场景 |
| A3 | SQLite 3.41.2 支持 JSON 存储 | Pattern 1 | 低风险 - params 字段使用 TEXT + json.dumps |

**如果此表为空:** 所有核心决策已由 CONTEXT.md 锁定，实现细节假设均为低风险。

## Open Questions

1. **DatabaseManager 是否需要添加写入方法？**
   - What we know: Phase 1 仅实现 init_database() 和 get_connection()
   - What's unclear: 是否应在 DatabaseManager 中封装写入方法，或在 ComparisonRecorder 直接使用连接
   - Recommendation: ComparisonRecorder 直接使用 get_connection()，保持 DatabaseManager 职责单一

2. **ComparisonRecorder 是否需要批量写入方法？**
   - What we know: D-02 决策为单条写入
   - What's unclear: search_results 是否需要批量插入优化
   - Recommendation: Phase 2 使用单条插入，Phase v2 的 PERF-01 可引入批量优化

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | 运行环境 | Yes | 3.11.5 | - |
| SQLite | 数据持久化 | Yes | 3.41.2 | - |
| pytest | 测试框架 | Yes | 9.0.2 | - |
| threading | 后台执行 | Yes | stdlib | - |
| json | 参数序列化 | Yes | stdlib | - |

**Missing dependencies with no fallback:**
- None - 所有依赖均已满足

**Missing dependencies with fallback:**
- None - 无需外部服务

## Validation Architecture

> workflow.nyquist_validation: true (from config.json)

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None - pytest 自动发现 |
| Quick run command | `pytest tests/domain/services/test_comparison_recorder.py -x` |
| Full suite command | `pytest tests/domain/services/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-01 | 记录完整搜索结果 | unit | `pytest tests/domain/services/test_comparison_recorder.py::TestWriteSearchResults -x` | Wave 0 新建 |
| COMP-02 | 持久化到 SQLite | integration | `pytest tests/domain/services/test_execution_strategy.py::TestComparisonPersistence -x` | Wave 0 新建 |
| COMP-03 | 记录请求参数 | unit | `pytest tests/domain/services/test_comparison_recorder.py::TestWriteSession -x` | Wave 0 新建 |
| COMP-04 | 记录排序位置 | unit | `pytest tests/domain/services/test_comparison_recorder.py::TestWriteSearchResults::test_rank_correct -x` | Wave 0 新建 |
| COMP-05 | 记录元数据指标 | unit | `pytest tests/domain/services/test_comparison_recorder.py::TestWriteProviderResult -x` | Wave 0 新建 |
| COMP-06 | 返回 session_id | unit | `pytest tests/domain/services/test_execution_strategy.py::TestComparisonSessionId -x` | Wave 0 修改 |
| COMP-07 | 修复 daemon thread | integration | `pytest tests/domain/services/test_execution_strategy.py::TestBackgroundThreadWait -x` | Wave 0 修改 |

### Sampling Rate
- **Per task commit:** `pytest tests/domain/services/test_comparison_recorder.py -x`
- **Per wave merge:** `pytest tests/domain/services/ -v`
- **Phase gate:** `pytest tests/ -v --tb=short` 全量通过

### Wave 0 Gaps
- [ ] `tests/domain/services/test_comparison_recorder.py` — covers COMP-01, COMP-03, COMP-04, COMP-05
- [ ] `tests/domain/services/test_execution_strategy.py` 修改 — 添加 COMP-02, COMP-06, COMP-07 测试
- [ ] `melodyi_search/domain/services/comparison_recorder.py` — 新建 recorder 服务
- [ ] `melodyi_search/domain/models/search_result.py` 修改 — 添加 session_id 字段

*(Wave 0 需创建 1 个新测试文件，修改 2 个现有测试文件)*

## Security Domain

> 此 Phase 无安全敏感操作（数据写入为本地 SQLite，无外部暴露）

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | CLI 单用户工具，无需认证 |
| V3 Session Management | No | 无用户会话概念 |
| V4 Access Control | No | 单用户本地工具 |
| V5 Input Validation | Yes | Pydantic 模型验证 request 参数 |
| V6 Cryptography | No | 无加密需求 |

### Known Threat Patterns for SQLite + Python

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL Injection | Tampering | 参数化查询（已使用） |
| 数据文件泄露 | Information Disclosure | 默认路径 ./data/，用户控制 |
| 日志敏感信息 | Information Disclosure | 不记录 API 密钥，仅记录 session_id |

## Sources

### Primary (HIGH confidence)
- CONTEXT.md D-01~04 - 用户锁定决策
- melodyi_search/domain/services/execution_strategy.py - 现有实现分析
- melodyi_search/infrastructure/database/database_manager.py - Phase 1 实现
- tests/domain/services/test_execution_strategy.py - 现有测试模式
- tests/infrastructure/database/test_database_manager.py - Phase 1 测试模式

### Secondary (MEDIUM confidence)
- Python threading 官方文档 - daemon 和 join 行为
- SQLite 官方文档 - 参数化查询

### Tertiary (LOW confidence)
- None - 所有核心技术点已通过代码分析确认

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python/SQLite/pytest 版本已验证
- Architecture: HIGH - D-01~04 决策已锁定，现有代码已分析
- Pitfalls: HIGH - daemon thread 问题已确认，解决方案已锁定

**Research date:** 2026-05-09
**Valid until:** 30 天 - SQLite 和 threading 为稳定技术