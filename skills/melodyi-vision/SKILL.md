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
