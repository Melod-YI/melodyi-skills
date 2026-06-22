import json
import os
import pytest
from config import load_config


class TestConfigDefaults:
    def test_defaults_with_api_key_from_env(self, monkeypatch):
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

    def test_missing_api_key_raises_error(self, monkeypatch):
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

    def test_none_cli_overrides_are_ignored(self, monkeypatch):
        monkeypatch.setenv("VISION_API_KEY", "env-key")
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        config = load_config(cli_overrides={"model": None, "max_tokens": None})
        assert config.model == "gpt-4o"
