"""GitCodeClient 单元测试：用 httpx.MockTransport 注入假响应，验证请求构造与响应解析"""

import httpx
import pytest

from gitcode.api import API_BASE, APIError, GitCodeClient


def _client(handler):
    return GitCodeClient("tok-123", transport=httpx.MockTransport(handler))


def test_get_user_request_and_parse():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"login": "alice", "id": 7})

    client = _client(handler)
    data = client.get_user()

    assert data == {"login": "alice", "id": 7}
    assert captured["url"] == f"{API_BASE}/user"
    assert captured["method"] == "GET"
    assert captured["auth"] == "Bearer tok-123"


def test_api_error_on_401():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")
    client = _client(handler)
    with pytest.raises(APIError) as exc:
        client.get_user()
    assert exc.value.status_code == 401


def test_api_error_on_404():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")
    client = _client(handler)
    with pytest.raises(APIError) as exc:
        client.get_user()
    assert exc.value.status_code == 404


def test_empty_body_returns_empty_dict():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")
    client = _client(handler)
    assert client.get_user() == {}


def test_network_error_raises_api_error_zero():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")
    client = _client(handler)
    with pytest.raises(APIError) as exc:
        client.get_user()
    assert exc.value.status_code == 0


def test_get_pr_request_and_parse():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"number": 123, "title": "feat: x"})

    client = _client(handler)
    data = client.get_pr("owner", "repo", "123")

    assert data == {"number": 123, "title": "feat: x"}
    assert captured["url"] == f"{API_BASE}/repos/owner/repo/pulls/123"


def test_get_files_request_and_parse():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=[{"filename": "a.py"}, {"filename": "b.py"}])

    client = _client(handler)
    data = client.get_files("owner", "repo", "123")

    assert [f["filename"] for f in data] == ["a.py", "b.py"]
    # 分页：单页即终止，请求带 page/per_page 参数
    assert captured["url"].startswith(f"{API_BASE}/repos/owner/repo/pulls/123/files?")
    assert "page=1" in captured["url"]
    assert "per_page=100" in captured["url"]


def test_get_files_paginates():
    """超过一页时循环聚合，直到返回不足 100 条"""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        calls.append(page)
        if page == 1:
            # 第一页满 100 条
            return httpx.Response(200, json=[{"filename": f"f{i}.py"} for i in range(100)])
        # 第二页 3 条，触发终止
        return httpx.Response(200, json=[{"filename": f"g{i}.py"} for i in range(3)])

    client = _client(handler)
    data = client.get_files("owner", "repo", "123")

    assert len(data) == 103
    assert calls == [1, 2]


def test_list_prs_request_params():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=[{"number": 1, "title": "t"}])

    client = _client(handler)
    data = client.list_prs("owner", "repo", state="merged", author="alice")

    assert data == [{"number": 1, "title": "t"}]
    assert captured["url"].startswith(f"{API_BASE}/repos/owner/repo/pulls?")
    assert "state=merged" in captured["url"]
    assert "author=alice" in captured["url"]
    assert "per_page=100" in captured["url"]
    assert "page=1" in captured["url"]


def test_list_prs_paginates():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        calls.append(page)
        if page == 1:
            return httpx.Response(200, json=[{"number": i} for i in range(100)])
        return httpx.Response(200, json=[{"number": 100}, {"number": 101}])

    client = _client(handler)
    data = client.list_prs("owner", "repo")

    assert len(data) == 102
    assert calls == [1, 2]


def test_list_prs_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    client = _client(handler)
    assert client.list_prs("owner", "repo") == []


def test_get_comments_request_and_parse():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=[
            {"id": 1, "body": "x", "user": {"login": "alice"}},
            {"id": 2, "body": "y", "user": {"login": "bob"}},
        ])

    client = _client(handler)
    data = client.get_comments("owner", "repo", "123")

    assert len(data) == 2
    assert data[0]["user"]["login"] == "alice"
    assert captured["url"] == f"{API_BASE}/repos/owner/repo/pulls/123/comments"


def test_post_comment_request_body():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = request.read()
        return httpx.Response(201, json={"id": 99, "body": "**[严重]** 问题"})

    client = _client(handler)
    data = client.post_comment(
        "owner", "repo", "123",
        body="**[严重]** 问题", path="src/a.py", position=10,
    )

    assert data == {"id": 99, "body": "**[严重]** 问题"}
    assert captured["method"] == "POST"
    assert captured["url"] == f"{API_BASE}/repos/owner/repo/pulls/123/comments"
    # 中文经 json= 自动 UTF-8 编码，能正确还原
    import json as _json
    assert _json.loads(captured["body"]) == {
        "body": "**[严重]** 问题", "path": "src/a.py", "position": 10,
    }


def test_post_comment_with_commit_id():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read()
        return httpx.Response(201, json={})

    client = _client(handler)
    client.post_comment(
        "owner", "repo", "123",
        body="b", path="p", position=1, commit_id="abc",
    )
    import json as _json
    assert _json.loads(captured["body"])["commit_id"] == "abc"


def test_resolve_comment_request():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = request.read()
        return httpx.Response(200, json={"resolved": True})

    client = _client(handler)
    data = client.resolve_comment("owner", "repo", "123", "disc-1")

    assert data == {"resolved": True}
    assert captured["method"] == "PUT"
    assert captured["url"] == f"{API_BASE}/repos/owner/repo/pulls/123/comments/disc-1"
    import json as _json
    assert _json.loads(captured["body"]) == {"resolved": True}


def test_resolve_comment_false():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read()
        return httpx.Response(200, json={})

    client = _client(handler)
    client.resolve_comment("owner", "repo", "123", "disc-1", resolved=False)
    import json as _json
    assert _json.loads(captured["body"]) == {"resolved": False}
