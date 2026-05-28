"""ProviderFactory 单元测试"""

import pytest
from melodyi_web.domain.models.provider_config import ProviderConfig
from melodyi_web.domain.services.provider_factory import ProviderFactory
from melodyi_web.providers.search.minimax_cn_provider import MiniMaxCNProvider
from melodyi_web.providers.search.tavily_provider import TavilyProvider
from melodyi_web.providers.search.brave_provider import BraveProvider
from melodyi_web.providers.search.exa_provider import ExaProvider
from melodyi_web.providers.search.searxng_provider import SearXNGProvider
from melodyi_web.providers.search.firecrawl_provider import FirecrawlProvider


class TestProviderFactory:
    """ProviderFactory 测试类"""

    def test_create_minimax_cn_provider(self):
        """测试创建 MiniMax-CN 提供商"""
        config = ProviderConfig(
            name="minimax-cn",
            api_key="test-api-key",
            host="https://custom.api.minimaxi.com",
            timeout_ms=5000,
            max_results=5,
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, MiniMaxCNProvider)
        assert provider.api_key == "test-api-key"
        assert provider.api_host == "https://custom.api.minimaxi.com"
        assert provider.timeout_ms == 5000
        assert provider.max_results == 5

    def test_create_tavily_provider(self):
        """测试创建 Tavily 提供商"""
        config = ProviderConfig(
            name="tavily",
            api_key="tvly-test-key",
            host="https://custom.tavily.com/search",
            timeout_ms=8000,
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, TavilyProvider)
        assert provider.api_key == "tvly-test-key"
        assert provider.api_url == "https://custom.tavily.com/search"
        assert provider.timeout_ms == 8000
        assert provider.default_depth == "basic"

    def test_create_tavily_with_depth(self):
        """测试创建 Tavily 提供商并指定搜索深度（使用 depth 参数）"""
        config = ProviderConfig(
            name="tavily",
            api_key="tvly-test-key",
            extra_params={"depth": "advanced"},
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, TavilyProvider)
        assert provider.default_depth == "advanced"

    def test_create_tavily_with_search_depth(self):
        """测试创建 Tavily 提供商并指定搜索深度（使用 search_depth 参数）"""
        config = ProviderConfig(
            name="tavily",
            api_key="tvly-test-key",
            extra_params={"search_depth": "advanced"},
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, TavilyProvider)
        assert provider.default_depth == "advanced"

    def test_create_brave_provider(self):
        """测试创建 Brave 提供商"""
        config = ProviderConfig(
            name="brave",
            api_key="brave-test-key",
            host="https://custom.brave.com/api",
            timeout_ms=6000,
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, BraveProvider)
        assert provider.api_key == "brave-test-key"
        assert provider.api_url == "https://custom.brave.com/api"
        assert provider.timeout_ms == 6000

    def test_create_exa_provider(self):
        """测试创建 Exa 提供商"""
        config = ProviderConfig(
            name="exa",
            api_key="exa-test-key",
            host="https://custom.exa.ai/search",
            timeout_ms=15000,
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, ExaProvider)
        assert provider.api_key == "exa-test-key"
        assert provider.api_url == "https://custom.exa.ai/search"
        assert provider.timeout_ms == 15000
        assert provider.default_type == "auto"

    def test_create_searxng_provider(self):
        """测试创建 SearXNG 提供商"""
        config = ProviderConfig(
            name="searxng",
            host="http://localhost:8888",
            timeout_ms=10000,
            max_results=15,
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, SearXNGProvider)
        assert provider.host == "http://localhost:8888"
        assert provider.timeout_ms == 10000
        assert provider.max_results == 15

    def test_create_searxng_with_api_key(self):
        """测试创建 SearXNG 提供商并指定 API key"""
        config = ProviderConfig(
            name="searxng",
            host="http://localhost:8888",
            api_key="searxng-key",
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, SearXNGProvider)
        assert provider.api_key == "searxng-key"

    def test_create_exa_with_type(self):
        """测试创建 Exa 提供商并指定搜索类型（使用 type 参数）"""
        config = ProviderConfig(
            name="exa",
            api_key="exa-test-key",
            extra_params={"type": "neural"},
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, ExaProvider)
        assert provider.default_type == "neural"

    def test_create_exa_with_search_type(self):
        """测试创建 Exa 提供商并指定搜索类型（使用 search_type 参数）"""
        config = ProviderConfig(
            name="exa",
            api_key="exa-test-key",
            extra_params={"search_type": "keyword"},
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, ExaProvider)
        assert provider.default_type == "keyword"

    def test_create_all_multiple_providers(self):
        """测试创建多个提供商"""
        configs = [
            ProviderConfig(name="minimax-cn", api_key="key1"),
            ProviderConfig(name="tavily", api_key="key2"),
            ProviderConfig(name="brave", api_key="key3"),
            ProviderConfig(name="exa", api_key="key4"),
        ]

        providers = ProviderFactory.create_all(configs)

        assert len(providers) == 4
        assert isinstance(providers[0], MiniMaxCNProvider)
        assert isinstance(providers[1], TavilyProvider)
        assert isinstance(providers[2], BraveProvider)
        assert isinstance(providers[3], ExaProvider)

    def test_create_all_empty_list(self):
        """测试创建空提供商列表"""
        providers = ProviderFactory.create_all([])
        assert providers == []

    def test_create_firecrawl_provider(self):
        """测试创建 Firecrawl 提供商"""
        config = ProviderConfig(
            name="firecrawl",
            api_key="firecrawl-test-key",
            host="https://firecrawl.example.com/v1/search",
            timeout_ms=12000,
            max_results=8,
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, FirecrawlProvider)
        assert provider.api_key == "firecrawl-test-key"
        assert provider.api_url == "https://firecrawl.example.com/v1/search"
        assert provider.timeout_ms == 12000
        assert provider.max_results == 8

    def test_create_firecrawl_provider_default_url(self):
        """测试创建 Firecrawl 提供商使用默认 URL"""
        config = ProviderConfig(
            name="firecrawl",
            api_key="firecrawl-test-key",
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, FirecrawlProvider)
        assert provider.api_url == FirecrawlProvider.DEFAULT_API_URL

    def test_get_supported_providers(self):
        """测试获取支持的提供商列表"""
        providers = ProviderFactory.get_supported_providers()

        assert "minimax-cn" in providers
        assert "tavily" in providers
        assert "brave" in providers
        assert "exa" in providers
        assert "searxng" in providers
        assert "firecrawl" in providers
        assert len(providers) == 6

    def test_create_with_default_values(self):
        """测试使用默认值创建提供商"""
        config = ProviderConfig(
            name="tavily",
            api_key="test-key",
            # 不指定 host, timeout_ms, max_results
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, TavilyProvider)
        assert provider.api_key == "test-key"
        assert provider.api_url == TavilyProvider.DEFAULT_API_URL
        assert provider.timeout_ms == 10000  # ProviderConfig 默认值
        assert provider.default_depth == "basic"  # Tavily 默认值

    def test_create_with_none_extra_params(self):
        """测试 extra_params 为 None 时的处理"""
        config = ProviderConfig(
            name="exa",
            api_key="test-key",
            extra_params=None,
        )

        provider = ProviderFactory.create(config)

        assert isinstance(provider, ExaProvider)
        assert provider.default_type == "auto"  # 使用默认值

    def test_create_minimax_cn_provider_name(self):
        """测试 MiniMax-CN 提供商的 name 属性"""
        config = ProviderConfig(name="minimax-cn", api_key="test-key")
        provider = ProviderFactory.create(config)

        assert provider.name == "minimax-cn"

    def test_create_tavily_provider_name(self):
        """测试 Tavily 提供商的 name 属性"""
        config = ProviderConfig(name="tavily", api_key="test-key")
        provider = ProviderFactory.create(config)

        assert provider.name == "tavily"

    def test_create_brave_provider_name(self):
        """测试 Brave 提供商的 name 属性"""
        config = ProviderConfig(name="brave", api_key="test-key")
        provider = ProviderFactory.create(config)

        assert provider.name == "brave"

    def test_create_exa_provider_name(self):
        """测试 Exa 提供商的 name 属性"""
        config = ProviderConfig(name="exa", api_key="test-key")
        provider = ProviderFactory.create(config)

        assert provider.name == "exa"

    def test_create_searxng_provider_name(self):
        """测试 SearXNG 提供商的 name 属性"""
        config = ProviderConfig(name="searxng", host="http://localhost:8888")
        provider = ProviderFactory.create(config)

        assert provider.name == "searxng"

    def test_create_firecrawl_provider_name(self):
        """测试 Firecrawl 提供商的 name 属性"""
        config = ProviderConfig(name="firecrawl", api_key="test-key")
        provider = ProviderFactory.create(config)

        assert provider.name == "firecrawl"