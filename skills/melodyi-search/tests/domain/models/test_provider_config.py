"""提供商配置测试"""

import pytest
from melodyi_web.domain.models.provider_config import ProviderConfig


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
        """测试 searxng 配置"""
        config = ProviderConfig(
            name="searxng",
            host="http://localhost:8888"
        )
        assert config.host == "http://localhost:8888"
        assert config.api_key is None  # 自托管不需要 api_key

    def test_name_required(self):
        """测试 name 必填"""
        with pytest.raises(Exception):  # ValidationError
            ProviderConfig(api_key="test")

    def test_valid_provider_names(self):
        """测试有效的提供商名称"""
        valid_names = ["minimax-cn", "tavily", "brave", "exa", "searxng", "firecrawl"]
        for name in valid_names:
            config = ProviderConfig(name=name)
            assert config.name == name

    def test_invalid_provider_name(self):
        """测试无效的提供商名称"""
        with pytest.raises(Exception):  # ValidationError
            ProviderConfig(name="invalid-provider")

    def test_is_self_hosted_method(self):
        """测试 is_self_hosted 方法"""
        # 自托管提供商
        config = ProviderConfig(name="searxng", host="http://localhost:8888")
        assert config.is_self_hosted() is True

        # 非自托管
        config = ProviderConfig(name="tavily", api_key="test")
        assert config.is_self_hosted() is False