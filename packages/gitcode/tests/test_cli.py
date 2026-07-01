"""CLI 子命令测试：CliRunner + monkeypatch GitCodeClient"""

import json

import httpx
from click.testing import CliRunner

from gitcode.cli import cli


def _write_cfg(tmp_path, token="tok-123"):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"gitcode_token": token}), encoding="utf-8")
    return cfg


def _patch_client(monkeypatch, handler):
    """把 GitCodeClient 替换为注入 MockTransport 的实例"""
    import gitcode.cli as cli_mod

    real_init = cli_mod.GitCodeClient.__init__

    def fake_init(self, token, transport=None):
        real_init(self, token, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(cli_mod.GitCodeClient, "__init__", fake_init)


def test_user_command_outputs_json(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(200, json={"login": "alice"}))
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(cli, ["--config", str(cfg), "user"])

    assert result.exit_code == 0
    assert json.loads(result.output) == {"login": "alice"}


def test_missing_token_exits_2(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(200, json={}))
    cfg = tmp_path / "config.json"  # 不写入 token
    cfg.write_text("{}", encoding="utf-8")

    result = CliRunner().invoke(cli, ["--config", str(cfg), "user"])

    assert result.exit_code == 2
    assert "token" in result.output.lower()


def test_api_error_exits_1(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(401, text="no auth"))
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(cli, ["--config", str(cfg), "user"])

    assert result.exit_code == 1
    assert "401" in result.output


def test_pr_command_uses_url(tmp_path, monkeypatch):
    captured = {}

    def handler(req):
        captured["url"] = str(req.url)
        return httpx.Response(200, json={"title": "t"})

    _patch_client(monkeypatch, handler)
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(
        cli, ["--config", str(cfg), "pr",
              "https://gitcode.com/owner/repo/-/merge_requests/123"]
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {"title": "t"}
    assert captured["url"].endswith("/repos/owner/repo/pulls/123")


def test_invalid_url_exits_1(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(200, json={}))
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(
        cli, ["--config", str(cfg), "pr", "https://example.com/x"]
    )
    assert result.exit_code == 1


def test_prs_command_outputs_json(tmp_path, monkeypatch):
    captured = {}

    def handler(req):
        captured["url"] = str(req.url)
        return httpx.Response(200, json=[
            {"number": 1, "title": "t1", "user": {"login": "alice"}},
            {"number": 2, "title": "t2", "user": {"login": "alice"}},
        ])

    _patch_client(monkeypatch, handler)
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(cli, [
        "--config", str(cfg), "prs",
        "https://gitcode.com/openJiuwen/jiuwenswarm",
        "--author", "alice", "--state", "all",
    ])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert [d["number"] for d in data] == [1, 2]
    assert "/repos/openJiuwen/jiuwenswarm/pulls" in captured["url"]
    assert "author=alice" in captured["url"]
    assert "state=all" in captured["url"]


def test_prs_invalid_repo_url_exits_1(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(200, json=[]))
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(
        cli, ["--config", str(cfg), "prs", "https://gitcode.com/onlyowner"]
    )
    assert result.exit_code == 1


def test_comments_mine_filters_by_user(tmp_path, monkeypatch):
    calls = []

    def handler(req):
        calls.append(str(req.url))
        if req.url.path.endswith("/user"):
            return httpx.Response(200, json={"login": "alice"})
        return httpx.Response(200, json=[
            {"id": 1, "user": {"login": "alice"}},
            {"id": 2, "user": {"login": "bob"}},
        ])

    _patch_client(monkeypatch, handler)
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(
        cli, ["--config", str(cfg), "comments", "--mine",
              "https://gitcode.com/owner/repo/-/merge_requests/123"]
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert [c["id"] for c in data] == [1]


def test_comment_body_file(tmp_path, monkeypatch):
    captured = {}

    def handler(req):
        captured["body"] = req.read()
        return httpx.Response(201, json={"id": 99})

    _patch_client(monkeypatch, handler)
    cfg = _write_cfg(tmp_path)
    body_file = tmp_path / "body.md"
    body_file.write_text("**[严重]** 中文问题", encoding="utf-8")

    result = CliRunner().invoke(cli, [
        "--config", str(cfg), "comment",
        "https://gitcode.com/owner/repo/-/merge_requests/123",
        "--path", "src/a.py", "--position", "10",
        "--body-file", str(body_file),
    ])

    assert result.exit_code == 0
    assert json.loads(result.output) == {"id": 99}
    assert json.loads(captured["body"])["body"] == "**[严重]** 中文问题"


def test_comment_requires_body(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(201, json={}))
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(cli, [
        "--config", str(cfg), "comment",
        "https://gitcode.com/owner/repo/-/merge_requests/123",
        "--path", "src/a.py", "--position", "10",
    ])
    assert result.exit_code == 2


def test_resolve_command(tmp_path, monkeypatch):
    captured = {}

    def handler(req):
        captured["method"] = req.method
        captured["url"] = str(req.url)
        return httpx.Response(200, json={"resolved": True})

    _patch_client(monkeypatch, handler)
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(cli, [
        "--config", str(cfg), "resolve",
        "https://gitcode.com/owner/repo/-/merge_requests/123",
        "--discussion-id", "disc-1",
    ])

    assert result.exit_code == 0
    assert captured["method"] == "PUT"
    assert captured["url"].endswith("/comments/disc-1")
