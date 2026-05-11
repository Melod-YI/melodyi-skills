"""配置加载器测试"""

import pytest
import tempfile
import os
from melodyi_web.infrastructure.config.config_loader import load_config, resolve_env_var


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
            temp_path = f.name
        try:
            config = load_config(temp_path)
        finally:
            os.unlink(temp_path)

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
            temp_path = f.name
        try:
            config = load_config(temp_path)
        finally:
            os.unlink(temp_path)
        del os.environ["MY_API_KEY"]

        assert config.providers[0].api_key == "env-value"

    def test_load_default_config(self):
        """测试加载默认配置"""
        config = load_config()
        assert config is not None
        assert len(config.providers) > 0