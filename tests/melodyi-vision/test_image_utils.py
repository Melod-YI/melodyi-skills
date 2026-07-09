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
