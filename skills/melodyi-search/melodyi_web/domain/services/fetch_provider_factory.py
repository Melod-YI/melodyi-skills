"""Fetch 供应商工厂

根据配置创建 Fetch 供应商实例。
"""

from typing import List, Type
from melodyi_web.domain.models.fetch_provider_config import FetchProviderConfig
from melodyi_web.providers.fetch.base_fetch_provider import BaseFetchProvider
from melodyi_web.providers.fetch.jina_reader_provider import JinaReaderProvider
from melodyi_web.providers.fetch.markdown_new_provider import MarkdownNewProvider
from melodyi_web.providers.fetch.tavily_extract_provider import TavilyExtractProvider
from melodyi_web.providers.fetch.exa_contents_provider import ExaContentsProvider


class FetchProviderFactory:
    """Fetch 供应商工厂

    根据配置创建 Fetch 供应商实例。支持的供应商类型：
    - jina-reader: Jina Reader 供应商（无需 API Key）
    - markdown-new: Markdown.new 供应商（无需 API Key）
    - tavily-extract: Tavily Extract 供应商（需要 API Key）
    - exa-contents: Exa Contents 供应商（需要 API Key）
    """

    _PROVIDER_MAP: dict[str, Type[BaseFetchProvider]] = {
        "jina-reader": JinaReaderProvider,
        "markdown-new": MarkdownNewProvider,
        "tavily-extract": TavilyExtractProvider,
        "exa-contents": ExaContentsProvider,
    }

    @classmethod
    def create(cls, config: FetchProviderConfig) -> BaseFetchProvider:
        """创建单个供应商实例

        Args:
            config: 供应商配置

        Returns:
            供应商实例

        Raises:
            ValueError: 不支持的供应商名称
        """
        provider_name = config.name

        if provider_name not in cls._PROVIDER_MAP:
            raise ValueError(f"不支持的 Fetch 供应商: {provider_name}")

        extra_params = config.extra_params or {}

        if provider_name == "jina-reader":
            return JinaReaderProvider(
                api_key=config.api_key,
                api_url=config.host,
                timeout_ms=config.timeout_ms,
            )
        elif provider_name == "markdown-new":
            return MarkdownNewProvider(
                api_url=config.host,
                timeout_ms=config.timeout_ms,
            )
        elif provider_name == "tavily-extract":
            extract_depth = extra_params.get("extract_depth", "basic")
            return TavilyExtractProvider(
                api_key=config.api_key or "",
                api_url=config.host,
                timeout_ms=config.timeout_ms,
                extract_depth=extract_depth,
            )
        elif provider_name == "exa-contents":
            return ExaContentsProvider(
                api_key=config.api_key or "",
                api_url=config.host,
                timeout_ms=config.timeout_ms,
            )
        else:
            raise ValueError(f"不支持的 Fetch 供应商: {provider_name}")

    @classmethod
    def create_all(cls, configs: List[FetchProviderConfig]) -> List[BaseFetchProvider]:
        """创建多个供应商实例

        Args:
            configs: 供应商配置列表

        Returns:
            供应商实例列表
        """
        providers = []
        for config in configs:
            providers.append(cls.create(config))
        return providers

    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """获取支持的供应商名称列表

        Returns:
            支持的供应商名称列表
        """
        return list(cls._PROVIDER_MAP.keys())