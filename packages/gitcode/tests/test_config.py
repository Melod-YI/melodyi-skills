"""load_token 单元测试：优先级 env > config 文件"""

import json

from gitcode.config import load_token


def test_env_takes_priority(monkeypatch, tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"gitcode_token": "from-file"}), encoding="utf-8")
    monkeypatch.setenv("GITCODE_TOKEN", "from-env")
    assert load_token(cfg) == "from-env"


def test_reads_from_config_file(monkeypatch, tmp_path):
    monkeypatch.delenv("GITCODE_TOKEN", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"gitcode_token": "from-file"}), encoding="utf-8")
    assert load_token(cfg) == "from-file"


def test_strips_whitespace(monkeypatch, tmp_path):
    monkeypatch.delenv("GITCODE_TOKEN", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"gitcode_token": "  spaced  "}), encoding="utf-8")
    assert load_token(cfg) == "spaced"


def test_missing_token_returns_none(monkeypatch, tmp_path):
    monkeypatch.delenv("GITCODE_TOKEN", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"other": "x"}), encoding="utf-8")
    assert load_token(cfg) is None


def test_missing_file_returns_none(monkeypatch, tmp_path):
    monkeypatch.delenv("GITCODE_TOKEN", raising=False)
    assert load_token(tmp_path / "nope.json") is None


def test_env_empty_falls_back_to_file(monkeypatch, tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"gitcode_token": "from-file"}), encoding="utf-8")
    monkeypatch.setenv("GITCODE_TOKEN", "   ")  # 空白视作未设置
    assert load_token(cfg) == "from-file"


def test_corrupt_json_returns_none(monkeypatch, tmp_path):
    """配置文件 JSON 损坏时返回 None，不抛异常"""
    monkeypatch.delenv("GITCODE_TOKEN", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text("{not valid json", encoding="utf-8")
    assert load_token(cfg) is None


def test_non_dict_json_returns_none(monkeypatch, tmp_path):
    """配置文件内容非对象（如数组）时返回 None"""
    monkeypatch.delenv("GITCODE_TOKEN", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    assert load_token(cfg) is None
