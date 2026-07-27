import io
import sys
import pytest
from understand_image import parse_args


class TestParseArgs:
    def test_minimal_args(self):
        args = parse_args(["./image.png"])
        assert args.image_source == "./image.png"
        assert args.prompt == "Describe this image in detail."
        assert args.config is None
        assert args.provider is None
        assert args.model is None
        assert args.max_tokens is None
        assert args.stream is None

    def test_all_args(self):
        args = parse_args([
            "https://example.com/img.jpg",
            "--prompt", "What is in this image?",
            "--config", "/path/to/config.json",
            "--provider", "openai",
            "--model", "gpt-4o-mini",
            "--max-tokens", "512",
            "--no-stream",
        ])
        assert args.image_source == "https://example.com/img.jpg"
        assert args.prompt == "What is in this image?"
        assert args.config == "/path/to/config.json"
        assert args.provider == "openai"
        assert args.model == "gpt-4o-mini"
        assert args.max_tokens == 512
        assert args.stream is False

    def test_stream_flag_default_none(self):
        """未指定时 stream 应为 None，以让配置文件/环境变量决定。"""
        assert parse_args(["./image.png"]).stream is None

    def test_explicit_stream_flag(self):
        assert parse_args(["./image.png", "--stream"]).stream is True

    def test_missing_image_source_exits(self):
        with pytest.raises(SystemExit):
            parse_args([])


class TestMainIntegration:
    def test_full_flow_with_local_file(self, tmp_path, monkeypatch):
        # Create a fake image file
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake png data")

        # Set API key via env
        monkeypatch.setenv("VISION_API_KEY", "test-key")
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)

        # Mock get_provider to avoid real API call
        import understand_image

        class MockProvider:
            def understand(self, image_data, mime_type, prompt):
                return "A test image with fake content."

        monkeypatch.setattr(
            understand_image, "get_provider", lambda name, **kwargs: MockProvider()
        )

        # Capture stdout
        import io
        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)

        understand_image.main([str(img_file), "--prompt", "What is this?"])
        assert captured.getvalue().strip() == "A test image with fake content."

    def test_stream_config_passed_to_provider(self, tmp_path, monkeypatch):
        """main 应把解析后的 stream 配置透传给 get_provider。"""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake png data")
        monkeypatch.setenv("VISION_API_KEY", "test-key")
        for v in ("VISION_API_BASE", "VISION_MODEL", "VISION_MAX_TOKENS",
                  "VISION_PROVIDER", "VISION_STREAM"):
            monkeypatch.delenv(v, raising=False)

        captured = {}

        class MockProvider:
            def understand(self, image_data, mime_type, prompt):
                return "ok"

        def fake_get_provider(name, **kwargs):
            captured["kwargs"] = kwargs
            return MockProvider()

        import understand_image
        monkeypatch.setattr(understand_image, "get_provider", fake_get_provider)
        monkeypatch.setattr(sys, "stdout", io.StringIO())

        # 默认走流式
        understand_image.main([str(img_file)])
        assert captured["kwargs"].get("stream") is True

        # --no-stream 透传为 False
        understand_image.main([str(img_file), "--no-stream"])
        assert captured["kwargs"].get("stream") is False

    def test_missing_api_key_exits(self, tmp_path, monkeypatch):
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake")

        monkeypatch.delenv("VISION_API_KEY", raising=False)
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)

        with pytest.raises(SystemExit):
            from understand_image import main
            main([str(img_file)])

    def test_nonexistent_file_exits(self, monkeypatch):
        monkeypatch.setenv("VISION_API_KEY", "test-key")
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)

        with pytest.raises(SystemExit):
            from understand_image import main
            main(["/nonexistent/path/image.png"])
