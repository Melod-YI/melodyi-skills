"""huawei_cloud.config 配置读取测试"""

import json
import sys
from pathlib import Path

import pytest

# 将 script/ 加入模块搜索路径，使其可直接 import huawei_cloud
SCRIPT_DIR = Path(__file__).resolve().parents[1] / "script"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import config


@pytest.fixture
def clean_env(monkeypatch):
    """隔离环境变量，避免本机真实凭据干扰测试。"""
    monkeypatch.delenv("HUAWEI_USERNAME", raising=False)
    monkeypatch.delenv("HUAWEI_PASSWORD", raising=False)


class TestConfigDirs:
    """配置目录常量测试"""

    def test_user_config_dir_matches_convention(self):
        """用户配置目录应为 ~/.melodyi-skills/get-user-location（与其他 melodyi skill 一致）。"""
        assert config.USER_CONFIG_DIR == Path.home() / ".melodyi-skills" / "get-user-location"

    def test_user_config_file_under_config_dir(self):
        assert config.USER_CONFIG_FILE == config.USER_CONFIG_DIR / "config.json"


class TestLoadConfigFile:
    """load_config_file 测试"""

    def test_loads_valid_json(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text(
            json.dumps({"huawei_username": "alice", "huawei_password": "secret"}),
            encoding="utf-8",
        )
        data = config.load_config_file(str(cfg))
        assert data["huawei_username"] == "alice"
        assert data["huawei_password"] == "secret"

    def test_missing_file_returns_empty(self, tmp_path):
        assert config.load_config_file(str(tmp_path / "nope.json")) == {}

    def test_default_path_when_none(self, monkeypatch, tmp_path):
        """未传 config_path 时读取 USER_CONFIG_FILE。"""
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"huawei_username": "bob"}), encoding="utf-8")
        monkeypatch.setattr(config, "USER_CONFIG_FILE", cfg)
        assert config.load_config_file()["huawei_username"] == "bob"

    def test_invalid_json_returns_empty(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text("{not json", encoding="utf-8")
        assert config.load_config_file(str(cfg)) == {}

    def test_non_dict_json_returns_empty(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps(["a", "b"]), encoding="utf-8")
        assert config.load_config_file(str(cfg)) == {}


class TestResolveCredentials:
    """resolve_credentials 优先级测试：环境变量 > 配置文件"""

    def test_env_overrides_config_file(self, tmp_path, clean_env, monkeypatch):
        cfg = tmp_path / "config.json"
        cfg.write_text(
            json.dumps({"huawei_username": "file-user", "huawei_password": "file-pwd"}),
            encoding="utf-8",
        )
        monkeypatch.setenv("HUAWEI_USERNAME", "env-user")
        monkeypatch.setenv("HUAWEI_PASSWORD", "env-pwd")
        username, password = config.resolve_credentials(str(cfg))
        assert username == "env-user"
        assert password == "env-pwd"

    def test_falls_back_to_config_file(self, tmp_path, clean_env):
        cfg = tmp_path / "config.json"
        cfg.write_text(
            json.dumps({"huawei_username": "file-user", "huawei_password": "file-pwd"}),
            encoding="utf-8",
        )
        username, password = config.resolve_credentials(str(cfg))
        assert username == "file-user"
        assert password == "file-pwd"

    def test_env_username_with_file_password(self, tmp_path, clean_env, monkeypatch):
        """单边覆盖：env 提供用户名，文件提供密码"""
        cfg = tmp_path / "config.json"
        cfg.write_text(
            json.dumps({"huawei_username": "file-user", "huawei_password": "file-pwd"}),
            encoding="utf-8",
        )
        monkeypatch.setenv("HUAWEI_USERNAME", "env-user")
        username, password = config.resolve_credentials(str(cfg))
        assert username == "env-user"
        assert password == "file-pwd"

    def test_returns_none_when_both_missing(self, tmp_path, clean_env):
        username, password = config.resolve_credentials(str(tmp_path / "nope.json"))
        assert username is None
        assert password is None


class TestValidateCredentials:
    """validate_credentials 测试"""

    def test_no_missing_when_configured(self, tmp_path, clean_env):
        cfg = tmp_path / "config.json"
        cfg.write_text(
            json.dumps({"huawei_username": "u", "huawei_password": "p"}),
            encoding="utf-8",
        )
        assert config.validate_credentials(str(cfg)) == []

    def test_reports_both_missing(self, tmp_path, clean_env):
        missing = config.validate_credentials(str(tmp_path / "nope.json"))
        assert len(missing) == 2

    def test_reports_only_password_missing(self, tmp_path, clean_env, monkeypatch):
        monkeypatch.setenv("HUAWEI_USERNAME", "env-user")
        missing = config.validate_credentials(str(tmp_path / "nope.json"))
        assert len(missing) == 1
        assert "HUAWEI_PASSWORD" in missing[0]


class TestParseArgs:
    """parse_args CLI 参数测试"""

    def test_config_option_parsed(self):
        args = config.parse_args(["--config", "/tmp/my.json"])
        assert args.config == "/tmp/my.json"

    def test_config_defaults_none(self):
        args = config.parse_args([])
        assert args.config is None

    def test_output_normalized(self):
        args = config.parse_args(["--output", r"C:\some\dir\\"])
        assert args.output == "C:/some/dir"


class TestBuildConfig:
    """build_config 测试"""

    def test_builds_from_env(self, clean_env, monkeypatch):
        monkeypatch.setenv("HUAWEI_USERNAME", "env-user")
        monkeypatch.setenv("HUAWEI_PASSWORD", "env-pwd")
        args = config.parse_args([])
        cfg = config.build_config(args=args)
        assert cfg.username == "env-user"
        assert cfg.password == "env-pwd"
        assert cfg.headed is False

    def test_builds_from_config_file(self, tmp_path, clean_env):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(
            json.dumps({"huawei_username": "u", "huawei_password": "p"}),
            encoding="utf-8",
        )
        args = config.parse_args(["--config", str(cfg_file)])
        cfg = config.build_config(args=args)
        assert cfg.username == "u"
        assert cfg.password == "p"

    def test_raises_when_credentials_missing(self, tmp_path, clean_env):
        args = config.parse_args(["--config", str(tmp_path / "nope.json")])
        with pytest.raises(RuntimeError):
            config.build_config(args=args)

    def test_output_defaults_none(self, clean_env, monkeypatch):
        """不指定 --output 时不保存文件：output_dir / output_file 均为 None。"""
        monkeypatch.setenv("HUAWEI_USERNAME", "env-user")
        monkeypatch.setenv("HUAWEI_PASSWORD", "env-pwd")
        args = config.parse_args([])
        cfg = config.build_config(args=args)
        assert cfg.output_dir is None
        assert cfg.output_file is None

    def test_output_resolves_file_path(self, clean_env, monkeypatch):
        """指定 --output 时据其拼出输出文件路径。"""
        monkeypatch.setenv("HUAWEI_USERNAME", "env-user")
        monkeypatch.setenv("HUAWEI_PASSWORD", "env-pwd")
        args = config.parse_args(["--output", "/tmp/out"])
        cfg = config.build_config(args=args)
        assert cfg.output_dir == "/tmp/out"
        assert cfg.output_file == f"/tmp/out/{config.OUTPUT_FILENAME}"
