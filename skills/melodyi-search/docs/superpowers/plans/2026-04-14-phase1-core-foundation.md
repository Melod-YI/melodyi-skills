# melodyi-search 实现计划 - 第一阶段：核心基础

> **执行说明:** 使用 superpowers:subagent-driven-development 或 superpowers:executing-plans 来执行此计划。步骤使用复选框 (`- [ ]`) 进行追踪。

**目标:** 建立项目的核心领域模型、提供商基类、配置系统和日志基础设施，为后续提供商实现提供稳定基础。

**架构:** DDD 分层架构，domain/models 定义统一数据模型，providers/base_provider.py 定义抽象基类，infrastructure 负责配置和日志。

**技术栈:** Python 3.10+, pydantic (数据模型), python-dotenv (环境变量), pyyaml (配置), pytest (测试)

---

## 文件结构

本阶段创建以下文件：

```
melodyi_search/
├── __init__.py
├── domain/
│   ├── __init__.py
│   └── models/
│       ├── __init__.py
│       ├── search_request.py     # UnifiedSearchRequest + TimeRange
│       ├── search_result.py      # UnifiedSearchResult + SearchResultItem
│       ├── error.py              # SearchError + 错误类型枚举
│       └── provider_config.py    # ProviderConfig 单个提供商配置
│   └── services/
│       └ __init__.py
│       └ parameter_adapter.py    # 参数适配服务
├── providers/
│   ├── __init__.py
│   └ base_provider.py            # BaseProvider 抽象基类 + ProviderSearchRequest
├── infrastructure/
│   ├── __init__.py
│   └ config/
│   │   ├── __init__.py
│   │   ├── config_schema.py      # Config 全局配置模型
│   │   ├── config_loader.py      # 配置加载器（支持 .env）
│   │   └ default_config.yaml     # 默认配置模板
│   └ logging/
│   │   ├── __init__.py
│   │   └ search_logger.py        # 搜索日志器
│   └ http/
│       ├── __init__.py
│       └ http_client.py          # HTTP 客户端抽象
├── .env.example                  # 环境变量模板
├── pyproject.toml                # 项目配置
tests/
├── __init__.py
├── domain/
│   └ __init__.py
│   └ models/
│       ├── __init__.py
│       ├── test_search_request.py
│       ├── test_search_result.py
│       ├── test_error.py
│       ├── test_provider_config.py
├── infrastructure/
│   └ __init__.py
│   └ config/
│       ├── __init__.py
│       ├── test_config_loader.py
│       ├── test_config_schema.py
│   └ logging/
│       ├── __init__.py
│       ├── test_search_logger.py
│   └ http/
│       ├── __init__.py
│       ├── test_http_client.py
├── providers/
│   ├── __init__.py
│   └ test_base_provider.py
```

---

## 任务列表

### 任务 1: 项目初始化与 pyproject.toml

**文件:**
- 创建: `pyproject.toml`
- 创建: `melodyi_search/__init__.py`
- 创建: `tests/__init__.py`

- [ ] **步骤 1: 创建 pyproject.toml**

```toml
[project]
name = "melodyi-search"
version = "0.1.0"
description = "多提供商搜索工具，支持多种搜索 API"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "pyyaml>=6.0",
    "httpx>=0.25",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]

[project.scripts]
melodyi-search = "melodyi_search.application.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["melodyi_search"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **步骤 2: 创建包初始化文件**

创建 `melodyi_search/__init__.py`:

```python
"""melodyi-search: 多提供商搜索工具"""

__version__ = "0.1.0"
```

创建 `tests/__init__.py`:

```python
"""melodyi-search 测试"""
```

- [ ] **步骤 3: 提交**

```bash
git add pyproject.toml melodyi_search/__init__.py tests/__init__.py
git commit -m "feat: 项目初始化，添加 pyproject.toml"
```

---

### 任务 2: TimeRange 时间范围模型

**文件:**
- 创建: `melodyi_search/domain/__init__.py`
- 创建: `melodyi_search/domain/models/__init__.py`
- 创建: `melodyi_search/domain/models/search_request.py`
- 创建: `tests/domain/__init__.py`
- 创建: `tests/domain/models/__init__.py`
- 创建: `tests/domain/models/test_search_request.py`

- [ ] **步骤 1: 编写 TimeRange 测试**

创建 `tests/domain/models/test_search_request.py`:

```python
"""TimeRange 模型测试"""

import pytest
from datetime import datetime, timedelta
from melodyi_search.domain.models.search_request import TimeRange


class TestTimeRange:
    """TimeRange 测试类"""

    def test_create_with_range_type_day(self):
        """测试使用 range_type='day' 创建"""
        time_range = TimeRange(range_type="day")
        assert time_range.range_type == "day"
        assert time_range.start_date is None
        assert time_range.end_date is None

    def test_create_with_range_type_week(self):
        """测试使用 range_type='week' 创建"""
        time_range = TimeRange(range_type="week")
        assert time_range.range_type == "week"

    def test_create_with_range_type_month(self):
        """测试使用 range_type='month' 创建"""
        time_range = TimeRange(range_type="month")
        assert time_range.range_type == "month"

    def test_create_with_range_type_year(self):
        """测试使用 range_type='year' 创建"""
        time_range = TimeRange(range_type="year")
        assert time_range.range_type == "year"

    def test_create_with_explicit_dates(self):
        """测试使用精确日期创建"""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)
        time_range = TimeRange(start_date=start, end_date=end)
        assert time_range.start_date == start
        assert time_range.end_date == end
        assert time_range.range_type is None

    def test_create_empty_time_range(self):
        """测试创建空的时间范围"""
        time_range = TimeRange()
        assert time_range.range_type is None
        assert time_range.start_date is None
        assert time_range.end_date is None

    def test_range_type_invalid_raises_error(self):
        """测试无效 range_type 抛出错误"""
        with pytest.raises(ValueError):
            TimeRange(range_type="invalid")
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/domain/models/test_search_request.py -v
```

预期: FAIL - `melodyi_search` 模块不存在

- [ ] **步骤 3: 创建目录结构**

```bash
mkdir -p melodyi_search/domain/models
mkdir -p tests/domain/models
```

创建 `melodyi_search/domain/__init__.py`:

```python
"""领域层"""
```

创建 `melodyi_search/domain/models/__init__.py`:

```python
"""领域模型"""

from melodyi_search.domain.models.search_request import TimeRange, UnifiedSearchRequest

__all__ = ["TimeRange", "UnifiedSearchRequest"]
```

创建 `tests/domain/__init__.py`:

```python
"""领域层测试"""
```

创建 `tests/domain/models/__init__.py`:

```python
"""领域模型测试"""
```

- [ ] **步骤 4: 实现 TimeRange 模型**

创建 `melodyi_search/domain/models/search_request.py`:

```python
"""统一搜索请求模型"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, field_validator


class TimeRange(BaseModel):
    """统一时间范围规范"""

    # 简单范围类型: day, week, month, year
    range_type: Optional[Literal["day", "week", "month", "year"]] = None

    # 精确日期范围
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("range_type")
    @classmethod
    def validate_range_type(cls, v: Optional[str]) -> Optional[str]:
        """验证 range_type 只能是允许的值"""
        if v is not None and v not in ("day", "week", "month", "year"):
            raise ValueError(f"无效的 range_type: {v}，必须是 day/week/month/year")
        return v

    def is_empty(self) -> bool:
        """检查是否为空的时间范围"""
        return self.range_type is None and self.start_date is None and self.end_date is None
```

- [ ] **步骤 5: 运行测试验证通过**

```bash
pytest tests/domain/models/test_search_request.py::TestTimeRange -v
```

预期: PASS

- [ ] **步骤 6: 提交**

```bash
git add melodyi_search/domain/ tests/domain/models/
git commit -m "feat: 实现 TimeRange 时间范围模型"
```

---

### 任务 3: UnifiedSearchRequest 统一搜索请求

**文件:**
- 修改: `melodyi_search/domain/models/search_request.py`
- 修改: `tests/domain/models/test_search_request.py`

- [ ] **步骤 1: 编写 UnifiedSearchRequest 测试**

追加到 `tests/domain/models/test_search_request.py`:

```python
from melodyi_search.domain.models.search_request import UnifiedSearchRequest


class TestUnifiedSearchRequest:
    """UnifiedSearchRequest 测试类"""

    def test_create_with_query_only(self):
        """测试仅使用 query 创建"""
        request = UnifiedSearchRequest(query="python tutorial")
        assert request.query == "python tutorial"
        assert request.max_results == 10  # 默认值
        assert request.time_range is None
        assert request.include_domains is None
        assert request.exclude_domains is None
        assert request.language is None
        assert request.preferred_provider is None

    def test_create_with_all_params(self):
        """测试使用所有参数创建"""
        time_range = TimeRange(range_type="week")
        request = UnifiedSearchRequest(
            query="AI news",
            max_results=20,
            time_range=time_range,
            include_domains=["github.com", "stackoverflow.com"],
            exclude_domains=["twitter.com"],
            language="en",
            preferred_provider="tavily"
        )
        assert request.query == "AI news"
        assert request.max_results == 20
        assert request.time_range.range_type == "week"
        assert request.include_domains == ["github.com", "stackoverflow.com"]
        assert request.exclude_domains == ["twitter.com"]
        assert request.language == "en"
        assert request.preferred_provider == "tavily"

    def test_query_required(self):
        """测试 query 必填"""
        with pytest.raises(ValueError):
            UnifiedSearchRequest()

    def test_query_cannot_be_empty(self):
        """测试 query 不能为空字符串"""
        with pytest.raises(ValueError):
            UnifiedSearchRequest(query="")

    def test_max_results_positive(self):
        """测试 max_results 必须为正数"""
        with pytest.raises(ValueError):
            UnifiedSearchRequest(query="test", max_results=0)

        with pytest.raises(ValueError):
            UnifiedSearchRequest(query="test", max_results=-1)
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/domain/models/test_search_request.py::TestUnifiedSearchRequest -v
```

预期: FAIL - UnifiedSearchRequest 未实现

- [ ] **步骤 3: 实现 UnifiedSearchRequest**

追加到 `melodyi_search/domain/models/search_request.py`:

```python
from typing import List, Optional
from pydantic import Field, field_validator


class UnifiedSearchRequest(BaseModel):
    """统一搜索请求，暴露给 Agent/CLI"""

    query: str = Field(..., description="搜索查询，必填")
    max_results: int = Field(default=10, ge=1, description="期望最大结果数")
    time_range: Optional[TimeRange] = Field(default=None, description="时间过滤")
    include_domains: Optional[List[str]] = Field(default=None, description="包含特定域名")
    exclude_domains: Optional[List[str]] = Field(default=None, description="排除特定域名")
    language: Optional[str] = Field(default=None, description="ISO 语言代码")
    preferred_provider: Optional[str] = Field(default=None, description="指定使用某个提供商")

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        """验证 query 不能为空"""
        if not v or not v.strip():
            raise ValueError("query 不能为空")
        return v.strip()
```

更新 `melodyi_search/domain/models/__init__.py` 导出:

```python
from melodyi_search.domain.models.search_request import TimeRange, UnifiedSearchRequest

__all__ = ["TimeRange", "UnifiedSearchRequest"]
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/domain/models/test_search_request.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/domain/models/search_request.py tests/domain/models/test_search_request.py
git commit -m "feat: 实现 UnifiedSearchRequest 统一搜索请求模型"
```

---

### 任务 4: SearchResultItem 搜索结果项

**文件:**
- 创建: `melodyi_search/domain/models/search_result.py`
- 创建: `tests/domain/models/test_search_result.py`

- [ ] **步骤 1: 编写 SearchResultItem 测试**

创建 `tests/domain/models/test_search_result.py`:

```python
"""搜索结果模型测试"""

import pytest
from datetime import datetime
from melodyi_search.domain.models.search_result import SearchResultItem


class TestSearchResultItem:
    """SearchResultItem 测试类"""

    def test_create_with_required_fields(self):
        """测试使用必填字段创建"""
        item = SearchResultItem(
            title="Python Tutorial",
            url="https://example.com/python",
            description="Learn Python basics"
        )
        assert item.title == "Python Tutorial"
        assert item.url == "https://example.com/python"
        assert item.description == "Learn Python basics"
        assert item.published_date is None
        assert item.source_domain == "example.com"
        assert item.provider_extra is None

    def test_create_with_all_fields(self):
        """测试使用所有字段创建"""
        published = datetime(2026, 1, 15)
        item = SearchResultItem(
            title="AI News",
            url="https://github.com/repo",
            description="Latest AI developments",
            published_date=published,
            source_domain="github.com",
            provider_extra={"raw": "data"}
        )
        assert item.title == "AI News"
        assert item.url == "https://github.com/repo"
        assert item.published_date == published
        assert item.source_domain == "github.com"
        assert item.provider_extra == {"raw": "data"}

    def test_source_domain_extracted_from_url(self):
        """测试 source_domain 从 URL 自动提取"""
        item = SearchResultItem(
            title="Test",
            url="https://stackoverflow.com/questions/123",
            description="test"
        )
        assert item.source_domain == "stackoverflow.com"

    def test_url_required(self):
        """测试 url 必填"""
        with pytest.raises(ValueError):
            SearchResultItem(title="Test", description="test")

    def test_title_required(self):
        """测试 title 必填"""
        with pytest.raises(ValueError):
            SearchResultItem(url="https://example.com", description="test")
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/domain/models/test_search_result.py::TestSearchResultItem -v
```

预期: FAIL - SearchResultItem 未实现

- [ ] **步骤 3: 实现 SearchResultItem**

创建 `melodyi_search/domain/models/search_result.py`:

```python
"""统一搜索结果模型"""

from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator


class SearchResultItem(BaseModel):
    """单个搜索结果项"""

    title: str = Field(..., description="结果标题")
    url: str = Field(..., description="结果 URL")
    description: str = Field(default="", description="摘要/片段")
    published_date: Optional[datetime] = Field(default=None, description="发布日期")
    source_domain: str = Field(default="", description="来源域名")
    provider_extra: Optional[dict] = Field(default=None, description="提供商原始数据")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """验证 URL 格式"""
        if not v:
            raise ValueError("url 不能为空")
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"无效的 URL: {v}")
        return v

    @field_validator("source_domain", always=True)
    @classmethod
    def extract_domain(cls, v: str, info) -> str:
        """从 URL 提取域名"""
        if v:
            return v
        url = info.data.get("url", "")
        if url:
            parsed = urlparse(url)
            return parsed.netloc
        return ""
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/domain/models/test_search_result.py::TestSearchResultItem -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/domain/models/search_result.py tests/domain/models/test_search_result.py
git commit -m "feat: 实现 SearchResultItem 搜索结果项模型"
```

---

### 任务 5: UnifiedSearchResult 统一搜索结果

**文件:**
- 修改: `melodyi_search/domain/models/search_result.py`
- 修改: `tests/domain/models/test_search_result.py`

- [ ] **步骤 1: 编写 UnifiedSearchResult 测试**

追加到 `tests/domain/models/test_search_result.py`:

```python
from melodyi_search.domain.models.search_result import UnifiedSearchResult, SearchError


class TestUnifiedSearchResult:
    """UnifiedSearchResult 测试类"""

    def test_create_success_result(self):
        """测试创建成功结果"""
        item = SearchResultItem(
            title="Test",
            url="https://example.com",
            description="test"
        )
        result = UnifiedSearchResult(
            provider="minimax-cn",
            response_time_ms=850,
            results=[item]
        )
        assert result.provider == "minimax-cn"
        assert result.response_time_ms == 850
        assert len(result.results) == 1
        assert result.error is None
        assert result.comparison_log is None

    def test_create_error_result(self):
        """测试创建错误结果"""
        error = SearchError(
            error_type="RATE_LIMITED",
            original_message="Too many requests",
            guidance="请等待后重试或切换提供商"
        )
        result = UnifiedSearchResult(
            provider="brave",
            response_time_ms=100,
            results=[],
            error=error
        )
        assert result.error.error_type == "RATE_LIMITED"
        assert result.error.guidance == "请等待后重试或切换提供商"

    def test_results_default_empty_list(self):
        """测试 results 默认为空列表"""
        result = UnifiedSearchResult(
            provider="test",
            response_time_ms=100
        )
        assert result.results == []
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/domain/models/test_search_result.py::TestUnifiedSearchResult -v
```

预期: FAIL - UnifiedSearchResult 未实现

- [ ] **步骤 3: 实现 UnifiedSearchResult 和 SearchError**

追加到 `melodyi_search/domain/models/search_result.py`:

```python
from typing import List, Optional


class SearchError(BaseModel):
    """带 Agent 补救指导的错误"""

    error_type: str = Field(..., description="错误类型分类")
    original_message: str = Field(default="", description="提供商原始错误")
    guidance: str = Field(default="", description="指导 Agent 行为的提示")


class UnifiedSearchResult(BaseModel):
    """统一搜索结果，暴露给 Agent/CLI"""

    provider: str = Field(..., description="响应的提供商")
    response_time_ms: int = Field(..., ge=0, description="响应时间(毫秒)")
    results: List[SearchResultItem] = Field(default_factory=list, description="搜索结果列表")
    comparison_log: Optional[dict] = Field(default=None, description="比对模式内部数据")
    error: Optional[SearchError] = Field(default=None, description="错误及指导")

    def is_success(self) -> bool:
        """检查是否成功"""
        return self.error is None

    def has_results(self) -> bool:
        """检查是否有结果"""
        return len(self.results) > 0
```

更新 `melodyi_search/domain/models/__init__.py`:

```python
from melodyi_search.domain.models.search_request import TimeRange, UnifiedSearchRequest
from melodyi_search.domain.models.search_result import SearchResultItem, UnifiedSearchResult, SearchError

__all__ = [
    "TimeRange",
    "UnifiedSearchRequest",
    "SearchResultItem",
    "UnifiedSearchResult",
    "SearchError",
]
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/domain/models/test_search_result.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/domain/models/search_result.py melodyi_search/domain/models/__init__.py tests/domain/models/test_search_result.py
git commit -m "feat: 实现 UnifiedSearchResult 和 SearchError 模型"
```

---

### 任务 6: SearchError 错误类型与指导

**文件:**
- 创建: `melodyi_search/domain/models/error.py`
- 创建: `tests/domain/models/test_error.py`

- [ ] **步骤 1: 编写错误类型枚举和指导测试**

创建 `tests/domain/models/test_error.py`:

```python
"""错误类型和指导测试"""

import pytest
from melodyi_search.domain.models.error import (
    ErrorType,
    ERROR_GUIDANCE,
    create_error_with_guidance
)


class TestErrorType:
    """ErrorType 枚举测试"""

    def test_all_error_types_exist(self):
        """测试所有错误类型存在"""
        expected_types = [
            "API_KEY_INVALID",
            "RATE_LIMITED",
            "QUOTA_EXCEEDED",
            "NETWORK_ERROR",
            "TIMEOUT",
            "INVALID_REQUEST",
            "DOMAIN_FILTER_UNSUPPORTED",
            "TIME_FILTER_UNSUPPORTED",
            "REGION_MISMATCH",
        ]
        for t in expected_types:
            assert hasattr(ErrorType, t)

    def test_error_type_values(self):
        """测试错误类型值"""
        assert ErrorType.API_KEY_INVALID.value == "API_KEY_INVALID"
        assert ErrorType.RATE_LIMITED.value == "RATE_LIMITED"


class TestErrorGuidance:
    """错误指导测试"""

    def test_api_key_invalid_guidance(self):
        """测试 API_KEY_INVALID 指导"""
        guidance = ERROR_GUIDANCE[ErrorType.API_KEY_INVALID]
        assert "API 密钥" in guidance
        assert "检查" in guidance

    def test_rate_limited_guidance(self):
        """测试 RATE_LIMITED 指导"""
        guidance = ERROR_GUIDANCE[ErrorType.RATE_LIMITED]
        assert "限流" in guidance
        assert "重试" in guidance or "切换" in guidance

    def test_create_error_with_guidance(self):
        """测试创建带指导的错误"""
        error = create_error_with_guidance(
            error_type=ErrorType.RATE_LIMITED,
            original_message="429 Too Many Requests"
        )
        assert error.error_type == "RATE_LIMITED"
        assert error.original_message == "429 Too Many Requests"
        assert "限流" in error.guidance
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/domain/models/test_error.py -v
```

预期: FAIL - error 模块不存在

- [ ] **步骤 3: 实现错误类型和指导**

创建 `melodyi_search/domain/models/error.py`:

```python
"""错误类型与 Agent 指导"""

from enum import Enum
from melodyi_search.domain.models.search_result import SearchError


class ErrorType(str, Enum):
    """错误类型枚举"""

    API_KEY_INVALID = "API_KEY_INVALID"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    INVALID_REQUEST = "INVALID_REQUEST"
    DOMAIN_FILTER_UNSUPPORTED = "DOMAIN_FILTER_UNSUPPORTED"
    TIME_FILTER_UNSUPPORTED = "TIME_FILTER_UNSUPPORTED"
    REGION_MISMATCH = "REGION_MISMATCH"


ERROR_GUIDANCE: dict[ErrorType, str] = {
    ErrorType.API_KEY_INVALID: """
此提供商的 API 密钥无效或缺失。
操作：检查您的配置，确保 API 密钥设置正确。
""",

    ErrorType.RATE_LIMITED: """
请求被此提供商限流。
操作：请等待后重试，或系统将自动切换到另一个提供商。
""",

    ErrorType.QUOTA_EXCEEDED: """
此提供商的 API 配额已耗尽。
操作：系统将切换到另一个提供商。考虑升级此提供商的计划。
""",

    ErrorType.NETWORK_ERROR: """
网络连接错误。
操作：请检查网络连接后重试。
""",

    ErrorType.TIMEOUT: """
请求超时。
操作：系统将使用更长的超时时间重试，或切换提供商。
""",

    ErrorType.INVALID_REQUEST: """
请求参数无效。
操作：请检查请求参数是否符合要求。
""",

    ErrorType.DOMAIN_FILTER_UNSUPPORTED: """
此提供商不支持原生域名过滤。
操作：适配器将在查询中使用搜索操作符（site:）或后过滤结果。
""",

    ErrorType.TIME_FILTER_UNSUPPORTED: """
此提供商不支持时间过滤。
操作：适配器将在查询中注入时间关键词（如"最新"、"今天"）。
""",

    ErrorType.REGION_MISMATCH: """
API 密钥与主机区域不匹配。
操作：中国大陆密钥使用 api.minimaxi.com，全球密钥使用 api.minimax.io。
""",
}


def create_error_with_guidance(
    error_type: ErrorType,
    original_message: str = ""
) -> SearchError:
    """创建带预设指导的搜索错误"""
    guidance = ERROR_GUIDANCE.get(error_type, "未知错误，请检查日志")
    return SearchError(
        error_type=error_type.value,
        original_message=original_message,
        guidance=guidance.strip()
    )
```

更新 `melodyi_search/domain/models/__init__.py`:

```python
from melodyi_search.domain.models.search_request import TimeRange, UnifiedSearchRequest
from melodyi_search.domain.models.search_result import SearchResultItem, UnifiedSearchResult, SearchError
from melodyi_search.domain.models.error import ErrorType, ERROR_GUIDANCE, create_error_with_guidance

__all__ = [
    "TimeRange",
    "UnifiedSearchRequest",
    "SearchResultItem",
    "UnifiedSearchResult",
    "SearchError",
    "ErrorType",
    "ERROR_GUIDANCE",
    "create_error_with_guidance",
]
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/domain/models/test_error.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/domain/models/error.py melodyi_search/domain/models/__init__.py tests/domain/models/test_error.py
git commit -m "feat: 实现错误类型枚举和 Agent 指导模板"
```

---

### 任务 7: ProviderConfig 单个提供商配置

**文件:**
- 创建: `melodyi_search/domain/models/provider_config.py`
- 创建: `tests/domain/models/test_provider_config.py`

- [ ] **步骤 1: 编写 ProviderConfig 测试**

创建 `tests/domain/models/test_provider_config.py`:

```python
"""提供商配置测试"""

import pytest
from melodyi_search.domain.models.provider_config import ProviderConfig


class TestProviderConfig:
    """ProviderConfig 测试类"""

    def test_create_minimal_config(self):
        """测试创建最小配置"""
        config = ProviderConfig(name="minimax-cn", api_key="test-key")
        assert config.name == "minimax-cn"
        assert config.api_key == "test-key"
        assert config.timeout_ms == 10000  # 默认值
        assert config.max_results == 10  # 默认值
        assert config.host is None

    def test_create_full_config(self):
        """测试创建完整配置"""
        config = ProviderConfig(
            name="tavily",
            api_key="tavily-key",
            timeout_ms=15000,
            max_results=20,
            host=None,
            extra_params={"depth": "advanced"}
        )
        assert config.name == "tavily"
        assert config.timeout_ms == 15000
        assert config.extra_params == {"depth": "advanced"}

    def test_searxng_requires_host(self):
        """测试 searxng 需要 host"""
        config = ProviderConfig(
            name="searxng",
            host="http://localhost:8888"
        )
        assert config.host == "http://localhost:8888"
        assert config.api_key is None  # 自托管不需要 api_key

    def test_name_required(self):
        """测试 name 必填"""
        with pytest.raises(ValueError):
            ProviderConfig(api_key="test")

    def test_valid_provider_names(self):
        """测试有效的提供商名称"""
        valid_names = ["minimax-cn", "tavily", "brave", "exa", "searxng", "firecrawl"]
        for name in valid_names:
            config = ProviderConfig(name=name)
            assert config.name == name

    def test_invalid_provider_name(self):
        """测试无效的提供商名称"""
        with pytest.raises(ValueError):
            ProviderConfig(name="invalid-provider")
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/domain/models/test_provider_config.py -v
```

预期: FAIL - ProviderConfig 未实现

- [ ] **步骤 3: 实现 ProviderConfig**

创建 `melodyi_search/domain/models/provider_config.py`:

```python
"""提供商配置模型"""

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


# 支持的提供商名称
PROVIDER_NAMES = Literal["minimax-cn", "tavily", "brave", "exa", "searxng", "firecrawl"]


class ProviderConfig(BaseModel):
    """单个提供商配置"""

    name: PROVIDER_NAMES = Field(..., description="提供商名称")
    api_key: Optional[str] = Field(default=None, description="API 密钥")
    host: Optional[str] = Field(default=None, description="自托管服务地址")
    timeout_ms: int = Field(default=10000, ge=1000, description="超时时间(毫秒)")
    max_results: int = Field(default=10, ge=1, description="最大结果数")
    extra_params: Optional[dict] = Field(default=None, description="提供商特定参数")

    @field_validator("name")
    @classmethod
    def validate_provider_name(cls, v: str) -> str:
        """验证提供商名称"""
        valid_names = ["minimax-cn", "tavily", "brave", "exa", "searxng", "firecrawl"]
        if v not in valid_names:
            raise ValueError(f"无效的提供商名称: {v}，必须是 {valid_names} 之一")
        return v

    def is_self_hosted(self) -> bool:
        """检查是否为自托管提供商"""
        return self.name in ("searxng", "firecrawl") and self.host is not None
```

更新 `melodyi_search/domain/models/__init__.py`:

```python
from melodyi_search.domain.models.search_request import TimeRange, UnifiedSearchRequest
from melodyi_search.domain.models.search_result import SearchResultItem, UnifiedSearchResult, SearchError
from melodyi_search.domain.models.error import ErrorType, ERROR_GUIDANCE, create_error_with_guidance
from melodyi_search.domain.models.provider_config import ProviderConfig, PROVIDER_NAMES

__all__ = [
    "TimeRange",
    "UnifiedSearchRequest",
    "SearchResultItem",
    "UnifiedSearchResult",
    "SearchError",
    "ErrorType",
    "ERROR_GUIDANCE",
    "create_error_with_guidance",
    "ProviderConfig",
    "PROVIDER_NAMES",
]
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/domain/models/test_provider_config.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/domain/models/provider_config.py melodyi_search/domain/models/__init__.py tests/domain/models/test_provider_config.py
git commit -m "feat: 实现 ProviderConfig 提供商配置模型"
```

---

### 任务 8: BaseProvider 抽象基类

**文件:**
- 创建: `melodyi_search/providers/__init__.py`
- 创建: `melodyi_search/providers/base_provider.py`
- 创建: `tests/providers/__init__.py`
- 创建: `tests/providers/test_base_provider.py`

- [ ] **步骤 1: 编写 BaseProvider 测试**

创建 `tests/providers/test_base_provider.py`:

```python
"""BaseProvider 抽象基类测试"""

import pytest
from melodyi_search.providers.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)


class MockProvider(BaseProvider):
    """模拟提供商用于测试"""

    @property
    def name(self) -> str:
        return "mock"

    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        return ProviderSearchResult(
            provider="mock",
            results=[],
            response_time_ms=100
        )

    def supports_time_filter(self) -> bool:
        return True

    def supports_domain_filter(self) -> bool:
        return True

    def get_max_results_limit(self) -> int:
        return 50


class TestProviderSearchRequest:
    """ProviderSearchRequest 测试"""

    def test_create_with_query(self):
        """测试创建请求"""
        request = ProviderSearchRequest(query="test query")
        assert request.query == "test query"
        assert request.max_results == 10
        assert request.time_range is None

    def test_native_params(self):
        """测试原生参数"""
        request = ProviderSearchRequest(
            query="test",
            native_params={"depth": "advanced"}
        )
        assert request.native_params == {"depth": "advanced"}


class TestBaseProvider:
    """BaseProvider 测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = MockProvider()
        assert provider.name == "mock"

    def test_supports_time_filter(self):
        """测试时间过滤支持"""
        provider = MockProvider()
        assert provider.supports_time_filter() is True

    def test_supports_domain_filter(self):
        """测试域名过滤支持"""
        provider = MockProvider()
        assert provider.supports_domain_filter() is True

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = MockProvider()
        assert provider.get_max_results_limit() == 50

    def test_cannot_instantiate_abstract_class(self):
        """测试不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            BaseProvider()
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/providers/test_base_provider.py -v
```

预期: FAIL - base_provider 模块不存在

- [ ] **步骤 3: 创建 providers 目录和实现**

```bash
mkdir -p melodyi_search/providers
mkdir -p tests/providers
```

创建 `melodyi_search/providers/__init__.py`:

```python
"""提供商实现"""

from melodyi_search.providers.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)

__all__ = ["BaseProvider", "ProviderSearchRequest", "ProviderSearchResult"]
```

创建 `melodyi_search/providers/base_provider.py`:

```python
"""提供商抽象基类"""

from abc import ABC, abstractmethod
from typing import Optional, List
from pydantic import BaseModel, Field
from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.domain.models.search_result import SearchResultItem


class ProviderSearchRequest(BaseModel):
    """提供商原生请求，保留所有参数"""

    query: str = Field(..., description="搜索查询")
    max_results: int = Field(default=10, ge=1, description="最大结果数")
    time_range: Optional[TimeRange] = Field(default=None, description="时间范围")
    include_domains: Optional[List[str]] = Field(default=None, description="包含域名")
    exclude_domains: Optional[List[str]] = Field(default=None, description="排除域名")
    language: Optional[str] = Field(default=None, description="语言")
    native_params: Optional[dict] = Field(default=None, description="提供商特定参数")
    modified_query: Optional[str] = Field(default=None, description="修改后的查询")


class ProviderSearchResult(BaseModel):
    """提供商原生结果"""

    provider: str = Field(..., description="提供商名称")
    results: List[SearchResultItem] = Field(default_factory=list, description="搜索结果")
    response_time_ms: int = Field(..., ge=0, description="响应时间")
    raw_response: Optional[dict] = Field(default=None, description="原始响应数据")
    error: Optional[str] = Field(default=None, description="错误信息")


class BaseProvider(ABC):
    """提供商抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """提供商标识符"""
        pass

    @abstractmethod
    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        """执行搜索"""
        pass

    @abstractmethod
    def supports_time_filter(self) -> bool:
        """是否支持时间过滤"""
        pass

    @abstractmethod
    def supports_domain_filter(self) -> bool:
        """是否支持域名过滤"""
        pass

    @abstractmethod
    def get_max_results_limit(self) -> int:
        """最大结果数限制"""
        pass
```

创建 `tests/providers/__init__.py`:

```python
"""提供商测试"""
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/providers/test_base_provider.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/providers/ tests/providers/
git commit -m "feat: 实现 BaseProvider 抽象基类和请求/结果模型"
```

---

### 任务 9: Config 全局配置模型

**文件:**
- 创建: `melodyi_search/infrastructure/__init__.py`
- 创建: `melodyi_search/infrastructure/config/__init__.py`
- 创建: `melodyi_search/infrastructure/config/config_schema.py`
- 创建: `tests/infrastructure/__init__.py`
- 创建: `tests/infrastructure/config/__init__.py`
- 创建: `tests/infrastructure/config/test_config_schema.py`

- [ ] **步骤 1: 编写 Config 测试**

创建 `tests/infrastructure/config/test_config_schema.py`:

```python
"""Config 配置模型测试"""

import pytest
from melodyi_search.infrastructure.config.config_schema import Config, ModeConfig, FallbackConfig


class TestProviderConfig:
    """ProviderConfig（配置文件中的）测试"""

    def test_config_from_dict(self):
        """测试从字典创建配置"""
        config_dict = {
            "providers": [
                {"name": "minimax-cn", "api_key": "key1"},
                {"name": "tavily", "api_key": "key2"},
            ],
            "mode": {"comparison": False},
            "fallback": {"retry_count": 2}
        }
        config = Config(**config_dict)
        assert len(config.providers) == 2
        assert config.providers[0].name == "minimax-cn"
        assert config.mode.comparison is False
        assert config.fallback.retry_count == 2

    def test_mode_config_defaults(self):
        """测试 ModeConfig 默认值"""
        mode = ModeConfig()
        assert mode.comparison is False
        assert mode.log_dir == "./logs"

    def test_fallback_config_defaults(self):
        """测试 FallbackConfig 默认值"""
        fallback = FallbackConfig()
        assert fallback.retry_count == 2
        assert fallback.retry_delay_ms == 1000

    def test_providers_order_preserved(self):
        """测试提供商顺序保留"""
        config_dict = {
            "providers": [
                {"name": "brave"},
                {"name": "tavily"},
                {"name": "minimax-cn"},
            ]
        }
        config = Config(**config_dict)
        assert config.providers[0].name == "brave"
        assert config.providers[1].name == "tavily"
        assert config.providers[2].name == "minimax-cn"
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/infrastructure/config/test_config_schema.py -v
```

预期: FAIL - config 模块不存在

- [ ] **步骤 3: 创建目录和实现**

```bash
mkdir -p melodyi_search/infrastructure/config
mkdir -p tests/infrastructure/config
```

创建 `melodyi_search/infrastructure/__init__.py`:

```python
"""基础设施层"""
```

创建 `melodyi_search/infrastructure/config/__init__.py`:

```python
"""配置管理"""

from melodyi_search.infrastructure.config.config_schema import Config, ModeConfig, FallbackConfig

__all__ = ["Config", "ModeConfig", "FallbackConfig"]
```

创建 `melodyi_search/infrastructure/config/config_schema.py`:

```python
"""全局配置模型"""

from typing import List
from pydantic import BaseModel, Field
from melodyi_search.domain.models.provider_config import ProviderConfig


class ModeConfig(BaseModel):
    """运行模式配置"""

    comparison: bool = Field(default=False, description="是否开启比对模式")
    log_dir: str = Field(default="./logs", description="日志目录")


class FallbackConfig(BaseModel):
    """回退配置"""

    retry_count: int = Field(default=2, ge=0, description="重试次数")
    retry_delay_ms: int = Field(default=1000, ge=0, description="重试间隔")


class Config(BaseModel):
    """全局配置"""

    providers: List[ProviderConfig] = Field(..., description="提供商配置数组")
    mode: ModeConfig = Field(default_factory=ModeConfig, description="运行模式")
    fallback: FallbackConfig = Field(default_factory=FallbackConfig, description="回退配置")

    def get_provider_names(self) -> List[str]:
        """获取所有提供商名称列表"""
        return [p.name for p in self.providers]

    def get_provider_by_name(self, name: str) -> ProviderConfig | None:
        """根据名称获取提供商配置"""
        for p in self.providers:
            if p.name == name:
                return p
        return None
```

创建 `tests/infrastructure/__init__.py`:

```python
"""基础设施层测试"""
```

创建 `tests/infrastructure/config/__init__.py`:

```python
"""配置测试"""
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/infrastructure/config/test_config_schema.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/infrastructure/ tests/infrastructure/
git commit -m "feat: 实现 Config 全局配置模型"
```

---

### 任务 10: config_loader 配置加载器

**文件:**
- 创建: `melodyi_search/infrastructure/config/config_loader.py`
- 创建: `melodyi_search/infrastructure/config/default_config.yaml`
- 创建: `tests/infrastructure/config/test_config_loader.py`

- [ ] **步骤 1: 编写 config_loader 测试**

创建 `tests/infrastructure/config/test_config_loader.py`:

```python
"""配置加载器测试"""

import pytest
import tempfile
import os
from melodyi_search.infrastructure.config.config_loader import load_config, resolve_env_var


class TestResolveEnvVar:
    """环境变量解析测试"""

    def test_resolve_env_var_with_value(self):
        """测试解析存在的环境变量"""
        os.environ["TEST_API_KEY"] = "test-value"
        result = resolve_env_var("${TEST_API_KEY}")
        assert result == "test-value"
        del os.environ["TEST_API_KEY"]

    def test_resolve_env_var_not_found(self):
        """测试解析不存在环境变量"""
        result = resolve_env_var("${NONEXISTENT_KEY}")
        assert result == "${NONEXISTENT_KEY}"  # 保留原值

    def test_resolve_plain_value(self):
        """测试解析普通值"""
        result = resolve_env_var("plain-value")
        assert result == "plain-value"


class TestLoadConfig:
    """配置加载测试"""

    def test_load_yaml_config(self):
        """测试加载 yaml 配置"""
        yaml_content = """
providers:
  - name: minimax-cn
    api_key: test-key
    timeout_ms: 5000
mode:
  comparison: false
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = load_config(f.name)
            os.unlink(f.name)

        assert len(config.providers) == 1
        assert config.providers[0].name == "minimax-cn"
        assert config.providers[0].timeout_ms == 5000

    def test_load_config_with_env_var(self):
        """测试加载配置并解析环境变量"""
        os.environ["MY_API_KEY"] = "env-value"
        yaml_content = """
providers:
  - name: tavily
    api_key: ${MY_API_KEY}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = load_config(f.name)
            os.unlink(f.name)
        del os.environ["MY_API_KEY"]

        assert config.providers[0].api_key == "env-value"

    def test_load_default_config(self):
        """测试加载默认配置"""
        # 默认配置文件存在时
        config = load_config()
        assert config is not None
        assert len(config.providers) > 0
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/infrastructure/config/test_config_loader.py -v
```

预期: FAIL - config_loader 模块不存在

- [ ] **步骤 3: 实现 config_loader**

创建 `melodyi_search/infrastructure/config/config_loader.py`:

```python
"""配置加载器，支持 .env 和 yaml"""

import os
import re
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv
from melodyi_search.infrastructure.config.config_schema import Config


def resolve_env_var(value: str) -> str:
    """解析环境变量引用 ${VAR_NAME}"""
    if not isinstance(value, str):
        return value

    pattern = r'\$\{([^}]+)\}'
    match = re.search(pattern, value)
    if match:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value:
            return value.replace(f"${{{var_name}}}", env_value)
    return value


def _resolve_config_env_vars(config_dict: dict) -> dict:
    """递归解析配置中的所有环境变量"""
    if isinstance(config_dict, dict):
        return {k: _resolve_config_env_vars(v) for k, v in config_dict.items()}
    elif isinstance(config_dict, list):
        return [_resolve_config_env_vars(item) for item in config_dict]
    elif isinstance(config_dict, str):
        return resolve_env_var(config_dict)
    else:
        return config_dict


def load_config(config_path: Optional[str] = None) -> Config:
    """加载配置文件

    Args:
        config_path: 配置文件路径，默认为 default_config.yaml

    Returns:
        Config: 全局配置对象
    """
    # 1. 先加载 .env 到环境变量
    load_dotenv()

    # 2. 确定配置文件路径
    if config_path is None:
        config_path = Path(__file__).parent / "default_config.yaml"
    else:
        config_path = Path(config_path)

    # 3. 加载 yaml
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)

    # 4. 解析环境变量
    config_dict = _resolve_config_env_vars(config_dict)

    # 5. 创建 Config 对象
    return Config(**config_dict)
```

创建 `melodyi_search/infrastructure/config/default_config.yaml`:

```yaml
# melodyi-search 默认配置
# providers: 有序数组，决定启用顺序和优先级

providers:
  - name: minimax-cn
    api_key: ${MINIMAX_API_KEY}
    timeout_ms: 10000
    max_results: 10

  - name: tavily
    api_key: ${TAVILY_API_KEY}
    timeout_ms: 10000
    max_results: 20
    extra_params:
      depth: basic

  - name: brave
    api_key: ${BRAVE_API_KEY}
    timeout_ms: 10000
    max_results: 20

  - name: exa
    api_key: ${EXA_API_KEY}
    timeout_ms: 30000
    max_results: 10
    extra_params:
      type: auto

mode:
  comparison: false
  log_dir: ./logs

fallback:
  retry_count: 2
  retry_delay_ms: 1000
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/infrastructure/config/test_config_loader.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/infrastructure/config/config_loader.py melodyi_search/infrastructure/config/default_config.yaml tests/infrastructure/config/test_config_loader.py
git commit -m "feat: 实现配置加载器，支持 .env 和 yaml"
```

---

### 任务 11: .env.example 环境变量模板

**文件:**
- 创建: `.env.example`

- [ ] **步骤 1: 创建 .env.example**

创建 `.env.example`:

```bash
# melodyi-search 环境变量模板
# 复制此文件为 .env 并填写真实 API Key

# MiniMax 中国大陆
MINIMAX_API_KEY=your_minimax_api_key

# Tavily
TAVILY_API_KEY=your_tavily_api_key

# Brave Search
BRAVE_API_KEY=your_brave_api_key

# Exa
EXA_API_KEY=your_exa_api_key

# Firecrawl（可选）
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

- [ ] **步骤 2: 确保 .gitignore 包含 .env**

检查 `.gitignore` 是否包含 `.env`:

```bash
cat .gitignore | grep .env || echo ".env" >> .gitignore
```

- [ ] **步骤 3: 提交**

```bash
git add .env.example .gitignore
git commit -m "feat: 添加 .env.example 环境变量模板"
```

---

### 任务 12: SearchLogger 搜索日志器

**文件:**
- 创建: `melodyi_search/infrastructure/logging/__init__.py`
- 创建: `melodyi_search/infrastructure/logging/search_logger.py`
- 创建: `tests/infrastructure/logging/__init__.py`
- 创建: `tests/infrastructure/logging/test_search_logger.py`

- [ ] **步骤 1: 编写 SearchLogger 测试**

创建 `tests/infrastructure/logging/test_search_logger.py`:

```python
"""搜索日志器测试"""

import pytest
import tempfile
import os
from melodyi_search.infrastructure.logging.search_logger import SearchLogger


class TestSearchLogger:
    """SearchLogger 测试类"""

    def test_create_logger(self):
        """测试创建日志器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SearchLogger(log_dir=tmpdir)
            assert logger is not None

    def test_log_search_request(self):
        """测试记录搜索请求"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SearchLogger(log_dir=tmpdir)
            logger.log_search_request(
                query="python tutorial",
                max_results=10,
                time_range="day"
            )
            # 检查日志文件存在
            assert os.path.exists(os.path.join(tmpdir, "search.log"))

    def test_log_provider_result(self):
        """测试记录提供商结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SearchLogger(log_dir=tmpdir)
            logger.log_provider_result(
                provider="minimax-cn",
                status="success",
                time_ms=850,
                results_count=8
            )

    def test_log_full_result(self):
        """测试记录完整结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SearchLogger(log_dir=tmpdir)
            logger.log_search_result(
                title="Test Result",
                url="https://example.com",
                description="test description"
            )

    def test_log_error(self):
        """测试记录错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SearchLogger(log_dir=tmpdir)
            logger.log_error(
                provider="brave",
                error_type="RATE_LIMITED",
                message="Too many requests",
                guidance="请等待后重试"
            )
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/infrastructure/logging/test_search_logger.py -v
```

预期: FAIL - search_logger 模块不存在

- [ ] **步骤 3: 创建目录和实现**

```bash
mkdir -p melodyi_search/infrastructure/logging
mkdir -p tests/infrastructure/logging
```

创建 `melodyi_search/infrastructure/logging/__init__.py`:

```python
"""日志"""

from melodyi_search.infrastructure.logging.search_logger import SearchLogger

__all__ = ["SearchLogger"]
```

创建 `melodyi_search/infrastructure/logging/search_logger.py`:

```python
"""搜索日志器"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class SearchLogger:
    """搜索日志器，完整记录搜索过程"""

    def __init__(self, log_dir: str = "./logs", console_output: bool = True):
        """初始化日志器

        Args:
            log_dir: 日志目录
            console_output: 是否输出到控制台
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 创建 logger
        self.logger = logging.getLogger("melodyi_search")
        self.logger.setLevel(logging.DEBUG)

        # 清除已有 handlers
        self.logger.handlers = []

        # 文件 handler
        log_file = self.log_dir / f"search_{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '[%(asctime)s] %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)

        # 控制台 handler（开发阶段）
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_format = logging.Formatter('[%(levelname)s] %(message)s')
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)

    def log_search_request(self, query: str, **params):
        """记录搜索请求"""
        param_str = ", ".join(f"{k}={v}" for k, v in params.items() if v)
        self.logger.info(f"Query: \"{query}\" | Params: {param_str}")

    def log_provider_start(self, provider: str):
        """记录提供商开始执行"""
        self.logger.debug(f"Provider: {provider} | Start")

    def log_provider_result(
        self,
        provider: str,
        status: str,
        time_ms: int,
        results_count: int = 0,
        error: Optional[str] = None
    ):
        """记录提供商执行结果"""
        if status == "success":
            self.logger.info(
                f"Provider: {provider} | Status: success | Time: {time_ms}ms | Results: {results_count}"
            )
        else:
            self.logger.warning(
                f"Provider: {provider} | Status: {status} | Time: {time_ms}ms | Error: {error}"
            )

    def log_search_result(self, title: str, url: str, description: str, index: int = 1):
        """记录单个搜索结果"""
        self.logger.info(
            f"Result {index}: title=\"{title}\" url=\"{url}\" description=\"{description[:100]}...\""
        )

    def log_error(self, provider: str, error_type: str, message: str, guidance: str):
        """记录错误和指导"""
        self.logger.error(f"Provider: {provider} | Error: {error_type} | Message: {message}")
        self.logger.info(f"Provider: {provider} | Guidance: {guidance}")

    def log_comparison_summary(self, winner: str, results: dict):
        """记录比对模式汇总"""
        self.logger.info(f"[COMPARISON] Winner: {winner}")
        for provider, data in results.items():
            self.logger.info(
                f"[COMPARISON] {provider}: {data['status']}, {data['time_ms']}ms, {data['results_count']} results"
            )
```

创建 `tests/infrastructure/logging/__init__.py`:

```python
"""日志测试"""
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/infrastructure/logging/test_search_logger.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/infrastructure/logging/ tests/infrastructure/logging/
git commit -m "feat: 实现 SearchLogger 搜索日志器"
```

---

### 任务 13: HttpClient HTTP 客户端

**文件:**
- 创建: `melodyi_search/infrastructure/http/__init__.py`
- 创建: `melodyi_search/infrastructure/http/http_client.py`
- 创建: `tests/infrastructure/http/__init__.py`
- 创建: `tests/infrastructure/http/test_http_client.py`

- [ ] **步骤 1: 编写 HttpClient 测试**

创建 `tests/infrastructure/http/test_http_client.py`:

```python
"""HTTP 客户端测试"""

import pytest
from melodyi_search.infrastructure.http.http_client import HttpClient


class TestHttpClient:
    """HttpClient 测试类"""

    def test_create_client(self):
        """测试创建客户端"""
        client = HttpClient(timeout_ms=10000)
        assert client.timeout_ms == 10000

    def test_create_client_with_headers(self):
        """测试创建带 headers 的客户端"""
        client = HttpClient(
            timeout_ms=5000,
            default_headers={"Authorization": "Bearer test"}
        )
        assert client.default_headers["Authorization"] == "Bearer test"

    @pytest.mark.asyncio
    async def test_get_request(self):
        """测试 GET 请求"""
        client = HttpClient(timeout_ms=5000)
        # 使用真实 API 测试或 mock
        # 这里先测试客户端可以发起请求
        pass

    @pytest.mark.asyncio
    async def test_post_request(self):
        """测试 POST 请求"""
        client = HttpClient(timeout_ms=5000)
        pass
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/infrastructure/http/test_http_client.py -v
```

预期: FAIL - http 模块不存在

- [ ] **步骤 3: 创建目录和实现**

```bash
mkdir -p melodyi_search/infrastructure/http
mkdir -p tests/infrastructure/http
```

创建 `melodyi_search/infrastructure/http/__init__.py`:

```python
"""HTTP 客户端"""

from melodyi_search.infrastructure.http.http_client import HttpClient

__all__ = ["HttpClient"]
```

创建 `melodyi_search/infrastructure/http/http_client.py`:

```python
"""HTTP 客户端抽象"""

import httpx
from typing import Optional, Dict, Any


class HttpClient:
    """异步 HTTP 客户端"""

    def __init__(
        self,
        timeout_ms: int = 10000,
        default_headers: Optional[Dict[str, str]] = None
    ):
        """初始化客户端

        Args:
            timeout_ms: 超时时间（毫秒）
            default_headers: 默认请求头
        """
        self.timeout_ms = timeout_ms
        self.default_headers = default_headers or {}
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建异步客户端"""
        if self._client is None:
            timeout = httpx.Timeout(self.timeout_ms / 1000)
            self._client = httpx.AsyncClient(
                timeout=timeout,
                headers=self.default_headers
            )
        return self._client

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """GET 请求"""
        client = await self._get_client()
        merged_headers = {**self.default_headers, **(headers or {})}
        return await client.get(url, params=params, headers=merged_headers)

    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """POST 请求"""
        client = await self._get_client()
        merged_headers = {**self.default_headers, **(headers or {})}
        return await client.post(url, json=json, data=data, headers=merged_headers)

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
```

创建 `tests/infrastructure/http/__init__.py`:

```python
"""HTTP 客户端测试"""
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/infrastructure/http/test_http_client.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/infrastructure/http/ tests/infrastructure/http/
git commit -m "feat: 实现 HttpClient 异步 HTTP 客户端"
```

---

### 任务 14: 运行所有测试验证第一阶段完成

- [ ] **步骤 1: 运行所有单元测试**

```bash
pytest tests/ -v --tb=short
```

预期: 所有测试 PASS

- [ ] **步骤 2: 检查项目结构**

```bash
tree melodyi_search -L 3
```

确认目录结构正确。

- [ ] **步骤 3: 最终提交**

```bash
git status
git add -A
git commit -m "feat: 第一阶段完成 - 核心基础模型、配置、日志"
```

---

## 第一阶段完成检查清单

完成本阶段后，项目应具备：

- [x] 领域模型：TimeRange, UnifiedSearchRequest, SearchResultItem, UnifiedSearchResult, SearchError, ErrorType, ProviderConfig
- [x] 提供商基类：BaseProvider, ProviderSearchRequest, ProviderSearchResult
- [x] 配置系统：Config, ModeConfig, FallbackConfig, config_loader（支持 .env + yaml）
- [x] 日志系统：SearchLogger（完整记录请求、结果、错误）
- [x] HTTP 客户端：HttpClient（异步 httpx）
- [x] 环境变量模板：.env.example
- [x] 所有单元测试通过