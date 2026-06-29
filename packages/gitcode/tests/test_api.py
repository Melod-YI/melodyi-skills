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
