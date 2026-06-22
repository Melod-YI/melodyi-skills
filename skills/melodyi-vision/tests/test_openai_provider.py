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
        )
        result = provider.understand("aW1hZ2VkYXRh", "image/png", "What is this?")

        assert result == "A cat sitting on a mat."
        assert captured_request["url"] == "https://api.openai.com/v1/chat/completions"
        body = captured_request["body"]
        assert body["model"] == "gpt-4o"
        assert body["max_tokens"] == 1024
        assert len(body["messages"]) == 1
        assert body["messages"][0]["role"] == "user"
        content = body["messages"][0]["content"]
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "What is this?"
        assert content[1]["type"] == "image_url"
        assert content[1]["image_url"]["url"] == "data:image/png;base64,aW1hZ2VkYXRh"


class TestOpenAIProviderErrors:
    def _make_provider(self):
        return OpenAIProvider(
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            model="gpt-4o",
            max_tokens=1024,
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
