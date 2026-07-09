import json
import os
from pathlib import Path
import pytest
from config import load_config


@pytest.fixture
def no_config_file(monkeypatch):
    """模拟不存在任何配置文件，隔离项目自带示例与用户目录配置。"""
    monkeypatch.setattr("config._find_config_file", lambda cli_path=None: None)


class TestConfigDefaults:
    def test_defaults_with_api_key_from_env(self, monkeypatch, no_config_file):
        monkeypatch.setenv("VISION_API_KEY", "test-key-123")
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        config = load_config()
        assert config.api_key == "test-key-123"
        assert config.api_base == "https://api.openai.com/v1"
        assert config.model == "gpt-4o"
        assert config.max_tokens == 1024
        assert config.provider == "openai"

    def test_missing_api_key_raises_error(self, monkeypatch, no_config_file):
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        with pytest.raises(SystemExit):
            load_config()


class TestConfigFile:
    def test_loads_values_from_config_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "api_key": "file-key",
            "model": "gpt-4o-mini",
            "max_tokens": 512
        }))
        config = load_config(config_path=str(config_file))
        assert config.api_key == "file-key"
        assert config.model == "gpt-4o-mini"
        assert config.max_tokens == 512
        assert config.api_base == "https://api.openai.com/v1"


class TestEnvVarOverride:
    def test_env_var_overrides_config_file(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "api_key": "file-key",
            "model": "gpt-4o-mini"
        }))
        monkeypatch.setenv("VISION_API_KEY", "env-key")
        monkeypatch.setenv("VISION_MODEL", "gpt-4o")
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        config = load_config(config_path=str(config_file))
        assert config.api_key == "env-key"
        assert config.model == "gpt-4o"


class TestCliOverride:
    def test_cli_overrides_take_highest_priority(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "api_key": "file-key",
            "model": "gpt-4o-mini"
        }))
        monkeypatch.setenv("VISION_API_KEY", "env-key")
        monkeypatch.setenv("VISION_MODEL", "env-model")
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        config = load_config(
            cli_overrides={"model": "cli-model", "api_key": "cli-key"},
            config_path=str(config_file),
        )
        assert config.api_key == "cli-key"
        assert config.model == "cli-model"

    def test_none_cli_overrides_are_ignored(self, monkeypatch, no_config_file):
        monkeypatch.setenv("VISION_API_KEY", "env-key")
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        config = load_config(cli_overrides={"model": None, "max_tokens": None})
        assert config.model == "gpt-4o"


class TestConfigFileLocation:
    """配置文件查找必须不依赖执行位置（cwd），路径相对脚本或用户主目录固定。"""

    def test_user_config_dir_matches_convention(self):
        """用户配置目录应为 ~/.melodyi-skills/melodyi-vision（与其他 melodyi skill 一致）。"""
        from config import USER_CONFIG_DIR

        assert USER_CONFIG_DIR == Path.home() / ".melodyi-skills" / "melodyi-vision"

    def test_user_config_takes_precedence_over_bundled_example(
        self, tmp_path, monkeypatch
    ):
        """用户目录配置应优先于项目自带示例，避免占位 key 屏蔽真实 key。"""
        user_cfg = tmp_path / "user.json"
        user_cfg.write_text(json.dumps({"api_key": "real-user-key"}))
        bundled_cfg = tmp_path / "bundled.json"
        bundled_cfg.write_text(json.dumps({"api_key": "placeholder"}))
        monkeypatch.setattr(
            "config._config_search_paths",
            lambda cli_path=None: [user_cfg, bundled_cfg],
        )
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        config = load_config()
        assert config.api_key == "real-user-key"

    def test_script_dir_config_found_independent_of_cwd(
        self, tmp_path, monkeypatch
    ):
        """在任意 cwd 下执行，都应通过脚本相对路径找到配置，而非 cwd。"""
        cfg = tmp_path / "config.json"
        cfg.write_text(
            json.dumps({"api_key": "located-without-cwd"})
        )
        # 切到与配置无关的目录执行
        other = tmp_path / "elsewhere"
        other.mkdir()
        monkeypatch.chdir(other)
        # 模拟查找链命中该配置（脚本同目录 / 用户目录均不依赖 cwd）
        monkeypatch.setattr(
            "config._config_search_paths", lambda cli_path=None: [cfg]
        )
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        config = load_config()
        assert config.api_key == "located-without-cwd"

