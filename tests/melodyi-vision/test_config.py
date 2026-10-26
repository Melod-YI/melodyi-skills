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
        monkeypatch.delenv("VISION_STREAM", raising=False)
        config = load_config()
        assert config.api_key == "test-key-123"
        assert config.api_base == "https://api.openai.com/v1"
        assert config.model == "gpt-4o"
        assert config.max_tokens == 1024
        assert config.provider == "openai"
        assert config.stream is True

    def test_missing_api_key_raises_error(self, monkeypatch, no_config_file):
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        monkeypatch.delenv("VISION_STREAM", raising=False)
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
        monkeypatch.delenv("VISION_STREAM", raising=False)
        config = load_config(cli_overrides={"model": None, "max_tokens": None})
        assert config.model == "gpt-4o"


class TestStreamConfig:
    """流式开关 stream：默认 True，可经配置文件/环境变量/CLI 关闭。"""

    def test_default_stream_is_true(self, monkeypatch, no_config_file):
        monkeypatch.setenv("VISION_API_KEY", "k")
        monkeypatch.delenv("VISION_STREAM", raising=False)
        assert load_config().stream is True

    def test_config_file_bool_false_disables_stream(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        monkeypatch.delenv("VISION_STREAM", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"api_key": "k", "stream": False}))
        assert load_config(config_path=str(cfg)).stream is False

    def test_config_file_string_false_is_coerced(self, tmp_path, monkeypatch):
        """配置文件把 stream 写成字符串时也应被归一为布尔。"""
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        monkeypatch.delenv("VISION_STREAM", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"api_key": "k", "stream": "false"}))
        assert load_config(config_path=str(cfg)).stream is False

    def test_env_var_disables_stream(self, monkeypatch, no_config_file):
        monkeypatch.setenv("VISION_API_KEY", "k")
        monkeypatch.setenv("VISION_STREAM", "false")
        assert load_config().stream is False

    def test_env_var_overrides_config_file_stream(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"api_key": "k", "stream": False}))
        monkeypatch.setenv("VISION_STREAM", "true")
        assert load_config(config_path=str(cfg)).stream is True

    def test_cli_override_overrides_env_stream(self, monkeypatch, no_config_file):
        monkeypatch.setenv("VISION_API_KEY", "k")
        monkeypatch.setenv("VISION_STREAM", "false")
        assert load_config(cli_overrides={"stream": True}).stream is True

    def test_none_cli_override_keeps_env_stream(self, monkeypatch, no_config_file):
        monkeypatch.setenv("VISION_API_KEY", "k")
        monkeypatch.setenv("VISION_STREAM", "false")
        assert load_config(cli_overrides={"stream": None}).stream is False


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



class TestMultiProviderConfig:
    """多供应商配置：providers 映射 + active_provider 切换。"""

    def test_switch_by_active_provider(self, tmp_path, monkeypatch):
        """改 active_provider 一个字段即切换供应商。"""
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "active_provider": "openrouter",
            "providers": {
                "openrouter": {"api_key": "or-key", "api_base": "https://openrouter.ai/api/v1/", "model": "xiaomi/mimo-v2.5"},
                "openai": {"api_key": "oai-key", "api_base": "https://api.openai.com/v1", "model": "gpt-4o"},
            },
        }))
        config = load_config(config_path=str(cfg))
        assert config.api_key == "or-key"
        assert config.api_base == "https://openrouter.ai/api/v1/"
        assert config.model == "xiaomi/mimo-v2.5"
        assert config.active_provider == "openrouter"

        # 切换到 openai：只改 active_provider
        cfg.write_text(json.dumps({
            "active_provider": "openai",
            "providers": {
                "openrouter": {"api_key": "or-key", "api_base": "https://openrouter.ai/api/v1/", "model": "xiaomi/mimo-v2.5"},
                "openai": {"api_key": "oai-key", "api_base": "https://api.openai.com/v1", "model": "gpt-4o"},
            },
        }))
        config2 = load_config(config_path=str(cfg))
        assert config2.api_key == "oai-key"
        assert config2.model == "gpt-4o"
        assert config2.active_provider == "openai"

    def test_per_profile_max_tokens_override(self, tmp_path, monkeypatch):
        """profile 显式 max_tokens 覆盖顶层默认。"""
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "active_provider": "openrouter",
            "max_tokens": 4096,
            "providers": {
                "openrouter": {"api_key": "k", "api_base": "https://x", "model": "m", "max_tokens": 102400},
                "openai": {"api_key": "k2", "api_base": "https://y", "model": "gpt-4o"},
            },
        }))
        config = load_config(config_path=str(cfg))
        assert config.max_tokens == 102400

        # openai 未带 max_tokens，回退顶层 4096
        cfg.write_text(json.dumps({
            "active_provider": "openai",
            "max_tokens": 4096,
            "providers": {
                "openrouter": {"api_key": "k", "api_base": "https://x", "model": "m", "max_tokens": 102400},
                "openai": {"api_key": "k2", "api_base": "https://y", "model": "gpt-4o"},
            },
        }))
        config2 = load_config(config_path=str(cfg))
        assert config2.max_tokens == 4096

    def test_per_profile_stream_override(self, tmp_path, monkeypatch):
        """profile 显式 stream 覆盖顶层默认。"""
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "active_provider": "openai",
            "stream": True,
            "providers": {
                "openai": {"api_key": "k", "api_base": "https://y", "model": "gpt-4o", "stream": False},
            },
        }))
        config = load_config(config_path=str(cfg))
        assert config.stream is False

    def test_active_provider_not_in_providers_exits(self, tmp_path, monkeypatch):
        """active_provider 指向不存在的 profile 应报错退出。"""
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "active_provider": "nonexistent",
            "providers": {"openai": {"api_key": "k", "api_base": "https://y", "model": "gpt-4o"}},
        }))
        with pytest.raises(SystemExit):
            load_config(config_path=str(cfg))

    def test_providers_without_active_provider_exits(self, tmp_path, monkeypatch):
        """有 providers 但未指定 active_provider 应报错退出。"""
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "providers": {"openai": {"api_key": "k", "api_base": "https://y", "model": "gpt-4o"}},
        }))
        with pytest.raises(SystemExit):
            load_config(config_path=str(cfg))

    def test_flat_config_backward_compat(self, tmp_path, monkeypatch):
        """无 providers 段时回退扁平结构（向后兼容）。"""
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "api_key": "flat-key",
            "api_base": "https://api.openai.com/v1",
            "model": "gpt-4o",
        }))
        config = load_config(config_path=str(cfg))
        assert config.api_key == "flat-key"
        assert config.api_base == "https://api.openai.com/v1"
        assert config.model == "gpt-4o"
        assert config.active_provider is None


class TestVerifySslConfig:
    """SSL 校验开关：默认 True，可经配置文件/环境变量关闭。"""

    def test_default_verify_ssl_is_true(self, monkeypatch, no_config_file):
        monkeypatch.setenv("VISION_API_KEY", "k")
        monkeypatch.delenv("VISION_VERIFY_SSL", raising=False)
        assert load_config().verify_ssl is True

    def test_config_file_disables_verify_ssl(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        monkeypatch.delenv("VISION_VERIFY_SSL", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"api_key": "k", "verify_ssl": False}))
        assert load_config(config_path=str(cfg)).verify_ssl is False

    def test_config_file_string_false_is_coerced(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        monkeypatch.delenv("VISION_VERIFY_SSL", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"api_key": "k", "verify_ssl": "false"}))
        assert load_config(config_path=str(cfg)).verify_ssl is False

    def test_env_var_disables_verify_ssl(self, monkeypatch, no_config_file):
        monkeypatch.setenv("VISION_API_KEY", "k")
        monkeypatch.setenv("VISION_VERIFY_SSL", "false")
        assert load_config().verify_ssl is False

    def test_env_var_overrides_config_file_verify_ssl(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"api_key": "k", "verify_ssl": False}))
        monkeypatch.setenv("VISION_VERIFY_SSL", "true")
        assert load_config(config_path=str(cfg)).verify_ssl is True


class TestProxyConfig:
    """HTTP 代理配置：默认 None，可经配置文件设置；全局共享不 per-profile。"""

    def test_default_proxy_is_none(self, monkeypatch, no_config_file):
        monkeypatch.setenv("VISION_API_KEY", "k")
        assert load_config().proxy is None

    def test_config_file_sets_proxy(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "api_key": "k",
            "proxy": "http://127.0.0.1:7890",
        }))
        assert load_config(config_path=str(cfg)).proxy == "http://127.0.0.1:7890"

    def test_empty_string_proxy_normalized_to_none(self, tmp_path, monkeypatch):
        """空字符串/纯空白视作未配置（归一为 None）"""
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"api_key": "k", "proxy": "   "}))
        assert load_config(config_path=str(cfg)).proxy is None

    def test_proxy_in_known_whitelist(self, tmp_path, monkeypatch):
        """回归保护：proxy 必须在 known 白名单里，否则会被静默丢弃"""
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "api_key": "k",
            "proxy": "http://127.0.0.1:7890",
        }))
        config = load_config(config_path=str(cfg))
        assert config.proxy == "http://127.0.0.1:7890"
        assert hasattr(config, "proxy")

    def test_proxy_not_per_profile(self, tmp_path, monkeypatch):
        """profile 内的 proxy 不被读取：与 verify_ssl 一样全局共享"""
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "api_key": "k",
            "proxy": "http://global:7890",
            "active_provider": "p1",
            "providers": {
                "p1": {"api_key": "k1", "proxy": "http://profile:1"}
            },
        }))
        config = load_config(config_path=str(cfg))
        assert config.proxy == "http://global:7890"
