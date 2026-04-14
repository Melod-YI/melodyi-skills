# melodyi-search 实现计划 - 第五阶段：完善

> **执行说明:** 使用 superpowers:subagent-driven-development 或 superpowers:executing-plans 来执行此计划。步骤使用复选框 (`- [ ]`) 进行追踪。

**目标:** 实现 SearXNG 和 Firecrawl 提供商（自托管）、完善错误指导、补充文档、最终验收。

**架构:** 补充 providers/searxng_provider.py 和 providers/firecrawl_provider.py，完善错误处理和文档。

**技术栈:** Python 3.10+, httpx (异步 HTTP), pytest-asyncio (异步测试)

---

## 文件结构

本阶段创建以下文件：

```
melodyi_search/
├── providers/
│   ├── searxng_provider.py    # SearXNG 实现（自托管）
│   ├── firecrawl_provider.py  # Firecrawl 实现
│   └── __init__.py            # 更新导出
tests/
├── providers/
│   ├── test_searxng_provider.py   # 单元测试（mock）
│   ├── test_firecrawl_provider.py # 单元测试（mock）
```

---

## 任务列表

### 任务 1: SearXNG 提供商实现

**文件:**
- 创建: `melodyi_search/providers/searxng_provider.py`
- 创建: `tests/providers/test_searxng_provider.py`

- [ ] **步骤 1: 编写 SearXNG 单元测试**

创建 `tests/providers/test_searxng_provider.py`:

```python
"""SearXNG 提供商单元测试"""

import pytest
from unittest.mock import AsyncMock, patch
from melodyi_search.providers.searxng_provider import SearXNGProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest
from melodyi_search.domain.models.search_request import TimeRange


class TestSearXNGProvider:
    """SearXNG 提供商测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = SearXNGProvider(host="http://localhost:8888")
        assert provider.name == "searxng"

    def test_requires_host(self):
        """测试需要配置 host"""
        provider = SearXNGProvider(host="http://localhost:8888")
        assert provider.host == "http://localhost:8888"

    def test_supports_time_filter(self):
        """测试时间过滤支持"""
        provider = SearXNGProvider(host="http://localhost:8888")
        assert provider.supports_time_filter() is True

    def test_supports_domain_filter(self):
        """测试域名过滤支持"""
        provider = SearXNGProvider(host="http://localhost:8888")
        assert provider.supports_domain_filter() is False  # 需要 site: 操作符

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = SearXNGProvider(host="http://localhost:8888")
        # SearXNG 结果数取决于实例配置
        assert provider.get_max_results_limit() > 0

    def test_build_time_range_param(self):
        """测试构建时间范围参数"""
        provider = SearXNGProvider(host="http://localhost:8888")

        # SearXNG 使用 time_range 参数
        params = provider._build_params(
            ProviderSearchRequest(
                query="test",
                time_range=TimeRange(range_type="day")
            )
        )
        assert "time_range" in params

    @pytest.mark.asyncio
    async def test_search_mock(self):
        """测试搜索（mock）"""
        provider = SearXNGProvider(host="http://localhost:8888")

        mock_response = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "test content"
                }
            ]
        }

        with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            request = ProviderSearchRequest(query="test")
            result = await provider.search(request)
            assert result.provider == "searxng"
            assert len(result.results) == 1
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/providers/test_searxng_provider.py -v
```

预期: FAIL - searxng_provider 模块不存在

- [ ] **步骤 3: 实现 SearXNG 提供商**

创建 `melodyi_search/providers/searxng_provider.py`:

```python
"""SearXNG 提供商实现（自托管）"""

import time
from typing import Optional, List
from melodyi_search.providers.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.domain.models.search_request import TimeRange
from melodyi_search.infrastructure.http.http_client import HttpClient


class SearXNGProvider(BaseProvider):
    """SearXNG 搜索提供商（自托管实例）"""

    def __init__(
        self,
        host: str,
        timeout_ms: int = 15000,
        max_results: int = 20
    ):
        """初始化 SearXNG 提供商

        Args:
            host: SearXNG 实例地址（如 http://localhost:8888）
            timeout_ms: 超时时间
            max_results: 最大结果数
        """
        self.host = host
        self.timeout_ms = timeout_ms
        self.max_results = max_results
        self._http_client: Optional[HttpClient] = None

    @property
    def name(self) -> str:
        return "searxng"

    def supports_time_filter(self) -> bool:
        """SearXNG 支持 time_range 参数"""
        return True

    def supports_domain_filter(self) -> bool:
        """SearXNG 不支持原生域名过滤，需要使用 site: 操作符"""
        return False

    def get_max_results_limit(self) -> int:
        """最大结果数限制"""
        return self.max_results

    async def _get_http_client(self) -> HttpClient:
        """获取 HTTP 客户端"""
        if self._http_client is None:
            self._http_client = HttpClient(
                timeout_ms=self.timeout_ms,
                default_headers={
                    "Accept": "application/json",
                }
            )
        return self._http_client

    def _inject_domain_operators(
        self,
        query: str,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> str:
        """注入域名搜索操作符"""
        modified_query = query

        if include_domains:
            for domain in include_domains:
                modified_query = f"{modified_query} site:{domain}"

        if exclude_domains:
            for domain in exclude_domains:
                modified_query = f"{modified_query} -site:{domain}"

        return modified_query

    def _build_params(self, request: ProviderSearchRequest) -> dict:
        """构建 SearXNG API 参数"""
        # 处理查询
        query = self._inject_domain_operators(
            request.query,
            request.include_domains,
            request.exclude_domains
        )

        params = {
            "q": query,
            "format": "json",
            "pageno": 1,
        }

        # 时间范围
        if request.time_range and request.time_range.range_type:
            # SearXNG time_range: day, week, month, year
            params["time_range"] = request.time_range.range_type

        return params

    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        """执行搜索"""
        start_time = time.time()

        try:
            client = await self._get_http_client()
            params = self._build_params(request)

            # SearXNG search endpoint
            search_url = f"{self.host}/search"

            response = await client.get(search_url, params=params)

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
        """解析 SearXNG 响应"""
        results = []

        raw_results = response.get("results", [])

        for item in raw_results:
            try:
                result = SearchResultItem(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("content", ""),
                    published_date=None,
                    provider_extra=item
                )
                results.append(result)
            except Exception:
                continue

        return results[:self.max_results]
```

更新 `melodyi_search/providers/__init__.py`:

```python
from melodyi_search.providers.searxng_provider import SearXNGProvider

__all__ = [
    "BaseProvider",
    "ProviderSearchRequest",
    "ProviderSearchResult",
    "MiniMaxCNProvider",
    "TavilyProvider",
    "BraveProvider",
    "ExaProvider",
    "SearXNGProvider",
]
```

- [ ] **步骤 4: 运行单元测试验证通过**

```bash
pytest tests/providers/test_searxng_provider.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/providers/searxng_provider.py tests/providers/test_searxng_provider.py
git commit -m "feat: 实现 SearXNG 提供商（自托管）"
```

---

### 任务 2: Firecrawl 提供商实现

**文件:**
- 创建: `melodyi_search/providers/firecrawl_provider.py`
- 创建: `tests/providers/test_firecrawl_provider.py`

- [ ] **步骤 1: 编写 Firecrawl 单元测试**

创建 `tests/providers/test_firecrawl_provider.py`:

```python
"""Firecrawl 提供商单元测试"""

import pytest
from unittest.mock import AsyncMock, patch
from melodyi_search.providers.firecrawl_provider import FirecrawlProvider
from melodyi_search.providers.base_provider import ProviderSearchRequest
from melodyi_search.domain.models.search_request import TimeRange


class TestFirecrawlProvider:
    """Firecrawl 提供商测试"""

    def test_provider_name(self):
        """测试提供商名称"""
        provider = FirecrawlProvider(api_key="test-key")
        assert provider.name == "firecrawl"

    def test_with_host_self_hosted(self):
        """测试自托管配置"""
        provider = FirecrawlProvider(
            api_key="test-key",
            host="http://localhost:3002"
        )
        assert provider.host == "http://localhost:3002"

    def test_without_host_cloud(self):
        """测试云服务配置"""
        provider = FirecrawlProvider(api_key="test-key")
        assert provider.api_host == "https://api.firecrawl.dev"

    def test_supports_time_filter(self):
        """测试时间过滤支持"""
        provider = FirecrawlProvider(api_key="test-key")
        # Firecrawl 搜索功能有限
        assert provider.supports_time_filter() is False

    def test_supports_domain_filter(self):
        """测试域名过滤支持"""
        provider = FirecrawlProvider(api_key="test-key")
        assert provider.supports_domain_filter() is False

    def test_max_results_limit(self):
        """测试最大结果限制"""
        provider = FirecrawlProvider(api_key="test-key")
        assert provider.get_max_results_limit() == 10

    @pytest.mark.asyncio
    async def test_search_mock(self):
        """测试搜索（mock）"""
        provider = FirecrawlProvider(api_key="test-key")

        mock_response = {
            "success": True,
            "data": [
                {
                    "url": "https://example.com",
                    "markdown": "Example content"
                }
            ]
        }

        with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            request = ProviderSearchRequest(query="test")
            result = await provider.search(request)
            assert result.provider == "firecrawl"
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/providers/test_firecrawl_provider.py -v
```

预期: FAIL - firecrawl_provider 模块不存在

- [ ] **步骤 3: 实现 Firecrawl 提供商**

创建 `melodyi_search/providers/firecrawl_provider.py`:

```python
"""Firecrawl 提供商实现"""

import time
from typing import Optional, List
from melodyi_search.providers.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult
from melodyi_search.domain.models.search_result import SearchResultItem
from melodyi_search.infrastructure.http.http_client import HttpClient


class FirecrawlProvider(BaseProvider):
    """Firecrawl 搜索提供商（支持搜索+抓取）"""

    # 云服务 API 地址
    CLOUD_API_HOST = "https://api.firecrawl.dev"

    def __init__(
        self,
        api_key: str,
        host: Optional[str] = None,
        timeout_ms: int = 10000,
        max_results: int = 10
    ):
        """初始化 Firecrawl 提供商

        Args:
            api_key: API 密钥
            host: 自托管地址（可选）
            timeout_ms: 超时时间
            max_results: 最大结果数
        """
        self.api_key = api_key
        self.host = host
        self.api_host = host or self.CLOUD_API_HOST
        self.timeout_ms = timeout_ms
        self.max_results = max_results
        self._http_client: Optional[HttpClient] = None

    @property
    def name(self) -> str:
        return "firecrawl"

    def supports_time_filter(self) -> bool:
        """Firecrawl 搜索功能不支持时间过滤"""
        return False

    def supports_domain_filter(self) -> bool:
        """Firecrawl 搜索功能不支持域名过滤"""
        return False

    def get_max_results_limit(self) -> int:
        """最大结果数限制"""
        return self.max_results

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

        Firecrawl 的搜索功能需要使用 search endpoint
        """
        start_time = time.time()

        try:
            client = await self._get_http_client()

            # Firecrawl search API
            payload = {
                "query": request.query,
                "limit": min(request.max_results, self.max_results),
            }

            search_url = f"{self.api_host}/v1/search"

            response = await client.post(search_url, json=payload)

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
        """解析 Firecrawl 响应"""
        results = []

        # Firecrawl 返回格式可能有不同版本
        data = response.get("data", []) or response.get("results", [])

        for item in data:
            try:
                url = item.get("url", "")
                title = item.get("title", "") or url
                description = item.get("markdown", "") or item.get("description", "") or ""
                # 截取描述前200字符
                description = description[:200]

                if not url:
                    continue

                result = SearchResultItem(
                    title=title,
                    url=url,
                    description=description,
                    provider_extra=item
                )
                results.append(result)
            except Exception:
                continue

        return results[:self.max_results]
```

更新 `melodyi_search/providers/__init__.py`:

```python
from melodyi_search.providers.firecrawl_provider import FirecrawlProvider

__all__ = [
    "BaseProvider",
    "ProviderSearchRequest",
    "ProviderSearchResult",
    "MiniMaxCNProvider",
    "TavilyProvider",
    "BraveProvider",
    "ExaProvider",
    "SearXNGProvider",
    "FirecrawlProvider",
]
```

更新 `melodyi_search/domain/services/provider_factory.py` 注册新提供商:

```python
self._registry: dict[str, type] = {
    "minimax-cn": MiniMaxCNProvider,
    "tavily": TavilyProvider,
    "brave": BraveProvider,
    "exa": ExaProvider,
    "searxng": SearXNGProvider,
    "firecrawl": FirecrawlProvider,
}
```

- [ ] **步骤 4: 运行单元测试验证通过**

```bash
pytest tests/providers/test_firecrawl_provider.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/providers/firecrawl_provider.py melodyi_search/providers/__init__.py melodyi_search/domain/services/provider_factory.py tests/providers/test_firecrawl_provider.py
git commit -m "feat: 实现 Firecrawl 提供商"
```

---

### 任务 3: 运行所有测试验证完整功能

- [ ] **步骤 1: 运行所有单元测试**

```bash
pytest tests/ -v --tb=short
```

预期: 所有测试 PASS

- [ ] **步骤 2: 运行端到端测试**

```bash
pytest tests/integration/ -v
```

预期: 端到端测试 PASS（需要真实 API Key）

- [ ] **步骤 3: 测试 CLI 完整功能**

```bash
python -m melodyi_search config show
python -m melodyi_search search "Python教程" --max-results 5
python -m melodyi_search search "AI news" --time-range week --comparison
```

预期: 命令正常执行

- [ ] **步骤 4: 最终验收提交**

```bash
git status
git add -A
git commit -m "feat: 第五阶段完成 - 所有提供商实现、功能验收"
```

---

## 第五阶段完成检查清单

完成本阶段后，项目应具备：

- [x] SearXNG 提供商：支持自托管实例、time_range 参数、site: 域名操作符
- [x] Firecrawl 提供商：支持云服务和自托管
- [x] 所有六个提供商已实现
- [x] ProviderFactory 注册所有提供商
- [x] 所有单元测试通过
- [x] CLI 完整功能可用
- [x] skill.md 集成描述文件

---

## 项目最终验收

完成全部五个阶段后，项目功能清单：

| 功能 | 状态 |
|------|------|
| 多提供商支持 | ✓ minimax-cn, tavily, brave, exa, searxng, firecrawl |
| 配置管理 | ✓ 有序数组配置、.env 加载、yaml 解析 |
| 统一请求模型 | ✓ query + max_results + time_range + domains |
| 执行策略 | ✓ 正常模式（串行回退）+ 比对模式（并发） |
| 错误指导 | ✓ 带 Agent 可执行指导的错误 |
| 日志可观测 | ✓ 完整记录请求、结果、耗时、错误 |
| CLI 命令 | ✓ search、config show、--version |
| Agent 集成 | ✓ skill.md 描述文件 |
| 提供商隔离 | ✓ 每个提供商可独立提取使用 |