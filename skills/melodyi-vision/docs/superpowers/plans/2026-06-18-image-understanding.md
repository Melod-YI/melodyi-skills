# Image Understanding Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-based skill that lets non-multimodal agents understand images by calling an OpenAI-compatible vision API.

**Architecture:** Modular Python scripts under `scripts/` with a provider abstraction pattern. Entry point (`understand_image.py`) orchestrates config loading, image processing, and API calls. Zero third-party dependencies — stdlib only.

**Tech Stack:** Python 3.11+, pytest, stdlib (`urllib`, `json`, `argparse`, `base64`, `pathlib`, `abc`, `mimetypes`)

---

## File Structure

```
image-understanding/
├── pytest.ini                          # pytest config (pythonpath = scripts)
├── SKILL.md                            # Skill documentation
├── scripts/
│   ├── understand_image.py             # CLI entry point
│   ├── config.py                       # Config loader (env > file > defaults)
│   ├── image_utils.py                  # Image load, encode, MIME detect
│   └── providers/
│       ├── __init__.py                 # Provider registry
│       ├── base.py                     # Abstract BaseProvider
│       └── openai_provider.py          # OpenAI Chat Completions impl
└── tests/
    ├── test_config.py
    ├── test_image_utils.py
    ├── test_openai_provider.py
    └── test_understand_image.py
```

---

### Task 1: Project Setup + Provider Base Class

**Files:**
- Create: `pytest.ini`
- Create: `scripts/providers/__init__.py`
- Create: `scripts/providers/base.py`
- Create: `tests/test_base_provider.py`

- [ ] **Step 1: Create project directory structure**

```bash
cd /c/Users/Melodyi/image-understanding
mkdir -p scripts/providers tests
```

- [ ] **Step 2: Write pytest.ini**

```ini
[pytest]
pythonpath = scripts
testpaths = tests
```

- [ ] **Step 3: Write the failing test for BaseProvider**

```python
# tests/test_base_provider.py
import pytest
from providers.base import BaseProvider


class TestBaseProvider:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseProvider()

    def test_concrete_subclass_must_implement_understand(self):
        class IncompleteProvider(BaseProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_concrete_subclass_can_be_instantiated(self):
        class CompleteProvider(BaseProvider):
            def understand(self, image_data, mime_type, prompt):
                return "test result"

        provider = CompleteProvider()
        assert provider.understand("data", "image/png", "describe") == "test result"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_base_provider.py -v`
Expected: FAIL — `ImportError: cannot import 'BaseProvider' from 'providers.base'`

- [ ] **Step 5: Write BaseProvider implementation**

```python
# scripts/providers/base.py
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    @abstractmethod
    def understand(self, image_data: str, mime_type: str, prompt: str) -> str:
        """
        Understand an image and return text result.

        Args:
            image_data: base64 encoded image data
            mime_type: MIME type of the image (e.g. image/png)
            prompt: user custom prompt or default description prompt

        Returns:
            Text description from the model
        """
        pass
```

- [ ] **Step 6: Create empty __init__.py for providers package**

```python
# scripts/providers/__init__.py
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_base_provider.py -v`
Expected: 3 passed

- [ ] **Step 8: Commit**

```bash
cd /c/Users/Melodyi/image-understanding
git add pytest.ini scripts/providers/ tests/test_base_provider.py
git commit -m "feat: add project setup and provider base class"
```

---

### Task 2: Configuration System

**Files:**
- Create: `scripts/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for defaults and config file loading**

```python
# tests/test_config.py
import json
import os
import pytest
from config import load_config


class TestConfigDefaults:
    def test_defaults_with_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("VISION_API_KEY", "test-key-123")
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        config = load_config()
        assert config.api_key == "test-key-123"
        assert config.api_base == "https://api.openai.com/v1"
        assert config.model == "gpt-4o"
        assert config.max_tokens == 1024
        assert config.provider == "openai"

    def test_missing_api_key_raises_error(self, monkeypatch):
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        with pytest.raises(SystemExit):
            load_config()


class TestConfigFile:
    def test_loads_values_from_config_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "api_key": "file-key",
            "model": "gpt-4o-mini",
            "max_tokens": 512
        }))
        config = load_config(config_path=str(config_file))
        assert config.api_key == "file-key"
        assert config.model == "gpt-4o-mini"
        assert config.max_tokens == 512
        assert config.api_base == "https://api.openai.com/v1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ImportError: cannot import 'load_config' from 'config'`

- [ ] **Step 3: Write config.py with defaults and file loading**

```python
# scripts/config.py
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VisionConfig:
    api_key: str
    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    max_tokens: int = 1024
    provider: str = "openai"


_DEFAULTS = {
    "api_base": "https://api.openai.com/v1",
    "model": "gpt-4o",
    "max_tokens": 1024,
    "provider": "openai",
}

_CONFIG_PATHS = [
    "./.image-understanding.json",
    os.path.expanduser("~/.config/image-understanding/config.json"),
]


def _find_config_file(cli_path=None):
    if cli_path:
        return cli_path
    for path in _CONFIG_PATHS:
        if os.path.isfile(path):
            return path
    return None


def _load_from_file(config_path):
    if not config_path:
        return {}
    path = Path(config_path)
    if not path.is_file():
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _load_from_env():
    result = {}
    mapping = {
        "VISION_API_KEY": ("api_key", str),
        "VISION_API_BASE": ("api_base", str),
        "VISION_MODEL": ("model", str),
        "VISION_MAX_TOKENS": ("max_tokens", int),
        "VISION_PROVIDER": ("provider", str),
    }
    for env_var, (key, type_fn) in mapping.items():
        value = os.environ.get(env_var)
        if value is not None and value != "":
            result[key] = type_fn(value)
    return result


def load_config(cli_overrides=None, config_path=None):
    config = dict(_DEFAULTS)

    file_path = _find_config_file(config_path)
    file_values = _load_from_file(file_path)
    config.update(file_values)

    env_values = _load_from_env()
    config.update(env_values)

    if cli_overrides:
        filtered = {k: v for k, v in cli_overrides.items() if v is not None}
        config.update(filtered)

    if "api_key" not in config or not config["api_key"]:
        print(
            "Error: API key not found. Set VISION_API_KEY or create config file.",
            file=sys.stderr,
        )
        sys.exit(1)

    return VisionConfig(**config)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Add tests for env var override and CLI override**

```python
# tests/test_config.py (append these classes)

class TestEnvVarOverride:
    def test_env_var_overrides_config_file(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "api_key": "file-key",
            "model": "gpt-4o-mini"
        }))
        monkeypatch.setenv("VISION_API_KEY", "env-key")
        monkeypatch.setenv("VISION_MODEL", "gpt-4o")
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        config = load_config(config_path=str(config_file))
        assert config.api_key == "env-key"
        assert config.model == "gpt-4o"


class TestCliOverride:
    def test_cli_overrides_take_highest_priority(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "api_key": "file-key",
            "model": "gpt-4o-mini"
        }))
        monkeypatch.setenv("VISION_API_KEY", "env-key")
        monkeypatch.setenv("VISION_MODEL", "env-model")
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        config = load_config(
            cli_overrides={"model": "cli-model", "api_key": "cli-key"},
            config_path=str(config_file),
        )
        assert config.api_key == "cli-key"
        assert config.model == "cli-model"

    def test_none_cli_overrides_are_ignored(self, monkeypatch):
        monkeypatch.setenv("VISION_API_KEY", "env-key")
        monkeypatch.delenv("VISION_API_BASE", raising=False)
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.delenv("VISION_MAX_TOKENS", raising=False)
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        config = load_config(cli_overrides={"model": None, "max_tokens": None})
        assert config.model == "gpt-4o"
```

- [ ] **Step 6: Run all config tests**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_config.py -v`
Expected: 6 passed

- [ ] **Step 7: Commit**

```bash
cd /c/Users/Melodyi/image-understanding
git add scripts/config.py tests/test_config.py
git commit -m "feat: add configuration system with priority chain"
```

---

### Task 3: Image Utilities — Local File Loading

**Files:**
- Create: `scripts/image_utils.py`
- Create: `tests/test_image_utils.py`

- [ ] **Step 1: Write failing tests for local file loading**

```python
# tests/test_image_utils.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_image_utils.py -v`
Expected: FAIL — `ImportError: cannot import 'load_image' from 'image_utils'`

- [ ] **Step 3: Write image_utils.py**

```python
# scripts/image_utils.py
import base64
import sys
import urllib.request
from pathlib import Path


_SUPPORTED_EXTENSIONS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _load_from_url(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
            mime_type = response.getheader("Content-Type", "").split(";")[0].strip()
            if not mime_type:
                mime_type = "image/jpeg"
            return base64.b64encode(data).decode("utf-8"), mime_type
    except Exception as e:
        print(f"Error: Failed to download image: {e}", file=sys.stderr)
        sys.exit(1)


def _load_from_file(file_path):
    path = Path(file_path)
    if not path.is_file():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    ext = path.suffix.lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        supported = ", ".join(
            e.lstrip(".") for e in sorted(_SUPPORTED_EXTENSIONS.keys())
        )
        print(
            f"Error: Unsupported format: {ext}. Supported: {supported}",
            file=sys.stderr,
        )
        sys.exit(1)

    mime_type = _SUPPORTED_EXTENSIONS[ext]
    data = path.read_bytes()
    return base64.b64encode(data).decode("utf-8"), mime_type


def load_image(source):
    """Load image from local path or URL. Returns (base64_data, mime_type)."""
    if source.startswith("http://") or source.startswith("https://"):
        return _load_from_url(source)
    return _load_from_file(source)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_image_utils.py -v`
Expected: 7 passed

- [ ] **Step 5: Add tests for URL loading**

```python
# tests/test_image_utils.py (append this class)

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
```

- [ ] **Step 6: Run all image_utils tests**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_image_utils.py -v`
Expected: 9 passed

- [ ] **Step 7: Commit**

```bash
cd /c/Users/Melodyi/image-understanding
git add scripts/image_utils.py tests/test_image_utils.py
git commit -m "feat: add image utilities with local file and URL loading"
```

---

### Task 4: OpenAI Provider

**Files:**
- Create: `scripts/providers/openai_provider.py`
- Create: `tests/test_openai_provider.py`

- [ ] **Step 1: Write failing test for request body format**

```python
# tests/test_openai_provider.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_openai_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'providers.openai_provider'`

- [ ] **Step 3: Write OpenAIProvider implementation**

```python
# scripts/providers/openai_provider.py
import json
import sys
import urllib.error
import urllib.request
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key, api_base, model, max_tokens):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens

    def _build_request_body(self, image_data, mime_type, prompt):
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            },
                        },
                    ],
                }
            ],
        }

    def understand(self, image_data, mime_type, prompt):
        body = self._build_request_body(image_data, mime_type, prompt)
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                return response_data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            print(
                f"Error: API returned {e.code}: {error_body}",
                file=sys.stderr,
            )
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"Error: API request failed: {e.reason}", file=sys.stderr)
            sys.exit(1)
        except (KeyError, IndexError, json.JSONDecodeError):
            print("Error: Failed to parse API response", file=sys.stderr)
            sys.exit(1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_openai_provider.py -v`
Expected: 1 passed

- [ ] **Step 5: Add tests for error handling**

```python
# tests/test_openai_provider.py (append these classes)

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
```

- [ ] **Step 6: Run all OpenAI provider tests**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_openai_provider.py -v`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
cd /c/Users/Melodyi/image-understanding
git add scripts/providers/openai_provider.py tests/test_openai_provider.py
git commit -m "feat: add OpenAI vision provider"
```

---

### Task 5: Provider Registry

**Files:**
- Modify: `scripts/providers/__init__.py`
- Create: `tests/test_provider_registry.py`

- [ ] **Step 1: Write failing tests for provider registry**

```python
# tests/test_provider_registry.py
import pytest
from providers import get_provider
from providers.openai_provider import OpenAIProvider


class TestProviderRegistry:
    def test_get_openai_provider(self):
        provider = get_provider(
            "openai",
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            model="gpt-4o",
            max_tokens=1024,
        )
        assert isinstance(provider, OpenAIProvider)

    def test_unknown_provider_raises_system_exit(self):
        with pytest.raises(SystemExit):
            get_provider(
                "unknown_provider",
                api_key="test-key",
                api_base="https://api.openai.com/v1",
                model="gpt-4o",
                max_tokens=1024,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_provider_registry.py -v`
Expected: FAIL — `ImportError: cannot import 'get_provider' from 'providers'`

- [ ] **Step 3: Write provider registry in __init__.py**

```python
# scripts/providers/__init__.py
import sys
from .openai_provider import OpenAIProvider

_PROVIDERS = {
    "openai": OpenAIProvider,
}


def get_provider(name, **kwargs):
    provider_class = _PROVIDERS.get(name)
    if provider_class is None:
        available = ", ".join(sorted(_PROVIDERS.keys()))
        print(
            f"Error: Unknown provider '{name}'. Available: {available}",
            file=sys.stderr,
        )
        sys.exit(1)
    return provider_class(**kwargs)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_provider_registry.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Melodyi/image-understanding
git add scripts/providers/__init__.py tests/test_provider_registry.py
git commit -m "feat: add provider registry"
```

---

### Task 6: CLI Entry Point + Integration

**Files:**
- Create: `scripts/understand_image.py`
- Create: `tests/test_understand_image.py`

- [ ] **Step 1: Write failing tests for argument parsing**

```python
# tests/test_understand_image.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_understand_image.py -v`
Expected: FAIL — `ImportError: cannot import 'parse_args' from 'understand_image'`

- [ ] **Step 3: Write understand_image.py with argument parsing and main flow**

```python
# scripts/understand_image.py
import argparse
import sys

from config import load_config
from image_utils import load_image
from providers import get_provider

DEFAULT_PROMPT = "Describe this image in detail."


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Understand an image using a vision-capable API."
    )
    parser.add_argument("image_source", help="Local file path or URL of the image")
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help=f"Custom question about the image (default: '{DEFAULT_PROMPT}')",
    )
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--provider", help="Override provider from config")
    parser.add_argument("--model", help="Override model from config")
    parser.add_argument(
        "--max-tokens", type=int, help="Override max_tokens from config"
    )
    return parser.parse_args(args)


def main(args=None):
    parsed = parse_args(args)

    cli_overrides = {
        "provider": parsed.provider,
        "model": parsed.model,
        "max_tokens": parsed.max_tokens,
    }
    config = load_config(
        cli_overrides=cli_overrides,
        config_path=parsed.config,
    )

    image_data, mime_type = load_image(parsed.image_source)

    provider = get_provider(
        config.provider,
        api_key=config.api_key,
        api_base=config.api_base,
        model=config.model,
        max_tokens=config.max_tokens,
    )

    result = provider.understand(image_data, mime_type, parsed.prompt)
    print(result)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_understand_image.py -v`
Expected: 3 passed

- [ ] **Step 5: Add integration test for main() with mocked provider**

```python
# tests/test_understand_image.py (append this class)

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
```

- [ ] **Step 6: Run all tests**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/test_understand_image.py -v`
Expected: 6 passed

- [ ] **Step 7: Run full test suite**

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/ -v`
Expected: All tests pass (19 tests total)

- [ ] **Step 8: Commit**

```bash
cd /c/Users/Melodyi/image-understanding
git add scripts/understand_image.py tests/test_understand_image.py
git commit -m "feat: add CLI entry point with argument parsing and integration"
```

---

### Task 7: SKILL.md Documentation

**Files:**
- Create: `SKILL.md`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: image-understanding
description: Use when you need to understand, analyze, or describe images but your model does not support multimodal input.
---

# Image Understanding

Enables non-multimodal agents to understand images by calling an external vision-capable API (OpenAI-compatible format).

## When to Use

- Need to describe what's in a screenshot, photo, or diagram
- Need to analyze charts, graphs, or data visualizations
- Need to understand UI layouts or wireframes
- Need to extract text from images (OCR-like description)
- Your current model does not support image/vision input

## Prerequisites

Configure an API key for a vision-capable model. Set the `VISION_API_KEY` environment variable, or create a config file.

## Quick Reference

```bash
# Describe an image
python scripts/understand_image.py ./screenshot.png

# Ask a specific question
python scripts/understand_image.py ./chart.jpg --prompt "What trend does this chart show?"

# Use a URL
python scripts/understand_image.py https://example.com/image.png

# Override model
python scripts/understand_image.py ./photo.png --model gpt-4o-mini
```

## Configuration

Priority: CLI arguments > environment variables > config file > defaults.

| Setting | Env Var | Config Key | Default |
|---------|---------|------------|---------|
| API Key | `VISION_API_KEY` | `api_key` | (required) |
| Base URL | `VISION_API_BASE` | `api_base` | `https://api.openai.com/v1` |
| Model | `VISION_MODEL` | `model` | `gpt-4o` |
| Max Tokens | `VISION_MAX_TOKENS` | `max_tokens` | `1024` |
| Provider | `VISION_PROVIDER` | `provider` | `openai` |

Config file locations (checked in order):
1. `--config <path>` (CLI argument)
2. `./.image-understanding.json` (current directory)
3. `~/.config/image-understanding/config.json` (home directory)

Config file format:
```json
{
  "api_key": "sk-xxx",
  "api_base": "https://api.openai.com/v1",
  "model": "gpt-4o",
  "max_tokens": 1024,
  "provider": "openai"
}
```

## Examples

**Describe a screenshot:**
```bash
python scripts/understand_image.py ./ui-screenshot.png
# Output: "The screenshot shows a login form with email and password fields..."
```

**Analyze a chart:**
```bash
python scripts/understand_image.py https://example.com/chart.png --prompt "Summarize the data trends in this chart"
# Output: "The chart shows an upward trend in revenue from Q1 to Q3..."
```

**Use with a compatible third-party API:**
```bash
VISION_API_KEY=your-key VISION_API_BASE=https://other-api.com/v1 python scripts/understand_image.py ./photo.png
```

## Common Mistakes

| Problem | Solution |
|---------|----------|
| "API key not found" error | Set `VISION_API_KEY` env var or create a config file |
| "File not found" error | Check the image path is correct and the file exists |
| "Unsupported format" error | Use PNG, JPG, GIF, or WebP format |
| API timeout | Check your network connection and API base URL |
| Wrong model response | Verify the model name supports vision (e.g., gpt-4o, gpt-4o-mini) |
```

- [ ] **Step 2: Commit**

```bash
cd /c/Users/Melodyi/image-understanding
git add SKILL.md
git commit -m "docs: add SKILL.md documentation"
```

- [ ] **Step 3: End-to-end smoke test**

Run: `cd /c/Users/Melodyi/image-understanding && python scripts/understand_image.py --help`
Expected: Shows usage information with all arguments listed.

Run: `cd /c/Users/Melodyi/image-understanding && python -m pytest tests/ -v`
Expected: All 19 tests pass.

- [ ] **Step 4: Final commit (all files)**

```bash
cd /c/Users/Melodyi/image-understanding
git add -A
git status
git commit -m "chore: final project structure"
```
