import json
import pytest
from providers.openai_provider import OpenAIProvider


class TestOpenAIProviderRequest:
    def test_builds_correct_request_body(self, monkeypatch):
        captured_request = {}

        class FakeResponse:
            def __init__(self):
                self.body = json.dumps({
                    "choices": [{"message": {"content": "A cat sitting on a mat."}}]
                }).encode("utf-8")

            def read(self):
                return self.body

            def getheader(self, name, default=""):
                return default

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        def fake_urlopen(req, data=None, timeout=None):
            captured_request["url"] = req.full_url
            captured_request["headers"] = dict(req.headers)
            captured_request["body"] = json.loads(data.decode("utf-8"))
            return FakeResponse()

        monkeypatch.setattr(
            "providers.openai_provider.urllib.request.urlopen", fake_urlopen
        )

        provider = OpenAIProvider(
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            model="gpt-4o",
            max_tokens=1024,
            stream=False,
        )
        result = provider.understand("aW1hZ2VkYXRh", "image/png", "What is this?")

        assert result == "A cat sitting on a mat."
        assert captured_request["url"] == "https://api.openai.com/v1/chat/completions"
        body = captured_request["body"]
        assert body["model"] == "gpt-4o"
        assert body["max_tokens"] == 1024
        # 非流式不应携带 stream 字段
        assert "stream" not in body
        assert len(body["messages"]) == 1
        assert body["messages"][0]["role"] == "user"
        content = body["messages"][0]["content"]
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "What is this?"
        assert content[1]["type"] == "image_url"
        assert content[1]["image_url"]["url"] == "data:image/png;base64,aW1hZ2VkYXRh"


class TestOpenAIProviderStream:
    """流式（SSE）调用默认开启，逐块累加 delta.content。"""

    def _stream_response(self, content_chunks):
        """构造一个可按行迭代的 SSE 假响应。"""
        lines = []
        for c in content_chunks:
            payload = {"choices": [{"delta": {"content": c}}]}
            lines.append(b"data: " + json.dumps(payload).encode("utf-8"))
        lines.append(b"data: [DONE]")

        class FakeStreamResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def __iter__(self):
                return iter(lines)

        return FakeStreamResponse()

    def test_default_stream_is_true(self):
        """未显式指定 stream 时，默认应为 True（流式）。"""
        provider = OpenAIProvider(
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            model="gpt-4o",
            max_tokens=1024,
        )
        assert provider.stream is True

    def test_stream_sends_stream_flag_in_body(self, monkeypatch):
        captured = {}

        def fake_urlopen(req, data=None, timeout=None):
            captured["body"] = json.loads(data.decode("utf-8"))
            return self._stream_response(["ok"])

        monkeypatch.setattr(
            "providers.openai_provider.urllib.request.urlopen", fake_urlopen
        )
        provider = OpenAIProvider(
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            model="gpt-4o",
            max_tokens=1024,
        )
        result = provider.understand("data", "image/png", "describe")
        assert captured["body"]["stream"] is True
        assert result == "ok"

    def test_stream_accumulates_delta_content(self, monkeypatch):
        def fake_urlopen(req, data=None, timeout=None):
            return self._stream_response(["Hello", " world", "!"])

        monkeypatch.setattr(
            "providers.openai_provider.urllib.request.urlopen", fake_urlopen
        )
        provider = OpenAIProvider(
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            model="gpt-4o",
            max_tokens=1024,
        )
        assert provider.understand("data", "image/png", "describe") == "Hello world!"

    def test_stream_skips_delta_without_content(self, monkeypatch):
        """首个 chunk 通常只有 role、无 content，应被跳过而不报错。"""
        lines = [
            b'data: {"choices":[{"delta":{"role":"user"}}]}',
            b'data: {"choices":[{"delta":{"content":"hi"}}]}',
            b"data: [DONE]",
        ]

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def __iter__(self):
                return iter(lines)

        monkeypatch.setattr(
            "providers.openai_provider.urllib.request.urlopen",
            lambda req, data=None, timeout=None: Resp(),
        )
        provider = OpenAIProvider(
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            model="gpt-4o",
            max_tokens=1024,
        )
        assert provider.understand("data", "image/png", "describe") == "hi"

    def test_stream_empty_result_exits(self, monkeypatch):
        """SSE 流没有累加出任何内容时应以 SystemExit 退出。"""
        monkeypatch.setattr(
            "providers.openai_provider.urllib.request.urlopen",
            lambda req, data=None, timeout=None: self._stream_response([]),
        )
        provider = OpenAIProvider(
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            model="gpt-4o",
            max_tokens=1024,
        )
        with pytest.raises(SystemExit):
            provider.understand("data", "image/png", "describe")


class TestOpenAIProviderErrors:
    def _make_provider(self):
        return OpenAIProvider(
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            model="gpt-4o",
            max_tokens=1024,
            stream=False,
        )

    def test_api_http_error(self, monkeypatch):
        import urllib.error
        import io

        def fake_urlopen(req, data=None, timeout=None):
            raise urllib.error.HTTPError(
                url="https://api.openai.com/v1/chat/completions",
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=io.BytesIO(b'{"error": "invalid api key"}'),
            )

        monkeypatch.setattr(
            "providers.openai_provider.urllib.request.urlopen", fake_urlopen
        )
        provider = self._make_provider()
        with pytest.raises(SystemExit):
            provider.understand("data", "image/png", "describe")

    def test_api_url_error(self, monkeypatch):
        import urllib.error

        def fake_urlopen(req, data=None, timeout=None):
            raise urllib.error.URLError("Connection refused")

        monkeypatch.setattr(
            "providers.openai_provider.urllib.request.urlopen", fake_urlopen
        )
        provider = self._make_provider()
        with pytest.raises(SystemExit):
            provider.understand("data", "image/png", "describe")

    def test_invalid_response_format(self, monkeypatch):
        class FakeResponse:
            def __init__(self):
                self.body = b'{"unexpected": "format"}'

            def read(self):
                return self.body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        def fake_urlopen(req, data=None, timeout=None):
            return FakeResponse()

        monkeypatch.setattr(
            "providers.openai_provider.urllib.request.urlopen", fake_urlopen
        )
        provider = self._make_provider()
        with pytest.raises(SystemExit):
            provider.understand("data", "image/png", "describe")


class TestOpenAIProviderVerifySsl:
    """verify_ssl 开关落地到 urlopen：默认不传 context；关闭时传 unverified context。"""

    def _stream_response(self, chunks):
        import io

        class FakeResponse:
            def __init__(self):
                self._lines = [
                    (b'data: ' + json.dumps({"choices": [{"delta": {"content": c}}]}).encode())
                    for c in chunks
                ] + [b'data: [DONE]']

            def __iter__(self):
                return iter(self._lines)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        return FakeResponse()

    def test_default_verify_ssl_passes_no_context(self, monkeypatch):
        """verify_ssl 默认 True：urlopen 不应收到 context kwarg（保持 urllib 默认校验）。"""
        captured = {}

        def fake_urlopen(req, data=None, timeout=None, **kwargs):
            captured["kwargs"] = kwargs
            return self._stream_response(["ok"])

        monkeypatch.setattr(
            "providers.openai_provider.urllib.request.urlopen", fake_urlopen
        )
        provider = OpenAIProvider(
            api_key="k", api_base="https://api.openai.com/v1", model="gpt-4o", max_tokens=1024
        )
        provider.understand("data", "image/png", "describe")
        assert "context" not in captured["kwargs"]

    def test_verify_ssl_false_passes_unverified_context(self, monkeypatch):
        """verify_ssl=False：urlopen 应收到 unverified SSL context。"""
        import ssl as _ssl

        captured = {}

        def fake_urlopen(req, data=None, timeout=None, **kwargs):
            captured["kwargs"] = kwargs
            return self._stream_response(["ok"])

        monkeypatch.setattr(
            "providers.openai_provider.urllib.request.urlopen", fake_urlopen
        )
        provider = OpenAIProvider(
            api_key="k", api_base="https://api.openai.com/v1", model="gpt-4o",
            max_tokens=1024, verify_ssl=False,
        )
        provider.understand("data", "image/png", "describe")
        ctx = captured["kwargs"].get("context")
        assert ctx is not None
        # unverified context 的标志：check_hostname 为 False 且 verify_mode 为 CERT_NONE
        assert ctx.check_hostname is False
        assert ctx.verify_mode == _ssl.CERT_NONE
