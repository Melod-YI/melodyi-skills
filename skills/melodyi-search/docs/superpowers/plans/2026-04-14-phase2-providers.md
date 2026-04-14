# melodyi-search 实现计划 - 第二阶段：提供商实现

> **执行说明:** 使用 superpowers:subagent-driven-development 或 superpowers:executing-plans 来执行此计划。步骤使用复选框 (`- [ ]`) 进行追踪。

**目标:** 实现四个核心搜索提供商：MiniMax-CN、Tavily、Brave、Exa，每个提供商独立实现并可通过真实 API 测试。

**架构:** 每个提供商在 `providers/` 目录独立实现，继承 BaseProvider，处理各自 API 的参数映射和响应解析。

**技术栈:** Python 3.10+, httpx (异步 HTTP), pydantic (数据验证), pytest-asyncio (异步测试)

---

## 文件结构

本阶段创建以下文件：

```
melodyi_search/
├── providers/
│   ├── minimax_cn_provider.py    # MiniMax-CN 实现
│   ├── tavily_provider.py        # Tavily 实现
│   ├── brave_provider.py         # Brave 实现
│   ├── exa_provider.py           # Exa 实现
tests/
├── providers/
│   ├── test_minimax_cn_provider.py   # 单元测试（mock）
│   ├── test_tavily_provider.py       # 单元测试（mock）
│   ├── test_brave_provider.py        # 单元测试（mock）
│   ├── test_exa_provider.py          # 单元测试（mock）
├── integration/
│   ├── __init__.py
│   ├── test_minimax_cn_e2e.py        # 端到端测试（真实 API）
│   ├── test_tavily_e2e.py            # 端到端测试（真实 API）
│   ├── test_brave_e2e.py             # 端到端测试（真实 API）
│   ├── test_exa_e2e.py               # 端到端测试（真实 API）
```

---

## 任务列表

### 任务 1: MiniMax-CN 提供商实现

**文件:**
- 创建: `melodyi_search/providers/minimax_cn_provider.py`
- 创建: `tests/providers/test_minimax_cn_provider.py`
- 创建: `tests/integration/__init__.py`
- 创建: `tests/integration/test_minimax_cn_e2e.py`

- [ ] **步骤 1: 编写 MiniMax-CN 单元测试（mock）**

创建 `tests/providers/test_minimax_cn_provider.py`:

```python
"""MiniMax-CN 提供商单元测试"""

import pytest
from unittest.mock import AsyncMock, patch
from melodyi_search.providers.minimax_cn_provider import MiniMaxCNProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest
from melodyi_search.domain.models.search_request import TimeRange


class TestMiniMaxCNProvider:
    """MiniMax-CN 提供商测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = MiniMaxCNProvider(api_key="test-key")
        assert provider.name == "minimax-cn"

    def test_provider_config(self):
        """测试提供商配置"""
        provider = MiniMaxCNProvider(
            api_key="test-key",
            timeout_ms=5000,
            max_results=20
        )
        assert provider.api_key == "test-key"
        assert provider.timeout_ms == 5000
        assert provider.max_results == 20

    def test_default_api_host(self):
        """测试默认 API 地址"""
        provider = MiniMaxCNProvider(api_key="test-key")
        assert provider.api_host == "https://api.minimaxi.com"

    def test_supports_time_filter(self):
        """测试时间过滤支持"""
        provider = MiniMaxCNProvider(api_key="test-key")
        assert provider.supports_time_filter() is False

    def test_supports_domain_filter(self):
        """测试域名过滤支持"""
        provider = MiniMaxCNProvider(api_key="test-key")
        assert provider.supports_domain_filter() is False

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = MiniMaxCNProvider(api_key="test-key")
        assert provider.get_max_results_limit() == 10

    def test_inject_time_keywords_day(self):
        """测试注入时间关键词 - day"""
        provider = MiniMaxCNProvider(api_key="test-key")
        query = provider._inject_time_keywords("python教程", TimeRange(range_type="day"))
        assert "今天" in query or "最新" in query

    def test_inject_time_keywords_week(self):
        """测试注入时间关键词 - week"""
        provider = MiniMaxCNProvider(api_key="test-key")
        query = provider._inject_time_keywords("AI新闻", TimeRange(range_type="week"))
        assert "本周" in query or "最新" in query

    def test_inject_time_keywords_month(self):
        """测试注入时间关键词 - month"""
        provider = MiniMaxCNProvider(api_key="test-key")
        query = provider._inject_time_keywords("技术", TimeRange(range_type="month"))
        assert "本月" in query or "最新" in query

    @pytest.mark.asyncio
    async def test_search_mock(self):
        """测试搜索（mock）"""
        provider = MiniMaxCNProvider(api_key="test-key")

        # Mock HTTP 响应
        mock_response = {
            "choices": [{
                "messages": [{
                    "content": "搜索结果"
                }]
            }]
        }

        with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            request = ProviderSearchRequest(query="测试")
            result = await provider.search(request)
            assert result.provider == "minimax-cn"
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/providers/test_minimax_cn_provider.py -v
```

预期: FAIL - minimax_cn_provider 模块不存在

- [ ] **步骤 3: 实现 MiniMax-CN 提供商**

创建 `melodyi_search/providers/minimax_cn_provider.py`:

```python
"""MiniMax-CN 提供商实现（中国大陆）"""

import json
from typing import Optional, List
from melodyi_search.providers.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.infrastructure.http.http_client import HttpClient


class MiniMaxCNProvider(BaseProvider):
    """MiniMax 中国大陆搜索提供商"""

    # 默认 API 地址
    DEFAULT_API_HOST = "https://api.minimaxi.com"

    def __init__(
        self,
        api_key: str,
        api_host: Optional[str] = None,
        timeout_ms: int = 10000,
        max_results: int = 10
    ):
        """初始化 MiniMax-CN 提供商

        Args:
            api_key: API 密钥
            api_host: API 地址（默认中国大陆地址）
            timeout_ms: 超时时间
            max_results: 最大结果数
        """
        self.api_key = api_key
        self.api_host = api_host or self.DEFAULT_API_HOST
        self.timeout_ms = timeout_ms
        self.max_results = max_results
        self._http_client: Optional[HttpClient] = None

    @property
    def name(self) -> str:
        return "minimax-cn"

    def supports_time_filter(self) -> bool:
        """MiniMax 不支持原生时间过滤"""
        return False

    def supports_domain_filter(self) -> bool:
        """MiniMax 不支持原生域名过滤"""
        return False

    def get_max_results_limit(self) -> int:
        """MiniMax 结果数固定，不支持自定义"""
        return 10

    def _inject_time_keywords(self, query: str, time_range: Optional[TimeRange]) -> str:
        """在查询中注入时间关键词

        MiniMax 不支持时间过滤 API 参数，需要通过关键词实现
        """
        if time_range is None or time_range.is_empty():
            return query

        time_keywords = {
            "day": "今天 最新",
            "week": "本周 最新",
            "month": "本月 最新",
            "year": "今年 最新",
        }

        keyword = time_keywords.get(time_range.range_type)
        if keyword:
            return f"{query} {keyword}"

        return query

    async def _get_http_client(self) -> HttpClient:
        """获取 HTTP 客户端"""
        if self._http_client is None:
            self._http_client = HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._http_client

    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        """执行搜索

        MiniMax 搜索 API 使用对话接口模拟搜索
        """
        import time
        start_time = time.time()

        # 处理查询（注入时间关键词）
        query = self._inject_time_keywords(request.query, request.time_range)

        # 构建请求
        search_prompt = f"请帮我搜索以下内容，返回相关的网页链接和摘要：{query}"

        payload = {
            "model": "abab6.5s-chat",
            "messages": [
                {"role": "user", "content": search_prompt}
            ],
            "temperature": 0.7,
            "top_p": 0.9,
        }

        try:
            client = await self._get_http_client()
            response = await client.post(
                f"{self.api_host}/v1/chat/completions",
                json=payload
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            # 解析响应
            results = self._parse_response(response.json(), request.include_domains, request.exclude_domains)

            return ProviderSearchResult(
                provider=self.name,
                results=results,
                response_time_ms=elapsed_ms,
                raw_response=response.json()
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return ProviderSearchResult(
                provider=self.name,
                results=[],
                response_time_ms=elapsed_ms,
                error=str(e)
            )

    def _parse_response(
        self,
        response: dict,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> List[SearchResultItem]:
        """解析 MiniMax 响应

        MiniMax 返回的是对话内容，需要从中提取搜索结果
        """
        results = []

        content = response.get("choices", [{}])[0].get("messages", [{}])[0].get("content", "")

        if not content:
            return results

        # 尝试从内容中解析 URL 和标题
        # MiniMax 可能返回 JSON 格式的搜索结果或文本描述
        try:
            # 尝试解析 JSON
            if "{" in content and "}" in content:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    for item in parsed:
                        result = self._create_result_item(item)
                        if result and self._filter_domain(result, include_domains, exclude_domains):
                            results.append(result)
        except json.JSONDecodeError:
            # 解析文本中的 URL
            lines = content.split("\n")
            for line in lines:
                if "http://" in line or "https://" in line:
                    # 尝试提取 URL 和标题
                    result = self._parse_text_line(line)
                    if result and self._filter_domain(result, include_domains, exclude_domains):
                        results.append(result)

        return results[:self.max_results]

    def _create_result_item(self, item: dict) -> Optional[SearchResultItem]:
        """从 JSON 项创建 SearchResultItem"""
        try:
            url = item.get("url") or item.get("link") or ""
            title = item.get("title") or item.get("name") or ""
            description = item.get("description") or item.get("snippet") or item.get("content") or ""

            if not url:
                return None

            return SearchResultItem(
                title=title,
                url=url,
                description=description,
                provider_extra=item
            )
        except Exception:
            return None

    def _parse_text_line(self, line: str) -> Optional[SearchResultItem]:
        """从文本行解析 URL"""
        import re

        # 提取 URL
        url_match = re.search(r'(https?://[^\s]+)', line)
        if not url_match:
            return None

        url = url_match.group(1)
        # 清理 URL（去除末尾标点）
        url = url.rstrip('.,;:!?)')

        # 提取标题（URL 前面的内容）
        title = line[:url_match.start()].strip()
        if not title:
            title = "搜索结果"

        return SearchResultItem(
            title=title,
            url=url,
            description=line
        )

    def _filter_domain(
        self,
        result: SearchResultItem,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> bool:
        """域名后过滤（MiniMax 不支持原生域名过滤）"""
        domain = result.source_domain

        if include_domains:
            if not any(d in domain for d in include_domains):
                return False

        if exclude_domains:
            if any(d in domain for d in exclude_domains):
                return False

        return True
```

更新 `melodyi_search/providers/__init__.py`:

```python
"""提供商实现"""

from melodyi_search.providers.base_provider import (
    BaseProvider,
    ProviderSearchRequest,
    ProviderSearchResult,
)
from melodyi_search.providers.minimax_cn_provider import MiniMaxCNProvider

__all__ = [
    "BaseProvider",
    "ProviderSearchRequest",
    "ProviderSearchResult",
    "MiniMaxCNProvider",
]
```

- [ ] **步骤 4: 运行单元测试验证通过**

```bash
pytest tests/providers/test_minimax_cn_provider.py -v
```

预期: PASS

- [ ] **步骤 5: 编写端到端测试**

创建 `tests/integration/__init__.py`:

```python
"""端到端测试"""
```

创建 `tests/integration/test_minimax_cn_e2e.py`:

```python
"""MiniMax-CN 端到端测试（真实 API）"""

import pytest
import os
from melodyi_search.providers.minimax_cn_provider import MiniMaxCNProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest
from melodyi_search.domain.models.search_request import TimeRange


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("MINIMAX_API_KEY"),
    reason="需要 MINIMAX_API_KEY 环境变量"
)
async def test_minimax_cn_real_search():
    """真实 API 测试"""
    api_key = os.environ["MINIMAX_API_KEY"]
    provider = MiniMaxCNProvider(api_key=api_key)

    request = ProviderSearchRequest(
        query="Python教程",
        max_results=10
    )

    result = await provider.search(request)

    assert result.provider == "minimax-cn"
    assert result.response_time_ms > 0
    assert result.error is None or "error" not in result.error.lower()
    print(f"MiniMax-CN 搜索完成，耗时 {result.response_time_ms}ms，结果数 {len(result.results)}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("MINIMAX_API_KEY"),
    reason="需要 MINIMAX_API_KEY 环境变量"
)
async def test_minimax_cn_with_time_range():
    """真实 API 测试 - 带时间范围"""
    api_key = os.environ["MINIMAX_API_KEY"]
    provider = MiniMaxCNProvider(api_key=api_key)

    request = ProviderSearchRequest(
        query="AI最新动态",
        time_range=TimeRange(range_type="day")
    )

    result = await provider.search(request)

    assert result.provider == "minimax-cn"
    print(f"MiniMax-CN 时间搜索完成，查询已注入时间关键词")
```

- [ ] **步骤 6: 提交**

```bash
git add melodyi_search/providers/minimax_cn_provider.py melodyi_search/providers/__init__.py tests/providers/test_minimax_cn_provider.py tests/integration/
git commit -m "feat: 实现 MiniMax-CN 提供商"
```

---

### 任务 2: Tavily 提供商实现

**文件:**
- 创建: `melodyi_search/providers/tavily_provider.py`
- 创建: `tests/providers/test_tavily_provider.py`
- 创建: `tests/integration/test_tavily_e2e.py`

- [ ] **步骤 1: 编写 Tavily 单元测试**

创建 `tests/providers/test_tavily_provider.py`:

```python
"""Tavily 提供商单元测试"""

import pytest
from unittest.mock import AsyncMock, patch
from melodyi_search.providers.tavily_provider import TavilyProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest
from melodyi_search.domain.models.search_request import TimeRange


class TestTavilyProvider:
    """Tavily 提供商测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = TavilyProvider(api_key="test-key")
        assert provider.name == "tavily"

    def test_supports_time_filter(self):
        """测试时间过滤支持"""
        provider = TavilyProvider(api_key="test-key")
        assert provider.supports_time_filter() is True

    def test_supports_domain_filter(self):
        """测试域名过滤支持"""
        provider = TavilyProvider(api_key="test-key")
        assert provider.supports_domain_filter() is True

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = TavilyProvider(api_key="test-key")
        assert provider.get_max_results_limit() == 20

    def test_default_depth(self):
        """测试默认搜索深度"""
        provider = TavilyProvider(api_key="test-key")
        assert provider.default_depth == "basic"

    def test_build_request_params(self):
        """测试构建请求参数"""
        provider = TavilyProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="AI news",
            max_results=15,
            time_range=TimeRange(range_type="week"),
            include_domains=["github.com"],
            exclude_domains=["twitter.com"]
        )
        params = provider._build_request_params(request)
        assert params["query"] == "AI news"
        assert params["max_results"] == 15
        assert params["time_range"] == "week"
        assert params["include_domains"] == ["github.com"]
        assert params["exclude_domains"] == ["twitter.com"]

    @pytest.mark.asyncio
    async def test_search_mock(self):
        """测试搜索（mock）"""
        provider = TavilyProvider(api_key="test-key")

        mock_response = {
            "results": [
                {
                    "title": "AI News",
                    "url": "https://example.com/ai",
                    "content": "Latest AI developments"
                }
            ]
        }

        with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            request = ProviderSearchRequest(query="test")
            result = await provider.search(request)
            assert result.provider == "tavily"
            assert len(result.results) == 1
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/providers/test_tavily_provider.py -v
```

预期: FAIL - tavily_provider 模块不存在

- [ ] **步骤 3: 实现 Tavily 提供商**

创建 `melodyi_search/providers/tavily_provider.py`:

```python
"""Tavily 提供商实现"""

import time
from typing import Optional, List
from melodyi_search.providers.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.infrastructure.http.http_client import HttpClient


class TavilyProvider(BaseProvider):
    """Tavily 搜索提供商"""

    API_URL = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str,
        timeout_ms: int = 10000,
        max_results: int = 20,
        default_depth: str = "basic"
    ):
        """初始化 Tavily 提供商

        Args:
            api_key: API 密钥
            timeout_ms: 超时时间
            max_results: 最大结果数
            default_depth: 搜索深度 (basic/advanced)
        """
        self.api_key = api_key
        self.timeout_ms = timeout_ms
        self.max_results = max_results
        self.default_depth = default_depth
        self._http_client: Optional[HttpClient] = None

    @property
    def name(self) -> str:
        return "tavily"

    def supports_time_filter(self) -> bool:
        """Tavily 支持时间过滤"""
        return True

    def supports_domain_filter(self) -> bool:
        """Tavily 支持域名过滤"""
        return True

    def get_max_results_limit(self) -> int:
        """最大结果数限制"""
        return 20

    async def _get_http_client(self) -> HttpClient:
        """获取 HTTP 客户端"""
        if self._http_client is None:
            self._http_client = HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers={
                    "Content-Type": "application/json",
                }
            )
        return self._http_client

    def _build_request_params(self, request: ProviderSearchRequest) -> dict:
        """构建 Tavily API 请求参数"""
        params = {
            "api_key": self.api_key,
            "query": request.query,
            "max_results": min(request.max_results, self.max_results),
            "search_depth": self.default_depth,
        }

        # 时间范围
        if request.time_range and request.time_range.range_type:
            params["time_range"] = request.time_range.range_type

        # 域名过滤
        if request.include_domains:
            params["include_domains"] = request.include_domains

        if request.exclude_domains:
            params["exclude_domains"] = request.exclude_domains

        return params

    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        """执行搜索"""
        start_time = time.time()

        try:
            client = await self._get_http_client()
            params = self._build_request_params(request)

            response = await client.post(self.API_URL, json=params)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # 解析响应
            results = self._parse_response(response.json())

            return ProviderSearchResult(
                provider=self.name,
                results=results,
                response_time_ms=elapsed_ms,
                raw_response=response.json()
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return ProviderSearchResult(
                provider=self.name,
                results=[],
                response_time_ms=elapsed_ms,
                error=str(e)
            )

    def _parse_response(self, response: dict) -> List[SearchResultItem]:
        """解析 Tavily 响应"""
        results = []

        raw_results = response.get("results", [])

        for item in raw_results:
            try:
                result = SearchResultItem(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("content", "") or item.get("raw_content", ""),
                    published_date=None,  # Tavily 不提供发布日期
                    provider_extra=item
                )
                results.append(result)
            except Exception:
                continue

        return results
```

更新 `melodyi_search/providers/__init__.py`:

```python
from melodyi_search.providers.tavily_provider import TavilyProvider

__all__ = [
    "BaseProvider",
    "ProviderSearchRequest",
    "ProviderSearchResult",
    "MiniMaxCNProvider",
    "TavilyProvider",
]
```

- [ ] **步骤 4: 运行单元测试验证通过**

```bash
pytest tests/providers/test_tavily_provider.py -v
```

预期: PASS

- [ ] **步骤 5: 编写端到端测试**

创建 `tests/integration/test_tavily_e2e.py`:

```python
"""Tavily 端到端测试（真实 API）"""

import pytest
import os
from melodyi_search.providers.tavily_provider import TavilyProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest
from melodyi_search.domain.models.search_request import TimeRange


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("TAVILY_API_KEY"),
    reason="需要 TAVILY_API_KEY 环境变量"
)
async def test_tavily_real_search():
    """真实 API 测试"""
    api_key = os.environ["TAVILY_API_KEY"]
    provider = TavilyProvider(api_key=api_key)

    request = ProviderSearchRequest(
        query="Python machine learning tutorials",
        max_results=10
    )

    result = await provider.search(request)

    assert result.provider == "tavily"
    assert result.response_time_ms > 0
    assert result.error is None
    assert len(result.results) > 0
    print(f"Tavily 搜索完成，耗时 {result.response_time_ms}ms，结果数 {len(result.results)}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("TAVILY_API_KEY"),
    reason="需要 TAVILY_API_KEY 环境变量"
)
async def test_tavily_with_domain_filter():
    """真实 API 测试 - 带域名过滤"""
    api_key = os.environ["TAVILY_API_KEY"]
    provider = TavilyProvider(api_key=api_key)

    request = ProviderSearchRequest(
        query="Python async",
        max_results=10,
        include_domains=["github.com", "stackoverflow.com"]
    )

    result = await provider.search(request)

    assert result.provider == "tavily"
    # 检查结果域名
    for item in result.results:
        assert "github.com" in item.source_domain or "stackoverflow.com" in item.source_domain
    print(f"Tavily 域名过滤搜索完成")
```

- [ ] **步骤 6: 提交**

```bash
git add melodyi_search/providers/tavily_provider.py melodyi_search/providers/__init__.py tests/providers/test_tavily_provider.py tests/integration/test_tavily_e2e.py
git commit -m "feat: 实现 Tavily 提供商"
```

---

### 任务 3: Brave 提供商实现

**文件:**
- 创建: `melodyi_search/providers/brave_provider.py`
- 创建: `tests/providers/test_brave_provider.py`
- 创建: `tests/integration/test_brave_e2e.py`

- [ ] **步骤 1: 编写 Brave 单元测试**

创建 `tests/providers/test_brave_provider.py`:

```python
"""Brave 提供商单元测试"""

import pytest
from unittest.mock import AsyncMock, patch
from melodyi_search.providers.brave_provider import BraveProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest
from melodyi_search.domain.models.search_request import TimeRange


class TestBraveProvider:
    """Brave 提供商测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = BraveProvider(api_key="test-key")
        assert provider.name == "brave"

    def test_supports_time_filter(self):
        """测试时间过滤支持"""
        provider = BraveProvider(api_key="test-key")
        assert provider.supports_time_filter() is True

    def test_supports_domain_filter(self):
        """测试域名过滤支持"""
        provider = BraveProvider(api_key="test-key")
        assert provider.supports_domain_filter() is False  # Brave 需要 site: 操作符

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = BraveProvider(api_key="test-key")
        assert provider.get_max_results_limit() == 20

    def test_build_freshness_day(self):
        """测试构建 freshness 参数 - day"""
        provider = BraveProvider(api_key="test-key")
        freshness = provider._build_freshness(TimeRange(range_type="day"))
        assert freshness == "pd"

    def test_build_freshness_week(self):
        """测试构建 freshness 参数 - week"""
        provider = BraveProvider(api_key="test-key")
        freshness = provider._build_freshness(TimeRange(range_type="week"))
        assert freshness == "pw"

    def test_build_freshness_month(self):
        """测试构建 freshness 参数 - month"""
        provider = BraveProvider(api_key="test-key")
        freshness = provider._build_freshness(TimeRange(range_type="month"))
        assert freshness == "pm"

    def test_inject_domain_operators(self):
        """测试注入域名操作符"""
        provider = BraveProvider(api_key="test-key")
        query = provider._inject_domain_operators(
            "python tutorial",
            include_domains=["github.com"],
            exclude_domains=["twitter.com"]
        )
        assert "site:github.com" in query
        assert "-site:twitter.com" in query

    @pytest.mark.asyncio
    async def test_search_mock(self):
        """测试搜索（mock）"""
        provider = BraveProvider(api_key="test-key")

        mock_response = {
            "web": {
                "results": [
                    {
                        "title": "Python Guide",
                        "url": "https://docs.python.org",
                        "description": "Official Python documentation"
                    }
                ]
            }
        }

        with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            request = ProviderSearchRequest(query="python")
            result = await provider.search(request)
            assert result.provider == "brave"
            assert len(result.results) == 1
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/providers/test_brave_provider.py -v
```

预期: FAIL - brave_provider 模块不存在

- [ ] **步骤 3: 实现 Brave 提供商**

创建 `melodyi_search/providers/brave_provider.py`:

```python
"""Brave Search 提供商实现"""

import time
from typing import Optional, List
from melodyi_search.providers.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.infrastructure.http.http_client import HttpClient


class BraveProvider(BaseProvider):
    """Brave Search 提供商"""

    API_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(
        self,
        api_key: str,
        timeout_ms: int = 10000,
        max_results: int = 20
    ):
        """初始化 Brave 提供商

        Args:
            api_key: API 密钥
            timeout_ms: 超时时间
            max_results: 最大结果数
        """
        self.api_key = api_key
        self.timeout_ms = timeout_ms
        self.max_results = max_results
        self._http_client: Optional[HttpClient] = None

    @property
    def name(self) -> str:
        return "brave"

    def supports_time_filter(self) -> bool:
        """Brave 支持 freshness 参数"""
        return True

    def supports_domain_filter(self) -> bool:
        """Brave 不支持原生域名过滤，需要使用 site: 操作符"""
        return False

    def get_max_results_limit(self) -> int:
        """最大结果数限制"""
        return 20

    async def _get_http_client(self) -> HttpClient:
        """获取 HTTP 客户端"""
        if self._http_client is None:
            self._http_client = HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": self.api_key,
                }
            )
        return self._http_client

    def _build_freshness(self, time_range: Optional[TimeRange]) -> Optional[str]:
        """构建 Brave freshness 参数"""
        if time_range is None or time_range.is_empty():
            return None

        freshness_map = {
            "day": "pd",   # past day
            "week": "pw",  # past week
            "month": "pm", # past month
            "year": "py",  # past year
        }

        return freshness_map.get(time_range.range_type)

    def _inject_domain_operators(
        self,
        query: str,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> str:
        """注入域名搜索操作符

        Brave 不支持原生域名过滤，需要使用 site: 操作符
        """
        modified_query = query

        if include_domains:
            # 只支持单个 include_domain（site: 操作符限制）
            if len(include_domains) == 1:
                modified_query = f"site:{include_domains[0]} {modified_query}"

        if exclude_domains:
            for domain in exclude_domains:
                modified_query = f"{modified_query} -site:{domain}"

        return modified_query

    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        """执行搜索"""
        start_time = time.time()

        # 处理查询（注入域名操作符）
        query = self._inject_domain_operators(
            request.query,
            request.include_domains,
            request.exclude_domains
        )

        try:
            client = await self._get_http_client()

            params = {
                "q": query,
                "count": min(request.max_results, self.max_results),
            }

            # 时间过滤
            freshness = self._build_freshness(request.time_range)
            if freshness:
                params["freshness"] = freshness

            response = await client.get(self.API_URL, params=params)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # 解析响应
            results = self._parse_response(response.json())

            return ProviderSearchResult(
                provider=self.name,
                results=results,
                response_time_ms=elapsed_ms,
                raw_response=response.json()
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return ProviderSearchResult(
                provider=self.name,
                results=[],
                response_time_ms=elapsed_ms,
                error=str(e)
            )

    def _parse_response(self, response: dict) -> List[SearchResultItem]:
        """解析 Brave 响应"""
        results = []

        web_results = response.get("web", {}).get("results", [])

        for item in web_results:
            try:
                result = SearchResultItem(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                    published_date=None,
                    provider_extra=item
                )
                results.append(result)
            except Exception:
                continue

        return results
```

更新 `melodyi_search/providers/__init__.py`:

```python
from melodyi_search.providers.brave_provider import BraveProvider

__all__ = [
    "BaseProvider",
    "ProviderSearchRequest",
    "ProviderSearchResult",
    "MiniMaxCNProvider",
    "TavilyProvider",
    "BraveProvider",
]
```

- [ ] **步骤 4: 运行单元测试验证通过**

```bash
pytest tests/providers/test_brave_provider.py -v
```

预期: PASS

- [ ] **步骤 5: 编写端到端测试**

创建 `tests/integration/test_brave_e2e.py`:

```python
"""Brave 端到端测试（真实 API）"""

import pytest
import os
from melodyi_search.providers.brave_provider import BraveProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest
from melodyi_search.domain.models.search_request import TimeRange


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("BRAVE_API_KEY"),
    reason="需要 BRAVE_API_KEY 环境变量"
)
async def test_brave_real_search():
    """真实 API 测试"""
    api_key = os.environ["BRAVE_API_KEY"]
    provider = BraveProvider(api_key=api_key)

    request = ProviderSearchRequest(
        query="Python programming",
        max_results=10
    )

    result = await provider.search(request)

    assert result.provider == "brave"
    assert result.response_time_ms > 0
    assert result.error is None
    assert len(result.results) > 0
    print(f"Brave 搜索完成，耗时 {result.response_time_ms}ms，结果数 {len(result.results)}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("BRAVE_API_KEY"),
    reason="需要 BRAVE_API_KEY 环境变量"
)
async def test_brave_with_time_filter():
    """真实 API 测试 - 带时间过滤"""
    api_key = os.environ["BRAVE_API_KEY"]
    provider = BraveProvider(api_key=api_key)

    request = ProviderSearchRequest(
        query="AI news",
        max_results=10,
        time_range=TimeRange(range_type="week")
    )

    result = await provider.search(request)

    assert result.provider == "brave"
    print(f"Brave 时间过滤搜索完成")
```

- [ ] **步骤 6: 提交**

```bash
git add melodyi_search/providers/brave_provider.py tests/providers/test_brave_provider.py tests/integration/test_brave_e2e.py
git commit -m "feat: 实现 Brave 提供商"
```

---

### 任务 4: Exa 提供商实现

**文件:**
- 创建: `melodyi_search/providers/exa_provider.py`
- 创建: `tests/providers/test_exa_provider.py`
- 创建: `tests/integration/test_exa_e2e.py`

- [ ] **步骤 1: 编写 Exa 单元测试**

创建 `tests/providers/test_exa_provider.py`:

```python
"""Exa 提供商单元测试"""

import pytest
from unittest.mock import AsyncMock, patch
from melodyi_search.providers.exa_provider import ExaProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest
from melodyi_search.domain.models.search_request import TimeRange
from datetime import datetime, timedelta


class TestExaProvider:
    """Exa 提供商测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = ExaProvider(api_key="test-key")
        assert provider.name == "exa"

    def test_supports_time_filter(self) -> bool:
        """测试时间过滤支持"""
        provider = ExaProvider(api_key="test-key")
        return True

    def test_supports_domain_filter(self):
        """测试域名过滤支持"""
        provider = ExaProvider(api_key="test-key")
        assert provider.supports_domain_filter() is True

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = ExaProvider(api_key="test-key")
        assert provider.get_max_results_limit() == 10

    def test_default_type(self):
        """测试默认搜索类型"""
        provider = ExaProvider(api_key="test-key")
        assert provider.default_type == "auto"

    def test_build_start_date(self):
        """测试构建起始日期"""
        provider = ExaProvider(api_key="test-key")

        # 测试 day
        start_date = provider._build_start_date(TimeRange(range_type="day"))
        assert start_date is not None

        # 测试 week
        start_date = provider._build_start_date(TimeRange(range_type="week"))
        assert start_date is not None

    def test_build_request_params(self):
        """测试构建请求参数"""
        provider = ExaProvider(api_key="test-key")
        request = ProviderSearchRequest(
            query="neural networks",
            max_results=5,
            include_domains=["arxiv.org"]
        )
        params = provider._build_request_params(request)
        assert params["query"] == "neural networks"
        assert params["numResults"] == 5
        assert params["includeDomains"] == ["arxiv.org"]

    @pytest.mark.asyncio
    async def test_search_mock(self):
        """测试搜索（mock）"""
        provider = ExaProvider(api_key="test-key")

        mock_response = {
            "results": [
                {
                    "title": "Neural Networks Paper",
                    "url": "https://arxiv.org/paper",
                    "text": "Abstract of the paper",
                    "publishedDate": "2026-01-10"
                }
            ]
        }

        with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            request = ProviderSearchRequest(query="test")
            result = await provider.search(request)
            assert result.provider == "exa"
            assert len(result.results) == 1
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/providers/test_exa_provider.py -v
```

预期: FAIL - exa_provider 模块不存在

- [ ] **步骤 3: 实现 Exa 提供商**

创建 `melodyi_search/providers/exa_provider.py`:

```python
"""Exa 提供商实现"""

import time
from datetime import datetime, timedelta
from typing import Optional, List
from melodyi_search.providers.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.infrastructure.http.http_client import HttpClient


class ExaProvider(BaseProvider):
    """Exa 搜索提供商（神经网络搜索）"""

    API_URL = "https://api.exa.ai/search"

    def __init__(
        self,
        api_key: str,
        timeout_ms: int = 30000,  # Exa 搜索可能需要更长超时
        max_results: int = 10,
        default_type: str = "auto"
    ):
        """初始化 Exa 提供商

        Args:
            api_key: API 密钥
            timeout_ms: 超时时间（神经网络搜索较慢）
            max_results: 最大结果数
            default_type: 搜索类型 (auto/neural/keyword)
        """
        self.api_key = api_key
        self.timeout_ms = timeout_ms
        self.max_results = max_results
        self.default_type = default_type
        self._http_client: Optional[HttpClient] = None

    @property
    def name(self) -> str:
        return "exa"

    def supports_time_filter(self) -> bool:
        """Exa 支持 startPublishedDate 参数"""
        return True

    def supports_domain_filter(self) -> bool:
        """Exa 支持 includeDomains 和 excludeDomains"""
        return True

    def get_max_results_limit(self) -> int:
        """最大结果数限制"""
        return 10

    async def _get_http_client(self) -> HttpClient:
        """获取 HTTP 客户端"""
        if self._http_client is None:
            self._http_client = HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                }
            )
        return self._http_client

    def _build_start_date(self, time_range: Optional[TimeRange]) -> Optional[str]:
        """构建起始日期参数

        Exa 使用 ISO 8601 格式的 startPublishedDate
        """
        if time_range is None or time_range.is_empty():
            return None

        now = datetime.now()

        if time_range.range_type == "day":
            start = now - timedelta(days=1)
        elif time_range.range_type == "week":
            start = now - timedelta(weeks=1)
        elif time_range.range_type == "month":
            start = now - timedelta(days=30)
        elif time_range.range_type == "year":
            start = now - timedelta(days=365)
        else:
            return None

        return start.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _build_request_params(self, request: ProviderSearchRequest) -> dict:
        """构建 Exa API 请求参数"""
        params = {
            "query": request.query,
            "numResults": min(request.max_results, self.max_results),
            "type": self.default_type,
            "contents": {
                "text": True,  # 返回文本内容
            }
        }

        # 时间过滤
        start_date = self._build_start_date(request.time_range)
        if start_date:
            params["startPublishedDate"] = start_date

        # 域名过滤
        if request.include_domains:
            params["includeDomains"] = request.include_domains

        if request.exclude_domains:
            params["excludeDomains"] = request.exclude_domains

        return params

    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        """执行搜索"""
        start_time = time.time()

        try:
            client = await self._get_http_client()
            params = self._build_request_params(request)

            response = await client.post(self.API_URL, json=params)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # 解析响应
            results = self._parse_response(response.json())

            return ProviderSearchResult(
                provider=self.name,
                results=results,
                response_time_ms=elapsed_ms,
                raw_response=response.json()
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return ProviderSearchResult(
                provider=self.name,
                results=[],
                response_time_ms=elapsed_ms,
                error=str(e)
            )

    def _parse_response(self, response: dict) -> List[SearchResultItem]:
        """解析 Exa 响应"""
        results = []

        raw_results = response.get("results", [])

        for item in raw_results:
            try:
                # 解析发布日期
                published_date = None
                if item.get("publishedDate"):
                    try:
                        published_date = datetime.fromisoformat(
                            item["publishedDate"].replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

                result = SearchResultItem(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("text", "") or item.get("summary", ""),
                    published_date=published_date,
                    provider_extra=item
                )
                results.append(result)
            except Exception:
                continue

        return results
```

更新 `melodyi_search/providers/__init__.py`:

```python
from melodyi_search.providers.exa_provider import ExaProvider

__all__ = [
    "BaseProvider",
    "ProviderSearchRequest",
    "ProviderSearchResult",
    "MiniMaxCNProvider",
    "TavilyProvider",
    "BraveProvider",
    "ExaProvider",
]
```

- [ ] **步骤 4: 运行单元测试验证通过**

```bash
pytest tests/providers/test_exa_provider.py -v
```

预期: PASS

- [ ] **步骤 5: 编写端到端测试**

创建 `tests/integration/test_exa_e2e.py`:

```python
"""Exa 端到端测试（真实 API）"""

import pytest
import os
from melodyi_search.providers.exa_provider import ExaProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest
from melodyi_search.domain.models.search_request import TimeRange


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("EXA_API_KEY"),
    reason="需要 EXA_API_KEY 环境变量"
)
async def test_exa_real_search():
    """真实 API 测试"""
    api_key = os.environ["EXA_API_KEY"]
    provider = ExaProvider(api_key=api_key)

    request = ProviderSearchRequest(
        query="machine learning transformers",
        max_results=5
    )

    result = await provider.search(request)

    assert result.provider == "exa"
    assert result.response_time_ms > 0
    assert result.error is None
    assert len(result.results) > 0
    print(f"Exa 搜索完成，耗时 {result.response_time_ms}ms，结果数 {len(result.results)}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("EXA_API_KEY"),
    reason="需要 EXA_API_KEY 环境变量"
)
async def test_exa_with_domain_filter():
    """真实 API 测试 - 带域名过滤"""
    api_key = os.environ["EXA_API_KEY"]
    provider = ExaProvider(api_key=api_key)

    request = ProviderSearchRequest(
        query="deep learning",
        max_results=5,
        include_domains=["arxiv.org"]
    )

    result = await provider.search(request)

    assert result.provider == "exa"
    # 检查结果域名
    for item in result.results:
        assert "arxiv.org" in item.source_domain
    print(f"Exa 域名过滤搜索完成")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("EXA_API_KEY"),
    reason="需要 EXA_API_KEY 环境变量"
)
async def test_exa_with_time_filter():
    """真实 API 测试 - 带时间过滤"""
    api_key = os.environ["EXA_API_KEY"]
    provider = ExaProvider(api_key=api_key)

    request = ProviderSearchRequest(
        query="AI research",
        max_results=5,
        time_range=TimeRange(range_type="week")
    )

    result = await provider.search(request)

    assert result.provider == "exa"
    print(f"Exa 时间过滤搜索完成")
```

- [ ] **步骤 6: 提交**

```bash
git add melodyi_search/providers/exa_provider.py tests/providers/test_exa_provider.py tests/integration/test_exa_e2e.py
git commit -m "feat: 实现 Exa 提供商"
```

---

### 任务 5: 运行所有端到端测试

- [ ] **步骤 1: 确保 .env 已填写 API Key**

```bash
cat .env | grep API_KEY
```

确认四个 API Key 都已填写。

- [ ] **步骤 2: 运行端到端测试**

```bash
pytest tests/integration/ -v --tb=short
```

预期: 所有端到端测试 PASS（需要真实 API Key）

- [ ] **步骤 3: 运行所有测试**

```bash
pytest tests/ -v
```

预期: 所有测试 PASS

- [ ] **步骤 4: 最终提交**

```bash
git status
git add -A
git commit -m "feat: 第二阶段完成 - 四个核心提供商实现"
```

---

## 第二阶段完成检查清单

完成本阶段后，项目应具备：

- [x] MiniMax-CN 提供商：支持时间关键词注入、域名后过滤
- [x] Tavily 提供商：支持原生时间/域名过滤
- [x] Brave 提供商：支持 freshness 时间过滤、site: 域名操作符
- [x] Exa 提供商：支持 startPublishedDate、includeDomains/excludeDomains
- [x] 每个提供商的单元测试（mock）通过
- [x] 每个提供商的端到端测试（真实 API）通过