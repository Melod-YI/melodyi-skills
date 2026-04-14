"""提供商工厂

根据配置创建提供商实例。
"""

from typing import List, Type
from melodyi_search.domain.models.provider_config import ProviderConfig
from melodyi_search.providers.base_provider import BaseProvider
from melodyi_search.providers.minimax_cn_provider import MiniMaxCNProvider
from melodyi_search.providers.tavily_provider import TavilyProvider
from melodyi_search.providers.brave_provider import BraveProvider
from melodyi_search.providers.exa_provider import ExaProvider


class ProviderFactory:
    """提供商工厂

    根据配置创建提供商实例。支持的提供商类型：
    - minimax-cn: MiniMax CN 提供商
    - tavily: Tavily 提供商
    - brave: Brave 提供商
    - exa: Exa 提供商
    """

    # 提供商名称到类的映射
    _PROVIDER_MAP: dict[str, Type[BaseProvider]] = {
        "minimax-cn": MiniMaxCNProvider,
        "tavily": TavilyProvider,
        "brave": BraveProvider,
        "exa": ExaProvider,
    }

    @classmethod
    def create(cls, config: ProviderConfig) -> BaseProvider:
        """创建单个提供商实例

        Args:
            config: 提供商配置

        Returns:
            提供商实例

        Raises:
            ValueError: 不支持的提供商名称或缺少必要配置
        """
        provider_name = config.name

        if provider_name not in cls._PROVIDER_MAP:
            raise ValueError(f"不支持的提供商: {provider_name}")

        provider_class = cls._PROVIDER_MAP[provider_name]
        extra_params = config.extra_params or {}

        # 创建提供商实例，根据不同类型处理不同参数
        if provider_name == "minimax-cn":
            return cls._create_minimax_cn(config, extra_params)
        elif provider_name == "tavily":
            return cls._create_tavily(config, extra_params)
        elif provider_name == "brave":
            return cls._create_brave(config, extra_params)
        elif provider_name == "exa":
            return cls._create_exa(config, extra_params)
        else:
            # This should never happen due to the check above
            raise ValueError(f"不支持的提供商: {provider_name}")

    @classmethod
    def create_all(cls, configs: List[ProviderConfig]) -> List[BaseProvider]:
        """创建多个提供商实例

        Args:
            configs: 提供商配置列表

        Returns:
            提供商实例列表

        Raises:
            ValueError: 任何配置包含不支持的提供商名称
        """
        providers = []
        for config in configs:
            providers.append(cls.create(config))
        return providers

    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """获取支持的提供商名称列表

        Returns:
            支持的提供商名称列表
        """
        return list(cls._PROVIDER_MAP.keys())

    @classmethod
    def _create_minimax_cn(
        cls, config: ProviderConfig, extra_params: dict
    ) -> MiniMaxCNProvider:
        """创建 MiniMax-CN 提供商

        Args:
            config: 提供商配置
            extra_params: 额外参数

        Returns:
            MiniMaxCNProvider 实例
        """
        return MiniMaxCNProvider(
            api_key=config.api_key or "",
            api_host=config.host,
            timeout_ms=config.timeout_ms,
            max_results=config.max_results,
            model=extra_params.get("model"),
        )

    @classmethod
    def _create_tavily(
        cls, config: ProviderConfig, extra_params: dict
    ) -> TavilyProvider:
        """创建 Tavily 提供商

        Args:
            config: 提供商配置
            extra_params: 额外参数

        Returns:
            TavilyProvider 实例
        """
        # 支持 depth 或 search_depth 参数名
        search_depth = extra_params.get("depth") or extra_params.get("search_depth", "basic")

        return TavilyProvider(
            api_key=config.api_key or "",
            api_url=config.host,
            timeout_ms=config.timeout_ms,
            search_depth=search_depth,
        )

    @classmethod
    def _create_brave(cls, config: ProviderConfig, extra_params: dict) -> BraveProvider:
        """创建 Brave 提供商

        Args:
            config: 提供商配置
            extra_params: 额外参数

        Returns:
            BraveProvider 实例
        """
        return BraveProvider(
            api_key=config.api_key or "",
            api_url=config.host,
            timeout_ms=config.timeout_ms,
        )

    @classmethod
    def _create_exa(cls, config: ProviderConfig, extra_params: dict) -> ExaProvider:
        """创建 Exa 提供商

        Args:
            config: 提供商配置
            extra_params: 额外参数

        Returns:
            ExaProvider 实例
        """
        # 支持 type 或 search_type 参数名
        search_type = extra_params.get("type") or extra_params.get("search_type", "auto")

        return ExaProvider(
            api_key=config.api_key or "",
            api_url=config.host,
            timeout_ms=config.timeout_ms,
            search_type=search_type,
        )