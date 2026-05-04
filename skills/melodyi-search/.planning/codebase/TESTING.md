# TESTING.md

**Last mapped:** 2026-05-04

## 测试框架

| 框架 | 版本 | 用途 |
|------|------|------|
| pytest | >=7.0 | 主测试框架 |
| pytest-asyncio | >=0.21 | 异步测试支持 |

### pytest 配置

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## 测试结构

测试目录镜像源码结构：

```
tests/
├── application/        → melodyi_search/application/
│   └ test_cli.py
├── domain/
│   ├── models/         → melodyi_search/domain/models/
│   │   ├── test_search_request.py
│   │   ├── test_search_result.py
│   │   ├── test_provider_config.py
│   │   ├── test_error.py
│   │   ├── services/         → melodyi_search/domain/services/
│   │   ├── test_provider_factory.py
│   │   ├── test_parameter_adapter.py
│   │   ├── test_execution_strategy.py
│   │
├── infrastructure/
│   ├── config/         → melodyi_search/infrastructure/config/
│   │   ├── test_config_schema.py
│   │   ├── test_config_loader.py
│   ├── http/           → melodyi_search/infrastructure/http/
│   │   ├── test_http_client.py
│   ├── logging/        → melodyi_search/infrastructure/logging/
│   │   ├── test_search_logger.py
│   │
├── providers/          → melodyi_search/providers/
│   ├── test_base_provider.py
│   ├── test_tavily_provider.py
│   ├── test_exa_provider.py
│   ├── test_searxng_provider.py
│   ├── test_firecrawl_provider.py
│   ├── test_minimax_cn_provider.py
│   ├── test_brave_provider.py
│   │
├── integration/        # E2E 集成测试
│   ├── test_tavily_e2e.py
│   ├── test_exa_e2e.py
│   ├── test_brave_e2e.py
│   ├── test_minimax_cn_e2e.py
```

## 测试分类

### 1. 单元测试

测试单个类/函数，位于 `tests/` 镜像目录。

命名约定: `test_{module_name}.py`

### 2. 集成测试

测试真实 API 调用，位于 `tests/integration/`。

命名约定: `test_{provider}_e2e.py`

需要真实 API Key 执行：

```bash
pytest tests/integration/test_tavily_e2e.py -v
```

## 测试模式

### Pydantic 模型测试

验证字段约束：

```python
def test_query_not_empty():
    """验证 query 不能为空"""
    with pytest.raises(ValueError):
        UnifiedSearchRequest(query="")
```

### Mock 使用

使用 `unittest.mock` 或 pytest fixtures：

```python
from unittest.mock import Mock, patch

def test_provider_search():
    provider = Mock(spec=BaseProvider)
    provider.name = "test"
    provider.search.return_value = ProviderSearchResult(...)
```

### 异步测试

`pytest-asyncio` 自动处理：

```python
@pytest.mark.asyncio
async def test_async_search():
    result = await async_provider.search(request)
    assert result.error is None
```

## 覆盖率

运行覆盖率测试：

```bash
pytest --cov=melodyi_search --cov-report=html
```

## 测试命令

| 命令 | 用途 |
|------|------|
| `pytest` | 运行所有测试 |
| `pytest tests/domain/` | 运行领域层测试 |
| `pytest tests/integration/` | 运行集成测试 |
| `pytest -v` | 详细输出 |
| `pytest -k "search"` | 按名称过滤 |

## 断言风格

使用标准 pytest 断言：

```python
assert result.error is None
assert len(result.results) > 0
assert result.response_time_ms < 1000
```

---

*Mapped by sequential codebase analysis on 2026-05-04*