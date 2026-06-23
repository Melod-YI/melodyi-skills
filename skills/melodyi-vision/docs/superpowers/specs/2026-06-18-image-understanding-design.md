# Image Understanding Skill Design

## Overview

A skill that enables non-multimodal agents to understand images by calling an external vision-capable API. The skill provides a Python script that agents invoke via Bash, passing an image source (local path or URL) and optionally a custom prompt. The script returns a text description of the image to stdout.

The first version supports the standard OpenAI Chat Completions API format. The code structure is designed to allow additional providers in the future without modifying existing code.

## Architecture

### Data Flow

```
Agent invokes via Bash
    │
    ▼
understand_image.py (entry point)
    │
    ├── Parse CLI arguments (image source, optional prompt)
    │
    ├── config.py loads configuration
    │   └── CLI args → env vars → config file → defaults
    │
    ├── image_utils.py processes image
    │   ├── Local file → read → base64 encode
    │   └── URL → download → base64 encode
    │
    ├── providers/openai_provider.py builds request
    │   └── Assembles OpenAI Chat Completions format
    │       (messages with image_url + text prompt)
    │
    ├── Send HTTP POST request → receive response
    │
    └── Output result to stdout
        └── Agent reads output and continues work
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `understand_image.py` | Entry point, argument parsing, orchestration, output |
| `config.py` | Load configuration from env vars, config file, or defaults |
| `image_utils.py` | Image reading, URL downloading, base64 encoding, MIME type detection |
| `providers/base.py` | Define `BaseProvider` abstract interface |
| `providers/openai_provider.py` | Implement OpenAI Chat Completions API call |

### Dependencies

Only Python standard library: `urllib`, `json`, `argparse`, `base64`, `os`, `pathlib`, `abc`, `mimetypes`. No third-party packages required.

## Directory Structure

```
image-understanding/
  SKILL.md                    # Skill documentation + usage guide
  scripts/
    understand_image.py       # Entry point script
    config.py                 # Configuration loader
    image_utils.py            # Image handling utilities
    providers/
      __init__.py             # Provider registry
      base.py                 # Abstract base class
      openai_provider.py      # OpenAI format implementation
```

## Configuration System

### Priority Chain

CLI arguments > environment variables > config file > defaults.

### Configuration Items

| Item | Env Var | Config Key | Default |
|------|---------|------------|---------|
| API Key | `VISION_API_KEY` | `api_key` | None (required) |
| API Base URL | `VISION_API_BASE` | `api_base` | `https://api.openai.com/v1` |
| Model | `VISION_MODEL` | `model` | `gpt-4o` |
| Max Tokens | `VISION_MAX_TOKENS` | `max_tokens` | `1024` |
| Provider | `VISION_PROVIDER` | `provider` | `openai` |

### Config File Lookup Order

1. CLI argument `--config <path>` (if specified)
2. Current directory `./.image-understanding.json`
3. User home `~/.config/image-understanding/config.json`

### Config File Format

```json
{
  "api_key": "sk-xxx",
  "api_base": "https://api.openai.com/v1",
  "model": "gpt-4o",
  "max_tokens": 1024,
  "provider": "openai"
}
```

### Missing API Key Behavior

Script exits with non-zero exit code. stderr outputs a clear error message instructing the user to set `VISION_API_KEY` or create a config file.

## Provider Abstraction

### Base Class (`providers/base.py`)

```python
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

### OpenAI Provider Implementation (`providers/openai_provider.py`)

Builds a standard Chat Completions request body:

```json
{
  "model": "gpt-4o",
  "max_tokens": 1024,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "<prompt>"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:<mime_type>;base64,<image_data>"
          }
        }
      ]
    }
  ]
}
```

- Uses `urllib.request` to send POST to `{api_base}/chat/completions`
- Parses response, extracts `choices[0].message.content`
- Request headers include `Authorization: Bearer {api_key}` and `Content-Type: application/json`

### Extension Pattern

Adding a new provider requires:

1. Create a new file in `providers/` inheriting from `BaseProvider`
2. Implement the `understand` method
3. Register the new provider in `providers/__init__.py`
4. Select via `provider` config field or `--provider` CLI argument

No changes to existing provider code needed.

## Image Handling (`image_utils.py`)

### Input Detection

- Starts with `http://` or `https://` → URL mode
- Otherwise → local file path

### URL Mode

- Download image using `urllib.request.urlopen`
- Extract MIME type from response `Content-Type` header
- Read response body and base64 encode
- Timeout: 30 seconds

### Local File Mode

- Validate file exists using `pathlib.Path`
- Infer MIME type from file extension (png, jpg/jpeg, gif, webp)
- Read file contents and base64 encode
- Supported formats: PNG, JPEG, GIF, WebP (aligned with OpenAI API support)

### Interface

```python
def load_image(source: str) -> tuple[str, str]:
    """Returns (base64_encoded_data, mime_type)"""
```

## CLI Interface (`understand_image.py`)

### Usage

```bash
python scripts/understand_image.py <image_source> [options]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `image_source` | positional | yes | Local path or URL |
| `--prompt` | optional | no | Custom question. Default: "Describe this image in detail." |
| `--config` | optional | no | Path to config file |
| `--provider` | optional | no | Override provider from config |
| `--model` | optional | no | Override model from config |
| `--max-tokens` | optional | no | Override max_tokens from config |

### Output

- Success: model's text description printed to stdout
- Failure: error message printed to stderr, non-zero exit code

### Examples

```bash
# Default description
python scripts/understand_image.py ./screenshot.png

# Custom prompt
python scripts/understand_image.py https://example.com/chart.jpg --prompt "What trends does this chart show?"

# With config file and model override
python scripts/understand_image.py ./photo.png --config ./my-config.json --model gpt-4o-mini
```

## Error Handling

| Error Type | Behavior |
|------------|----------|
| Missing API Key | stderr: "Error: API key not found. Set VISION_API_KEY or create config file.", exit 1 |
| Image file not found | stderr: "Error: File not found: <path>", exit 1 |
| Unsupported image format | stderr: "Error: Unsupported format: <ext>. Supported: png, jpg, gif, webp", exit 1 |
| URL download failure | stderr: "Error: Failed to download image: <reason>", exit 1 |
| API network failure | stderr: "Error: API request failed: <reason>", exit 1 |
| API error status code | stderr: "Error: API returned <status>: <message>", exit 1 |
| Response parse failure | stderr: "Error: Failed to parse API response", exit 1 |

All errors go to stderr. stdout is reserved for successful results only. Agents can determine success/failure via exit code.

## SKILL.md Structure

### Frontmatter

```yaml
---
name: image-understanding
description: Use when you need to understand, analyze, or describe images but your model does not support multimodal input.
---
```

### Sections

1. **Overview** — One-line: enables non-multimodal agents to understand images via external vision API
2. **When to Use** — Trigger scenarios: describing screenshots, analyzing charts, understanding UI designs, etc.
3. **Prerequisites** — API key configuration required (env var or config file)
4. **Quick Reference** — Common commands cheat sheet
5. **Configuration** — How to configure (env vars, config file, CLI overrides)
6. **Examples** — 2-3 typical usage scenarios
7. **Common Mistakes** — Frequent issues (forgot API key, wrong path, unsupported format)
