"""fetch_comments 的代理透传测试：requests.get 应收到配置文件提供的 proxies"""

import json

import fetch_comments
import hn_config


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.text = ""
        self._payload = payload or {}

    def json(self):
        return self._payload


def _patch_requests_get(monkeypatch, captured):
    def fake_get(url, timeout=None, proxies=None, **kwargs):
        captured["url"] = url
        captured["timeout"] = timeout
        captured["proxies"] = proxies
        # 最小 item：根节点 + 无子评论
        return _FakeResponse(payload={"author": "alice", "children": []})

    monkeypatch.setattr(fetch_comments.requests, "get", fake_get)


class TestFetchCommentsProxies:
    def test_passes_proxies_when_configured(self, tmp_path, monkeypatch):
        """配置文件设置 proxy 后，requests.get 收到 http/https 映射"""
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"proxy": "http://127.0.0.1:7890"}), encoding="utf-8")
        monkeypatch.setattr(hn_config, "CONFIG_PATH", cfg)

        captured = {}
        _patch_requests_get(monkeypatch, captured)

        result = fetch_comments.fetch_comments(123, threshold=201, budget=200)
        assert result["author"] == "alice"
        assert captured["proxies"] == {
            "http": "http://127.0.0.1:7890",
            "https": "http://127.0.0.1:7890",
        }
        assert captured["timeout"] == 30

    def test_passes_none_when_unconfigured(self, tmp_path, monkeypatch):
        """未配置代理时 proxies=None（等价于不传，走 requests 默认行为）"""
        monkeypatch.setattr(hn_config, "CONFIG_PATH", tmp_path / "nope.json")

        captured = {}
        _patch_requests_get(monkeypatch, captured)

        fetch_comments.fetch_comments(123, threshold=201, budget=200)
        assert captured["proxies"] is None
