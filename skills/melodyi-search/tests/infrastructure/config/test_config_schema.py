"""Config 配置模型测试"""

import pytest
from melodyi_search.infrastructure.config.config_schema import Config, ModeConfig, FallbackConfig


class TestConfig:
    """Config 测试类"""

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

    def test_get_provider_names(self):
        """测试获取提供商名称列表"""
        config_dict = {
            "providers": [
                {"name": "minimax-cn"},
                {"name": "tavily"},
            ]
        }
        config = Config(**config_dict)
        names = config.get_provider_names()
        assert names == ["minimax-cn", "tavily"]

    def test_get_provider_by_name(self):
        """测试根据名称获取提供商配置"""
        config_dict = {
            "providers": [
                {"name": "minimax-cn", "api_key": "key"},
                {"name": "tavily"},
            ]
        }
        config = Config(**config_dict)
        provider = config.get_provider_by_name("minimax-cn")
        assert provider is not None
        assert provider.api_key == "key"

        provider = config.get_provider_by_name("unknown")
        assert provider is None