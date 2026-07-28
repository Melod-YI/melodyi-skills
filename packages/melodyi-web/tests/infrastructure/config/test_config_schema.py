"""Config 配置模型测试"""

from pathlib import Path
import pytest
from melodyi_web.infrastructure.config.config_schema import Config, ModeConfig, FallbackConfig, HttpConfig


class TestConfig:
    """Config 测试类"""

    def test_config_from_dict(self):
        """测试从字典创建配置（使用 search_providers）"""
        config_dict = {
            "search_providers": [
                {"name": "minimax-cn", "api_key": "key1"},
                {"name": "tavily", "api_key": "key2"},
            ],
            "mode": {"comparison": False},
            "fallback": {"retry_count": 2}
        }
        config = Config(**config_dict)
        assert len(config.search_providers) == 2
        assert config.search_providers[0].name == "minimax-cn"
        assert config.mode.comparison is False
        assert config.fallback.retry_count == 2

    def test_config_backward_compatibility(self):
        """测试 providers 字段向后兼容"""
        config_dict = {
            "providers": [
                {"name": "minimax-cn", "api_key": "key1"},
                {"name": "tavily", "api_key": "key2"},
            ],
        }
        config = Config(**config_dict)
        # providers 字段值迁移到 search_providers
        assert len(config.search_providers) == 2
        assert config.search_providers[0].name == "minimax-cn"

    def test_mode_config_defaults(self):
        """测试 ModeConfig 默认值"""
        mode = ModeConfig()
        assert mode.comparison is False
        # 默认日志目录落在用户目录下（绝对路径），避免落到 CWD
        assert mode.log_dir == str(
            Path.home() / ".melodyi-skills" / "melodyi-web" / "logs"
        )

    def test_fallback_config_defaults(self):
        """测试 FallbackConfig 默认值"""
        fallback = FallbackConfig()
        assert fallback.retry_count == 2
        assert fallback.retry_delay_ms == 1000

    def test_http_config_default_verify_ssl(self):
        """测试 HttpConfig 默认校验 SSL

        回归保护：默认必须为 True（校验 SSL），仅在显式配置时关闭。
        """
        http = HttpConfig()
        assert http.verify_ssl is True

    def test_http_config_disable_verify_ssl(self):
        """测试 HttpConfig 显式关闭 SSL 校验"""
        http = HttpConfig(verify_ssl=False)
        assert http.verify_ssl is False

    def test_config_http_default(self):
        """测试 Config 默认带 http 配置且默认校验 SSL"""
        config = Config()
        assert config.http.verify_ssl is True

    def test_config_http_from_dict(self):
        """测试从字典加载 http 配置（关闭 SSL 校验）"""
        config = Config(**{"http": {"verify_ssl": False}})
        assert config.http.verify_ssl is False

    def test_providers_order_preserved(self):
        """测试供应商顺序保留"""
        config_dict = {
            "search_providers": [
                {"name": "brave"},
                {"name": "tavily"},
                {"name": "minimax-cn"},
            ]
        }
        config = Config(**config_dict)
        assert config.search_providers[0].name == "brave"
        assert config.search_providers[1].name == "tavily"
        assert config.search_providers[2].name == "minimax-cn"

    def test_get_provider_names(self):
        """测试获取供应商名称列表"""
        config_dict = {
            "search_providers": [
                {"name": "minimax-cn"},
                {"name": "tavily"},
            ]
        }
        config = Config(**config_dict)
        names = config.get_search_provider_names()
        assert names == ["minimax-cn", "tavily"]

    def test_get_provider_by_name(self):
        """测试根据名称获取供应商配置"""
        config_dict = {
            "search_providers": [
                {"name": "minimax-cn", "api_key": "key"},
                {"name": "tavily"},
            ]
        }
        config = Config(**config_dict)
        provider = config.get_search_provider_by_name("minimax-cn")
        assert provider is not None
        assert provider.api_key == "key"

        provider = config.get_search_provider_by_name("unknown")
        assert provider is None