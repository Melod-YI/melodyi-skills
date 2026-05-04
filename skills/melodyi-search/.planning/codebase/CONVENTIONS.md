# CONVENTIONS.md

**Last mapped:** 2026-05-04

## 代码风格

### Python 版本

- 目标: Python >=3.10
- 使用现代特性: `typing.Optional`, `typing.Literal`, `@field_validator`

### 类型注解

全面使用类型注解：

```python
from typing import List, Optional, Literal

def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
    ...
```

### 数据模型

使用 **Pydantic V2** 进行数据验证：

```python
from pydantic import BaseModel, Field, field_validator, model_validator

class UnifiedSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="搜索查询，必填")
    max_results: int = Field(default=10, ge=1, description="期望最大结果数")
```

### 导入顺序

标准导入顺序：

```python
# 1. 标准库
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Literal

# 2. 第三方库
from pydantic import BaseModel, Field
import click

# 3. 项目内部模块
from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.providers.base_provider import BaseProvider
```

## 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 类名 | PascalCase | `UnifiedSearchRequest`, `ProviderFactory` |
| 函数名 | snake_case | `load_config`, `create_error_with_guidance` |
| 方法名 | snake_case | `execute_normal`, `supports_time_filter` |
| 变量名 | snake_case | `provider_name`, `error_msg` |
| 常量 | UPPER_SNAKE_CASE | `ERROR_GUIDANCE`, `_PROVIDER_MAP` |
| 私有成员 | 前缀 `_` | `_comparison_results`, `_create_error_result` |

### 枚举命名

```python
class ErrorType(str, Enum):
    API_KEY_INVALID = "API_KEY_INVALID"
    RATE_LIMITED = "RATE_LIMITED"
    ...
```

## 文档字符串

使用中文文档字符串：

```python
"""统一搜索请求模型"""

def execute_normal(self, providers: List[BaseProvider], ...):
    """正常模式执行

    按顺序串行执行提供商，成功则立即返回，失败则回退到下一个提供商。

    Args:
        providers: 提供商列表
        request: 统一的搜索请求

    Returns:
        统一的搜索结果
    """
```

## 错误处理

### 带指导的错误

所有错误使用 `SearchError` 模型，包含 Agent 指导：

```python
error = SearchError(
    error_type="RATE_LIMITED",
    original_message="Too many requests",
    guidance="请求被此提供商限流。操作：请等待后重试，或系统将自动切换到另一个提供商。"
)
```

### 错误类型枚举

定义于 `melodyi_search/domain/models/error.py`：

| 类型 | 常量 | 指导内容 |
|------|------|----------|
| API Key 无效 | `API_KEY_INVALID` | 检查配置 |
| 限流 | `RATE_LIMITED` | 等待重试 |
| 配额耗尽 | `QUOTA_EXCEEDED` | 切换提供商 |
| 网络错误 | `NETWORK_ERROR` | 检查连接 |
| 超时 | `TIMEOUT` | 重试/切换 |

## 日志规范

### 日志级别

| 级别 | 用途 |
|------|------|
| DEBUG | 提供商开始/结束、后台执行 |
| INFO | 成功结果、请求参数 |
| WARNING | 提供商失败（预期内） |
| ERROR | 异常、非预期错误 |

### 日志格式

```
[2026-05-04 09:08:12] INFO | Query: "Python教程" | Params: max_results=10
[2026-05-04 09:08:12] DEBUG | Provider: tavily | Start
[2026-05-04 09:08:12] INFO | Provider: tavily | Status: success | Time: 234ms | Results: 10
```

### 关键位置日志

- 方法入口: `logger.debug(f"[Mode] Trying provider: {provider_name}")`
- 成功返回: `logger.info(f"[Mode] Provider {provider_name} succeeded")`
- 失败记录: `logger.warning(f"[Mode] Provider {provider_name} failed: {error}")`
- 异常捕获: `logger.error(f"[Mode] Provider {provider_name} raised exception: {error_msg}")`

## 设计模式

| 模式 | 使用位置 |
|------|----------|
| 抽象工厂 | `ProviderFactory` |
| 策略模式 | `ExecutionStrategy` |
| 适配器模式 | `ParameterAdapter` |
| 模板方法 | `BaseProvider` 抽象类 |

---

*Mapped by sequential codebase analysis on 2026-05-04*