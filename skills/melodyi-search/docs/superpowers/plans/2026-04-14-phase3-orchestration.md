# melodyi-search 实现计划 - 第三阶段：编排

> **执行说明:** 使用 superpowers:subagent-driven-development 或 superpowers:executing-plans 来执行此计划。步骤使用复选框 (`- [ ]`) 进行追踪。

**目标:** 实现执行策略（正常模式串行回退 + 比对模式串行执行第一个）、参数适配服务、回退重试机制，将提供商串联为完整的搜索流程。

**架构:** domain/services 层实现 ExecutionStrategy 和 ParameterAdapter，编排提供商调用。

**技术栈:** Python 3.10+, threading (后台线程执行), pytest (同步测试)

---

## 文件结构

本阶段创建以下文件：

```
melodyi_search/
├── domain/
│   └── services/
│       ├── __init__.py
│       ├── execution_strategy.py   # 执行策略（正常/比对模式）
│       ├── parameter_adapter.py     # 参数适配服务
│       └── provider_factory.py      # 提供商工厂
tests/
├── domain/
│   └── services/
│       ├── __init__.py
│       ├── test_execution_strategy.py
│       ├── test_parameter_adapter.py
│       ├── test_provider_factory.py
├── integration/
│   └ test_fallback_e2e.py           # 回退机制端到端测试
```

---

## 任务列表

### 任务 1: ProviderFactory 提供商工厂

**文件:**
- 创建: `melodyi_search/domain/services/__init__.py`
- 创建: `melodyi_search/domain/services/provider_factory.py`
- 创建: `tests/domain/services/__init__.py`
- 创建: `tests/domain/services/test_provider_factory.py`

- [ ] **步骤 1: 编写 ProviderFactory 测试**

创建 `tests/domain/services/test_provider_factory.py`:

```python
"""提供商工厂测试"""

import pytest
from melodyi_search.domain.services.provider_factory import ProviderFactory
from melodyi_search.domain.models.provider_config import ProviderConfig
from melodyi_search.providers.base_provider import BaseProvider


class TestProviderFactory:
    """ProviderFactory 测试类"""

    def test_create_minimax_cn_provider(self):
        """测试创建 MiniMax-CN 提供商"""
        config = ProviderConfig(
            name="minimax-cn",
            api_key="test-key",
            timeout_ms=5000
        )
        factory = ProviderFactory()
        provider = factory.create(config)
        assert provider.name == "minimax-cn"
        assert provider.api_key == "test-key"

    def test_create_tavily_provider(self):
        """测试创建 Tavily 提供商"""
        config = ProviderConfig(
            name="tavily",
            api_key="test-key",
            timeout_ms=10000,
            extra_params={"depth": "advanced"}
        )
        factory = ProviderFactory()
        provider = factory.create(config)
        assert provider.name == "tavily"
        assert provider.default_depth == "advanced"

    def test_create_brave_provider(self):
        """测试创建 Brave 提供商"""
        config = ProviderConfig(
            name="brave",
            api_key="test-key"
        )
        factory = ProviderFactory()
        provider = factory.create(config)
        assert provider.name == "brave"

    def test_create_exa_provider(self):
        """测试创建 Exa 提供商"""
        config = ProviderConfig(
            name="exa",
            api_key="test-key",
            extra_params={"type": "neural"}
        )
        factory = ProviderFactory()
        provider = factory.create(config)
        assert provider.name == "exa"
        assert provider.default_type == "neural"

    def test_create_all_providers_from_config(self):
        """测试从配置创建所有提供商"""
        configs = [
            ProviderConfig(name="minimax-cn", api_key="key1"),
            ProviderConfig(name="tavily", api_key="key2"),
            ProviderConfig(name="brave", api_key="key3"),
            ProviderConfig(name="exa", api_key="key4"),
        ]
        factory = ProviderFactory()
        providers = factory.create_all(configs)
        assert len(providers) == 4
        names = [p.name for p in providers]
        assert "minimax-cn" in names
        assert "tavily" in names
        assert "brave" in names
        assert "exa" in names

    def test_invalid_provider_name(self):
        """测试无效提供商名称"""
        config = ProviderConfig(name="invalid", api_key="test")
        factory = ProviderFactory()
        with pytest.raises(ValueError):
            factory.create(config)
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/domain/services/test_provider_factory.py -v
```

预期: FAIL - provider_factory 模块不存在

- [ ] **步骤 3: 创建目录和实现**

```bash
mkdir -p melodyi_search/domain/services
mkdir -p tests/domain/services
```

创建 `melodyi_search/domain/services/__init__.py`:

```python
"""领域服务"""

from melodyi_search.domain.services.provider_factory import ProviderFactory
from melodyi_search.domain.services.execution_strategy import ExecutionStrategy
from melodyi_search.domain.services.parameter_adapter import ParameterAdapter

__all__ = ["ProviderFactory", "ExecutionStrategy", "ParameterAdapter"]
```

创建 `melodyi_search/domain/services/provider_factory.py`:

```python
"""提供商工厂"""

from typing import List
from melodyi_search.domain.models.provider_config import ProviderConfig
from melodyi_search.providers.base_provider import BaseProvider
from melodyi_search.providers.minimax_cn_provider import MiniMaxCNProvider
from melodyi_search.providers.tavily_provider import TavilyProvider
from melodyi_search.providers.brave_provider import BraveProvider
from melodyi_search.providers.exa_provider import ExaProvider


class ProviderFactory:
    """提供商工厂，根据配置创建提供商实例"""

    def __init__(self):
        """初始化工厂"""
        self._registry: dict[str, type] = {
            "minimax-cn": MiniMaxCNProvider,
            "tavily": TavilyProvider,
            "brave": BraveProvider,
            "exa": ExaProvider,
            # searxng 和 firecrawl 在第五阶段实现
        }

    def create(self, config: ProviderConfig) -> BaseProvider:
        """创建单个提供商

        Args:
            config: 提供商配置

        Returns:
            BaseProvider: 提供商实例

        Raises:
            ValueError: 不支持的提供商名称
        """
        provider_class = self._registry.get(config.name)
        if provider_class is None:
            raise ValueError(f"不支持的提供商: {config.name}")

        # 根据提供商类型创建实例
        if config.name == "minimax-cn":
            return MiniMaxCNProvider(
                api_key=config.api_key or "",
                api_host=config.host,
                timeout_ms=config.timeout_ms,
                max_results=config.max_results
            )
        elif config.name == "tavily":
            extra_params = config.extra_params or {}
            return TavilyProvider(
                api_key=config.api_key or "",
                timeout_ms=config.timeout_ms,
                max_results=config.max_results,
                default_depth=extra_params.get("depth", "basic")
            )
        elif config.name == "brave":
            return BraveProvider(
                api_key=config.api_key or "",
                timeout_ms=config.timeout_ms,
                max_results=config.max_results
            )
        elif config.name == "exa":
            extra_params = config.extra_params or {}
            return ExaProvider(
                api_key=config.api_key or "",
                timeout_ms=config.timeout_ms,
                max_results=config.max_results,
                default_type=extra_params.get("type", "auto")
            )
        else:
            raise ValueError(f"不支持的提供商: {config.name}")

    def create_all(self, configs: List[ProviderConfig]) -> List[BaseProvider]:
        """创建所有提供商

        Args:
            configs: 提供商配置列表

        Returns:
            List[BaseProvider]: 提供商实例列表
        """
        return [self.create(config) for config in configs]
```

创建 `tests/domain/services/__init__.py`:

```python
"""领域服务测试"""
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/domain/services/test_provider_factory.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/domain/services/provider_factory.py melodyi_search/domain/services/__init__.py tests/domain/services/
git commit -m "feat: 实现 ProviderFactory 提供商工厂"
```

---

### 任务 2: ParameterAdapter 参数适配服务

**文件:**
- 创建: `melodyi_search/domain/services/parameter_adapter.py`
- 创建: `tests/domain/services/test_parameter_adapter.py`

- [ ] **步骤 1: 编写 ParameterAdapter 测试**

创建 `tests/domain/services/test_parameter_adapter.py`:

```python
"""参数适配服务测试"""

import pytest
from melodyi_search.domain.services.parameter_adapter import ParameterAdapter
from melodyi_search.domain.models.search_request import UnifiedSearchRequest, TimeRange
from melodyi_search.providers.base_provider import ProviderSearchRequest
from melodyi_search.providers.minimax_cn_provider import MiniMaxCNProvider
from melodyi_search.providers.tavily_provider import TavilyProvider
from melodyi_search.providers.brave_provider import BraveProvider


class TestParameterAdapter:
    """ParameterAdapter 测试类"""

    def test_adapter_creation(self):
        """测试创建适配器"""
        adapter = ParameterAdapter()
        assert adapter is not None

    def test_adapt_for_minimax_cn(self):
        """测试适配 MiniMax-CN 提供商"""
        adapter = ParameterAdapter()
        provider = MiniMaxCNProvider(api_key="test")
        unified = UnifiedSearchRequest(
            query="python教程",
            max_results=10,
            time_range=TimeRange(range_type="day")
        )

        adapted = adapter.adapt(unified, provider)

        assert adapted.query == "python教程"
        # MiniMax 时间关键词注入在 search 时处理，不在这里
        assert adapted.max_results == 10

    def test_adapt_for_tavily(self):
        """测试适配 Tavily 提供商"""
        adapter = ParameterAdapter()
        provider = TavilyProvider(api_key="test")
        unified = UnifiedSearchRequest(
            query="AI news",
            max_results=15,
            time_range=TimeRange(range_type="week"),
            include_domains=["github.com"]
        )

        adapted = adapter.adapt(unified, provider)

        assert adapted.query == "AI news"
        assert adapted.max_results == 15
        assert adapted.time_range.range_type == "week"
        assert adapted.include_domains == ["github.com"]

    def test_adapt_for_brave(self):
        """测试适配 Brave 提供商"""
        adapter = ParameterAdapter()
        provider = BraveProvider(api_key="test")
        unified = UnifiedSearchRequest(
            query="python",
            exclude_domains=["twitter.com"]
        )

        adapted = adapter.adapt(unified, provider)

        assert adapted.query == "python"
        assert adapted.exclude_domains == ["twitter.com"]
        # Brave 域名操作符注入在 search 时处理

    def test_adapt_with_preferred_provider(self):
        """测试适配带 preferred_provider"""
        adapter = ParameterAdapter()
        provider = TavilyProvider(api_key="test")
        unified = UnifiedSearchRequest(
            query="test",
            preferred_provider="tavily"
        )

        adapted = adapter.adapt(unified, provider)
        assert adapted.query == "test"

    def test_limit_max_results_by_provider(self):
        """测试按提供商限制最大结果数"""
        adapter = ParameterAdapter()
        provider = MiniMaxCNProvider(api_key="test")  # max_results_limit = 10

        unified = UnifiedSearchRequest(
            query="test",
            max_results=50  # 超过提供商限制
        )

        adapted = adapter.adapt(unified, provider)
        # 应被限制为提供商最大值
        assert adapted.max_results <= provider.get_max_results_limit()
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/domain/services/test_parameter_adapter.py -v
```

预期: FAIL - parameter_adapter 模块不存在

- [ ] **步骤 3: 实现 ParameterAdapter**

创建 `melodyi_search/domain/services/parameter_adapter.py`:

```python
"""参数适配服务"""

from melodyi_search.domain.models.search_request import UnifiedSearchRequest
from melodyi_search.providers.base_provider import BaseProvider, ProviderSearchRequest


class ParameterAdapter:
    """参数适配服务，将统一请求转换为提供商请求"""

    def adapt(self, unified: UnifiedSearchRequest, provider: BaseProvider) -> ProviderSearchRequest:
        """适配统一请求到提供商请求

        Args:
            unified: 统一搜索请求
            provider: 目标提供商

        Returns:
            ProviderSearchRequest: 提供商原生请求
        """
        # 限制最大结果数
        max_results = unified.max_results
        provider_limit = provider.get_max_results_limit()
        if max_results > provider_limit:
            max_results = provider_limit

        # 创建提供商请求
        adapted = ProviderSearchRequest(
            query=unified.query,
            max_results=max_results,
            time_range=unified.time_range,
            include_domains=unified.include_domains,
            exclude_domains=unified.exclude_domains,
            language=unified.language,
            native_params=None,
            modified_query=None
        )

        return adapted
```

更新 `melodyi_search/domain/services/__init__.py`:

```python
from melodyi_search.domain.services.parameter_adapter import ParameterAdapter

__all__ = ["ProviderFactory", "ExecutionStrategy", "ParameterAdapter"]
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/domain/services/test_parameter_adapter.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/domain/services/parameter_adapter.py tests/domain/services/test_parameter_adapter.py
git commit -m "feat: 实现 ParameterAdapter 参数适配服务"
```

---

### 任务 3: ExecutionStrategy 执行策略

**文件:**
- 创建: `melodyi_search/domain/services/execution_strategy.py`
- 创建: `tests/domain/services/test_execution_strategy.py`

- [ ] **步骤 1: 编写 ExecutionStrategy 测试**

创建 `tests/domain/services/test_execution_strategy.py`:

```python
"""执行策略测试"""

import pytest
from unittest.mock import MagicMock
from melodyi_search.domain.services.execution_strategy import ExecutionStrategy
from melodyi_search.providers.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult
from melodyi_search.domain.models.search_result import SearchResultItem


class MockProvider(BaseProvider):
    """模拟提供商"""

    def __init__(self, name: str, delay_ms: int = 100, should_fail: bool = False):
        self._name = name
        self._delay_ms = delay_ms
        self._should_fail = should_fail

    @property
    def name(self) -> str:
        return self._name

    def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:  # 同步
        import time
        time.sleep(self._delay_ms / 1000)  # 同步 sleep

        if self._should_fail:
            return ProviderSearchResult(
                provider=self._name,
                results=[],
                response_time_ms=self._delay_ms,
                error="模拟错误"
            )

        return ProviderSearchResult(
            provider=self._name,
            results=[
                SearchResultItem(
                    title=f"Result from {self._name}",
                    url="https://example.com",
                    description="test"
                )
            ],
            response_time_ms=self._delay_ms
        )

    def supports_time_filter(self) -> bool:
        return True

    def supports_domain_filter(self) -> bool:
        return True

    def get_max_results_limit(self) -> int:
        return 10


class TestExecutionStrategy:
    """ExecutionStrategy 测试类"""

    def test_execute_normal_returns_first_success(self):
        """测试正常模式返回第一个成功结果"""
        providers = [
            MockProvider("provider1", delay_ms=100),
            MockProvider("provider2", delay_ms=200),
        ]

        strategy = ExecutionStrategy()
        request = ProviderSearchRequest(query="test")

        result = strategy.execute_normal(providers, request)

        assert result.provider == "provider1"
        assert len(result.results) == 1

    def test_execute_normal_fallback_on_error(self):
        """测试正常模式错误时回退"""
        providers = [
            MockProvider("provider1", should_fail=True),
            MockProvider("provider2", delay_ms=100),
        ]

        strategy = ExecutionStrategy()
        request = ProviderSearchRequest(query="test")

        result = strategy.execute_normal(providers, request)

        # 应回退到 provider2
        assert result.provider == "provider2"

    def test_execute_comparison_returns_first_provider(self):
        """测试比对模式返回第一个提供商"""
        providers = [
            MockProvider("slow", delay_ms=500),
            MockProvider("fast", delay_ms=100),
            MockProvider("medium", delay_ms=300),
        ]

        strategy = ExecutionStrategy()
        request = ProviderSearchRequest(query="test")

        result = strategy.execute_comparison(providers, request)

        # 应返回第一个提供商
        assert result.provider == providers[0].name

    def test_execute_all_fail_returns_error(self):
        """测试所有提供商失败返回错误"""
        providers = [
            MockProvider("p1", should_fail=True),
            MockProvider("p2", should_fail=True),
        ]

        strategy = ExecutionStrategy()
        request = ProviderSearchRequest(query="test")

        result = strategy.execute_normal(providers, request)

        assert result.error is not None
        assert len(result.results) == 0
```

- [ ] **步骤 2: 运行测试验证失败**

```bash
pytest tests/domain/services/test_execution_strategy.py -v
```

预期: FAIL - execution_strategy 模块不存在

- [ ] **步骤 3: 实现 ExecutionStrategy**

创建 `melodyi_search/domain/services/execution_strategy.py`:

```python
"""执行策略"""

import threading
import time
from typing import List, Optional
from melodyi_search.providers.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult
from melodyi_search.domain.models.search_result import UnifiedSearchResult, SearchError, SearchResultItem
from melodyi_search.domain.models.error import ErrorType, create_error_with_guidance
from melodyi_search.infrastructure.logging.search_logger import SearchLogger


class ExecutionStrategy:
    """执行策略：正常模式（串行回退）和比对模式（串行+后台线程）"""

    def __init__(self, logger: Optional[SearchLogger] = None):
        """初始化执行策略

        Args:
            logger: 搜索日志器
        """
        self.logger = logger

    def execute_normal(
        self,
        providers: List[BaseProvider],
        request: ProviderSearchRequest
    ) -> UnifiedSearchResult:
        """正常模式：按顺序串行执行，失败时回退

        Args:
            providers: 提供商列表（按优先级顺序）
            request: 提供商请求

        Returns:
            UnifiedSearchResult: 统一搜索结果
        """
        for provider in providers:
            if self.logger:
                self.logger.log_provider_start(provider.name)

            try:
                result = provider.search(request)  # 同步调用

                if self.logger:
                    self.logger.log_provider_result(
                        provider=provider.name,
                        status="success" if not result.error else "error",
                        time_ms=result.response_time_ms,
                        results_count=len(result.results),
                        error=result.error
                    )

                # 成功则返回
                if not result.error:
                    return self._convert_to_unified(result)

                # 失败则继续下一个提供商

            except Exception as e:
                if self.logger:
                    self.logger.log_provider_result(
                        provider=provider.name,
                        status="error",
                        time_ms=0,
                        error=str(e)
                    )
                continue

        # 所有提供商都失败
        error = create_error_with_guidance(
            ErrorType.INVALID_REQUEST,
            "所有提供商均失败"
        )

        return UnifiedSearchResult(
            provider="none",
            response_time_ms=0,
            results=[],
            error=error
        )

    def execute_comparison(
        self,
        providers: List[BaseProvider],
        request: ProviderSearchRequest
    ) -> UnifiedSearchResult:
        """比对模式：串行执行第一个，其余在后台线程执行

        Args:
            providers: 所有提供商列表
            request: 提供商请求

        Returns:
            UnifiedSearchResult: 第一个提供商的结果
        """
        # 第一个 provider 正常执行并返回
        result = providers[0].search(request)

        if self.logger:
            self.logger.log_provider_result(
                provider=providers[0].name,
                status="success" if not result.error else "error",
                time_ms=result.response_time_ms,
                results_count=len(result.results),
                error=result.error
            )

        # 剩余 provider 在后台线程执行并记录
        def background_task():
            for p in providers[1:]:
                try:
                    r = p.search(request)
                    if self.logger:
                        self.logger.log_provider_result(
                            provider=p.name,
                            status="success" if not r.error else "error",
                            time_ms=r.response_time_ms,
                            results_count=len(r.results),
                            error=r.error
                        )
                except Exception as e:
                    if self.logger:
                        self.logger.log_provider_result(
                            provider=p.name,
                            status="error",
                            time_ms=0,
                            error=str(e)
                        )

        threading.Thread(target=background_task, daemon=True).start()

        return self._convert_to_unified(result)

    def _convert_to_unified(self, provider_result: ProviderSearchResult) -> UnifiedSearchResult:
        """将提供商结果转换为统一结果"""
        error = None
        if provider_result.error:
            error = SearchError(
                error_type="PROVIDER_ERROR",
                original_message=provider_result.error,
                guidance="请检查提供商配置或切换提供商"
            )

        return UnifiedSearchResult(
            provider=provider_result.provider,
            response_time_ms=provider_result.response_time_ms,
            results=provider_result.results,
            error=error
        )
```

更新 `melodyi_search/domain/services/__init__.py`:

```python
from melodyi_search.domain.services.execution_strategy import ExecutionStrategy

__all__ = ["ProviderFactory", "ExecutionStrategy", "ParameterAdapter"]
```

- [ ] **步骤 4: 运行测试验证通过**

```bash
pytest tests/domain/services/test_execution_strategy.py -v
```

预期: PASS

- [ ] **步骤 5: 提交**

```bash
git add melodyi_search/domain/services/execution_strategy.py tests/domain/services/test_execution_strategy.py
git commit -m "feat: 实现 ExecutionStrategy 执行策略"
```

---

### 任务 4: 回退机制端到端测试

**文件:**
- 创建: `tests/integration/test_fallback_e2e.py`

- [ ] **步骤 1: 编写回退机制端到端测试**

创建 `tests/integration/test_fallback_e2e.py`:

```python
"""回退机制端到端测试"""

import pytest
import os
from melodyi_search.infrastructure.config.config_loader import load_config
from melodyi_search.domain.services.provider_factory import ProviderFactory
from melodyi_search.domain.services.execution_strategy import ExecutionStrategy
from melodyi_search.domain.services.parameter_adapter import ParameterAdapter
from melodyi_search.domain.models.search_request import UnifiedSearchRequest


@pytest.mark.skipif(
    not (os.environ.get("MINIMAX_API_KEY") or os.environ.get("TAVILY_API_KEY")),
    reason="需要至少一个 API Key"
)
def test_fallback_mechanism():
    """测试回退机制：从配置顺序提供商依次尝试"""
    config = load_config()
    factory = ProviderFactory()

    # 创建提供商（按配置顺序）
    providers = factory.create_all(config.providers)

    strategy = ExecutionStrategy()
    adapter = ParameterAdapter()

    # 使用第一个提供商
    unified = UnifiedSearchRequest(query="Python programming")
    request = adapter.adapt(unified, providers[0])

    result = strategy.execute_normal(providers, request)

    # 应返回某个成功提供商的结果
    assert result.provider in config.get_provider_names()
    assert result.response_time_ms > 0

    print(f"回退测试完成，使用提供商: {result.provider}")


@pytest.mark.skipif(
    not (os.environ.get("MINIMAX_API_KEY") and os.environ.get("TAVILY_API_KEY")),
    reason="需要多个 API Key"
)
def test_comparison_mode():
    """测试比对模式：返回第一个提供商结果"""
    config = load_config()
    factory = ProviderFactory()

    # 创建提供商
    providers = factory.create_all(config.providers)

    strategy = ExecutionStrategy()
    adapter = ParameterAdapter()

    unified = UnifiedSearchRequest(query="AI latest news")
    request = adapter.adapt(unified, providers[0])

    result = strategy.execute_comparison(providers, request)

    # 应返回第一个提供商的结果
    assert result.provider is not None
    assert result.provider == providers[0].name

    print(f"比对模式测试完成")
    print(f"使用提供商: {result.provider}")
```

- [ ] **步骤 2: 运行端到端测试**

```bash
pytest tests/integration/test_fallback_e2e.py -v
```

预期: PASS（需要真实 API Key）

- [ ] **步骤 3: 提交**

```bash
git add tests/integration/test_fallback_e2e.py
git commit -m "feat: 添加回退机制端到端测试"
```

---

### 任务 5: 运行所有测试验证第三阶段完成

- [ ] **步骤 1: 运行所有测试**

```bash
pytest tests/ -v --tb=short
```

预期: 所有测试 PASS

- [ ] **步骤 2: 最终提交**

```bash
git status
git add -A
git commit -m "feat: 第三阶段完成 - 执行策略、参数适配、回退机制"
```

---

## 第三阶段完成检查清单

完成本阶段后，项目应具备：

- [x] ProviderFactory：根据配置创建提供商实例
- [x] ParameterAdapter：统一请求转换为提供商请求
- [x] ExecutionStrategy：正常模式（串行回退）和比对模式（串行执行第一个）
- [x] 回退机制：提供商失败时自动切换到下一个
- [x] 比对模式日志：后台线程记录其他提供商执行结果