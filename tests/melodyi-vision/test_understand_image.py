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

    def test_all_args(self):
        args = parse_args([
            "https://example.com/img.jpg",
            "--prompt", "What is in this image?",
            "--config", "/path/to/config.json",
            "--provider", "openai",
            "--model", "gpt-4o-mini",
            "--max-tokens", "512",
        ])
        assert args.image_source == "https://example.com/img.jpg"
        assert args.prompt == "What is in this image?"
        assert args.config == "/path/to/config.json"
        assert args.provider == "openai"
        assert args.model == "gpt-4o-mini"
        assert args.max_tokens == 512

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
