import base64
import pytest
from pathlib import Path
from image_utils import load_image


class TestLoadLocalFile:
    def test_load_png_file(self, tmp_path):
        png_file = tmp_path / "test.png"
        content = b"\x89PNG\r\n\x1a\n" + b"fake png data"
        png_file.write_bytes(content)
        b64_data, mime_type = load_image(str(png_file))
        assert mime_type == "image/png"
        assert b64_data == base64.b64encode(content).decode("utf-8")

    def test_load_jpg_file(self, tmp_path):
        jpg_file = tmp_path / "test.jpg"
        content = b"\xff\xd8\xff\xe0" + b"fake jpg data"
        jpg_file.write_bytes(content)
        b64_data, mime_type = load_image(str(jpg_file))
        assert mime_type == "image/jpeg"
        assert b64_data == base64.b64encode(content).decode("utf-8")

    def test_load_jpeg_extension(self, tmp_path):
        jpeg_file = tmp_path / "test.jpeg"
        jpeg_file.write_bytes(b"fake data")
        _, mime_type = load_image(str(jpeg_file))
        assert mime_type == "image/jpeg"

    def test_load_webp_file(self, tmp_path):
        webp_file = tmp_path / "test.webp"
        webp_file.write_bytes(b"fake webp data")
        _, mime_type = load_image(str(webp_file))
        assert mime_type == "image/webp"

    def test_load_gif_file(self, tmp_path):
        gif_file = tmp_path / "test.gif"
        gif_file.write_bytes(b"fake gif data")
        _, mime_type = load_image(str(gif_file))
        assert mime_type == "image/gif"

    def test_file_not_found_raises_system_exit(self):
        with pytest.raises(SystemExit):
            load_image("/nonexistent/path/image.png")

    def test_unsupported_format_raises_system_exit(self, tmp_path):
        bmp_file = tmp_path / "test.bmp"
        bmp_file.write_bytes(b"fake bmp data")
        with pytest.raises(SystemExit):
            load_image(str(bmp_file))


class TestLoadUrl:
    def test_load_from_url(self, monkeypatch):
        fake_data = b"fake image content from url"
        expected_b64 = base64.b64encode(fake_data).decode("utf-8")

        class FakeResponse:
            def read(self):
                return fake_data
            def getheader(self, name, default=""):
                if name == "Content-Type":
                    return "image/png"
                return default
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass

        def fake_urlopen(req, timeout=None):
            return FakeResponse()

        monkeypatch.setattr("image_utils.urllib.request.urlopen", fake_urlopen)
        b64_data, mime_type = load_image("https://example.com/test.png")
        assert b64_data == expected_b64
        assert mime_type == "image/png"

    def test_url_download_failure(self, monkeypatch):
        def fake_urlopen(req, timeout=None):
            raise Exception("Connection refused")

        monkeypatch.setattr("image_utils.urllib.request.urlopen", fake_urlopen)
        with pytest.raises(SystemExit):
            load_image("https://nonexistent.example.com/image.png")


class TestVerifySslLoadFromUrl:
    """verify_ssl 落地到 URL 图片下载。"""

    def test_default_verify_ssl_passes_no_context(self, monkeypatch):
        import image_utils

        captured = {}

        class FakeResponse:
            def read(self):
                return b"img"

            def getheader(self, name, default=""):
                return "image/png" if name == "Content-Type" else default

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        def fake_urlopen(url, timeout=None, **kwargs):
            captured["kwargs"] = kwargs
            return FakeResponse()

        monkeypatch.setattr("image_utils.urllib.request.urlopen", fake_urlopen)
        load_image("https://example.com/test.png")
        assert "context" not in captured["kwargs"]

    def test_verify_ssl_false_passes_unverified_context(self, monkeypatch):
        import ssl as _ssl

        import image_utils

        captured = {}

        class FakeResponse:
            def read(self):
                return b"img"

            def getheader(self, name, default=""):
                return "image/png" if name == "Content-Type" else default

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        def fake_urlopen(url, timeout=None, **kwargs):
            captured["kwargs"] = kwargs
            return FakeResponse()

        monkeypatch.setattr("image_utils.urllib.request.urlopen", fake_urlopen)
        load_image("https://example.com/test.png", verify_ssl=False)
        ctx = captured["kwargs"].get("context")
        assert ctx is not None
        assert ctx.check_hostname is False
        assert ctx.verify_mode == _ssl.CERT_NONE


class TestProxyLoadFromUrl:
    """proxy 落地到 URL 图片下载：默认走 urlopen；配置代理后走 opener。"""

    class _FakeResponse:
        def read(self):
            return b"img"

        def getheader(self, name, default=""):
            return "image/png" if name == "Content-Type" else default

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def test_no_proxy_keeps_urlopen(self, monkeypatch):
        """未配置代理：只走 urlopen，不构造 opener（保持默认行为与 monkeypatch 兼容）。"""
        urlopen_called = []

        def fake_urlopen(url, timeout=None, **kwargs):
            urlopen_called.append(url)
            return self._FakeResponse()

        def fail_build_opener(*args, **kwargs):
            raise AssertionError("未配置代理不应构造 opener")

        monkeypatch.setattr("image_utils.urllib.request.urlopen", fake_urlopen)
        monkeypatch.setattr("image_utils.urllib.request.build_opener", fail_build_opener)
        load_image("https://example.com/test.png")
        assert len(urlopen_called) == 1

    def test_proxy_uses_opener(self, monkeypatch):
        """配置代理：经 build_opener(ProxyHandler) 构造 opener 下载，不再走 urlopen。"""
        import urllib.request

        captured = {}

        class FakeOpener:
            def open(self, url, timeout=None):
                captured["url"] = url
                captured["timeout"] = timeout
                return TestProxyLoadFromUrl._FakeResponse()

        def fake_build_opener(*handlers):
            captured["handlers"] = handlers
            return FakeOpener()

        def fail_urlopen(*args, **kwargs):
            raise AssertionError("配置代理后不应再走 urlopen")

        monkeypatch.setattr("image_utils.urllib.request.build_opener", fake_build_opener)
        monkeypatch.setattr("image_utils.urllib.request.urlopen", fail_urlopen)
        b64_data, mime_type = load_image(
            "https://example.com/test.png", proxy="http://127.0.0.1:7890"
        )
        assert b64_data == base64.b64encode(b"img").decode("utf-8")
        assert mime_type == "image/png"
        assert captured["timeout"] == 30
        proxy_handlers = [
            h for h in captured["handlers"]
            if isinstance(h, urllib.request.ProxyHandler)
        ]
        assert len(proxy_handlers) == 1
        assert proxy_handlers[0].proxies == {
            "http": "http://127.0.0.1:7890",
            "https": "http://127.0.0.1:7890",
        }

    def test_proxy_with_verify_ssl_false_adds_https_handler(self, monkeypatch):
        """代理 + 关闭 SSL 校验：handlers 里应含 HTTPSHandler（挂 unverified context）。"""
        import urllib.request

        captured = {}

        class FakeOpener:
            def open(self, url, timeout=None):
                return TestProxyLoadFromUrl._FakeResponse()

        def fake_build_opener(*handlers):
            captured["handlers"] = handlers
            return FakeOpener()

        monkeypatch.setattr("image_utils.urllib.request.build_opener", fake_build_opener)
        monkeypatch.setattr(
            "image_utils.urllib.request.urlopen",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("不应走 urlopen")),
        )
        load_image(
            "https://example.com/test.png",
            verify_ssl=False, proxy="http://127.0.0.1:7890",
        )
        https_handlers = [
            h for h in captured["handlers"]
            if isinstance(h, urllib.request.HTTPSHandler)
        ]
        assert len(https_handlers) == 1
