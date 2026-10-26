"""hn_config 读取测试：~/.melodyi-skills/hackernews/config.json 的 proxy 字段"""

import json

import hn_config


def _write_cfg(tmp_path, data):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(data), encoding="utf-8")
    return cfg


class TestLoadProxy:
    def test_from_config_file(self, tmp_path, monkeypatch):
        cfg = _write_cfg(tmp_path, {"proxy": "http://127.0.0.1:7890"})
        monkeypatch.setattr(hn_config, "CONFIG_PATH", cfg)
        assert hn_config.load_proxy() == "http://127.0.0.1:7890"

    def test_strips_whitespace(self, tmp_path, monkeypatch):
        cfg = _write_cfg(tmp_path, {"proxy": "  http://127.0.0.1:7890  "})
        monkeypatch.setattr(hn_config, "CONFIG_PATH", cfg)
        assert hn_config.load_proxy() == "http://127.0.0.1:7890"

    def test_empty_string_returns_none(self, tmp_path, monkeypatch):
        """空字符串/纯空白视作未配置"""
        cfg = _write_cfg(tmp_path, {"proxy": "   "})
        monkeypatch.setattr(hn_config, "CONFIG_PATH", cfg)
        assert hn_config.load_proxy() is None

    def test_missing_key_returns_none(self, tmp_path, monkeypatch):
        cfg = _write_cfg(tmp_path, {"other": "x"})
        monkeypatch.setattr(hn_config, "CONFIG_PATH", cfg)
        assert hn_config.load_proxy() is None

    def test_missing_file_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hn_config, "CONFIG_PATH", tmp_path / "nope.json")
        assert hn_config.load_proxy() is None

    def test_corrupt_json_returns_none(self, tmp_path, monkeypatch):
        """配置文件 JSON 损坏时返回 None，不抛异常"""
        cfg = tmp_path / "config.json"
        cfg.write_text("{not valid json", encoding="utf-8")
        monkeypatch.setattr(hn_config, "CONFIG_PATH", cfg)
        assert hn_config.load_proxy() is None

    def test_non_dict_returns_none(self, tmp_path, monkeypatch):
        """配置文件内容非对象（如数组）时返回 None"""
        cfg = _write_cfg(tmp_path, ["not", "an", "object"])
        monkeypatch.setattr(hn_config, "CONFIG_PATH", cfg)
        assert hn_config.load_proxy() is None


class TestRequestProxies:
    def test_none_when_unconfigured(self, tmp_path, monkeypatch):
        """未配置返回 None（等价于不传 proxies 参数）"""
        monkeypatch.setattr(hn_config, "CONFIG_PATH", tmp_path / "nope.json")
        assert hn_config.request_proxies() is None

    def test_mapping_when_configured(self, tmp_path, monkeypatch):
        """配置了代理返回 http/https 映射（显式代理优先于环境变量）"""
        cfg = _write_cfg(tmp_path, {"proxy": "http://127.0.0.1:7890"})
        monkeypatch.setattr(hn_config, "CONFIG_PATH", cfg)
        assert hn_config.request_proxies() == {
            "http": "http://127.0.0.1:7890",
            "https": "http://127.0.0.1:7890",
        }
