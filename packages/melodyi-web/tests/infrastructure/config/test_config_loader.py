"""配置加载器测试"""

import pytest
import tempfile
import os
from pathlib import Path
from melodyi_web.infrastructure.config.config_loader import load_config, resolve_env_var, USER_CONFIG_DIR, USER_CONFIG_FILE


class TestConfigDirs:
    """配置目录常量测试"""

    def test_user_config_dir_matches_convention(self):
        """用户配置目录应为 ~/.melodyi-skills/melodyi-web（与其他 melodyi skill 一致）。"""
        assert USER_CONFIG_DIR == Path.home() / ".melodyi-skills" / "melodyi-web"

    def test_user_config_file_under_config_dir(self):
        assert USER_CONFIG_FILE == USER_CONFIG_DIR / "config.yaml"


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
        """测试加载 yaml 配置（使用 search_providers）"""
        yaml_content = """
search_providers:
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

        assert len(config.search_providers) == 1
        assert config.search_providers[0].name == "minimax-cn"
        assert config.search_providers[0].timeout_ms == 5000

    def test_load_yaml_config_backward_compat(self):
        """测试加载 yaml 配置（旧 providers 字段名）"""
        yaml_content = """
providers:
  - name: minimax-cn
    api_key: test-key
    timeout_ms: 5000
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        try:
            config = load_config(temp_path)
        finally:
            os.unlink(temp_path)

        # providers 迁移到 search_providers
        assert len(config.search_providers) == 1
        assert config.search_providers[0].name == "minimax-cn"

    def test_load_config_with_env_var(self):
        """测试加载配置并解析环境变量"""
        os.environ["MY_API_KEY"] = "env-value"
        yaml_content = """
search_providers:
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

        assert config.search_providers[0].api_key == "env-value"

    def test_load_default_config(self, monkeypatch, tmp_path):
        """测试加载内置默认配置（无配置文件时）"""
        # 隔离真实用户配置：将查找路径指向不存在的文件，强制走内置默认
        monkeypatch.setattr(
            "melodyi_web.infrastructure.config.config_loader.USER_CONFIG_FILE",
            tmp_path / "nonexistent.yaml",
        )
        config = load_config()
        assert config is not None
        # Search providers 需用户配置，默认为空
        assert config.search_providers == []
        # Fetch providers 有内置默认值
        assert len(config.fetch_providers) == 2
        assert config.fetch_providers[0].name == "jina"
        assert config.fetch_providers[1].name == "markdown-new"


class TestDatabaseConfigDefault:
    """DatabaseConfig 默认路径测试"""

    def test_default_database_path_in_user_dir(self):
        """DatabaseConfig 默认路径应落在用户目录下，而非相对的 ./data/compare.db。

        回归保护：之前 schema 默认是相对路径 ./data/compare.db，当 config.yaml
        缺少 database 段时会把 db 创建到 CWD（仓库内）。修复后应为绝对路径。
        """
        from melodyi_web.infrastructure.config.config_schema import DatabaseConfig

        expected = str(Path.home() / ".melodyi-skills" / "melodyi-web" / "data" / "compare.db")
        assert DatabaseConfig().database_path == expected
        # 必须是绝对路径，不能是相对路径
        assert Path(DatabaseConfig().database_path).is_absolute()

    def test_yaml_without_database_section_uses_user_dir(self, tmp_path):
        """config.yaml 缺少 database 段时，应回退到用户目录下的绝对路径。"""
        yaml_content = """
search_providers: []
mode:
  comparison: false
"""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml_content, encoding="utf-8")
        config = load_config(str(cfg_file))
        expected = str(Path.home() / ".melodyi-skills" / "melodyi-web" / "data" / "compare.db")
        assert config.database.database_path == expected