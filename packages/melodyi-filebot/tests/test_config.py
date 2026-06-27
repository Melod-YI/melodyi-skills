"""config 读取测试"""

import os
from unittest.mock import patch

from melodyi_filebot import config


class TestLoadTmdbApiKey:
    """load_tmdb_api_key 测试"""

    def test_from_env(self):
        """环境变量优先"""
        with patch.dict(os.environ, {"TMDB_API_KEY": "env_key_123"}):
            assert config.load_tmdb_api_key() == "env_key_123"

    def test_env_strips_whitespace(self):
        """环境变量去除空白"""
        with patch.dict(os.environ, {"TMDB_API_KEY": "  key  "}):
            assert config.load_tmdb_api_key() == "key"

    def test_env_overrides_config_file(self, tmp_path, monkeypatch):
        """环境变量优先于配置文件"""
        cfg = tmp_path / "config.yaml"
        cfg.write_text("tmdb_api_key: file_key\n", encoding="utf-8")
        monkeypatch.setattr(config, "CONFIG_PATH", cfg)
        with patch.dict(os.environ, {"TMDB_API_KEY": "env_key"}, clear=False):
            assert config.load_tmdb_api_key() == "env_key"

    def test_from_config_file(self, tmp_path, monkeypatch):
        """配置文件兜底"""
        cfg = tmp_path / "config.yaml"
        cfg.write_text("tmdb_api_key: file_key\n", encoding="utf-8")
        monkeypatch.setattr(config, "CONFIG_PATH", cfg)
        with patch.dict(os.environ, {}, clear=True):
            assert config.load_tmdb_api_key() == "file_key"

    def test_returns_none_when_missing(self, tmp_path, monkeypatch):
        """未配置返回 None"""
        monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "nope.yaml")
        with patch.dict(os.environ, {}, clear=True):
            assert config.load_tmdb_api_key() is None


class TestConfigDirs:
    """配置/数据目录常量测试"""

    def test_config_dir_is_user_home(self):
        from pathlib import Path
        from melodyi_filebot import config
        assert config.CONFIG_DIR == Path.home() / ".melodyi-skills" / "melodyi-filebot"

    def test_config_path_under_config_dir(self):
        from melodyi_filebot import config
        assert config.CONFIG_PATH == config.CONFIG_DIR / "config.yaml"

    def test_snapshots_dir_under_config_dir(self):
        from melodyi_filebot import config
        assert config.SNAPSHOTS_DIR == config.CONFIG_DIR / "snapshots"
