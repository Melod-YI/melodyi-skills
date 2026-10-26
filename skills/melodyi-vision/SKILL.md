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
| 流式调用 | `VISION_STREAM` | `stream` | `true` |
| SSL 校验 | `VISION_VERIFY_SSL` | `verify_ssl` | `true` |
| HTTP 代理 | —（无环境变量） | `proxy` | (无) |
| 当前供应商 | `VISION_ACTIVE_PROVIDER` | `active_provider` | (无) |

Config file locations (checked in order; all resolved independent of the current working directory — you can run the script from any drive/directory):
1. `--config <path>` (CLI argument)
2. `~/.melodyi-skills/melodyi-vision/config.json` (user-private config under home directory; preferred for real keys)
3. `scripts/config.json` next to the script (bundled **example** with a placeholder key; used only as a fallback when no user config exists, located relative to `understand_image.py`, not cwd)

The bundled `scripts/config.json` has a placeholder key `sk-your-api-key-here` — it loads successfully but the API call will fail until replaced. For persistent private use, copy it to `~/.melodyi-skills/melodyi-vision/config.json` and edit there (the user-dir file takes precedence over the bundled example, so secrets stay out of the repo).

Config file format:
```json
{
  "api_key": "sk-xxx",
  "api_base": "https://api.openai.com/v1",
  "model": "gpt-4o",
  "max_tokens": 1024,
  "provider": "openai",
  "stream": true,
  "verify_ssl": true,
  "proxy": "http://127.0.0.1:7890"
}
```

> **流式调用**：默认 `stream: true`，以 SSE 方式请求并在内部累加 `delta.content` 后返回完整文本，可降低首 token 延迟、避免长输出超时。若上游 API 不支持流式或需一次性返回，可经 `VISION_STREAM=false`、配置文件 `"stream": false` 或 CLI `--no-stream` 切回非流式。

> **SSL 校验**：默认 `verify_ssl: true` 校验 HTTPS 证书。仅在内网自签名证书、自托管网关等场景下设为 `false` 关闭校验。

> **HTTP 代理**：可选配置 `"proxy": "http://127.0.0.1:7890"`，配置后 API 调用与 URL 图片下载的 http/https 请求统一走该代理；未配置时走 urllib 默认行为（可读 `HTTP_PROXY`/`HTTPS_PROXY` 环境变量），不设专用环境变量。

### 多供应商配置（推荐）

所有 OpenAI 兼容接口都复用同一 provider 实现，可在 `providers` 里保留多份配置，通过改 `active_provider` 一个字段切换供应商：
```json
{
  "active_provider": "openrouter",
  "verify_ssl": true,
  "stream": true,
  "max_tokens": 4096,
  "providers": {
    "openrouter": {
      "api_key": "sk-or-xxx",
      "api_base": "https://openrouter.ai/api/v1/",
      "model": "xiaomi/mimo-v2.5",
      "max_tokens": 102400
    },
    "openai": {
      "api_key": "sk-xxx",
      "api_base": "https://api.openai.com/v1",
      "model": "gpt-4o",
      "stream": false
    }
  }
}
```
- 切换供应商 = 改 `active_provider` 为 `providers` 里的某个 key。
- 每个 profile 含 `api_key`/`api_base`/`model`（必须各不相同）；`max_tokens`/`stream` 可 per-profile 覆盖，缺省回退顶层默认（不同模型限额不同，建议在 profile 里各自指定 `max_tokens`）。
- `verify_ssl`/`provider`/`proxy` 为全局共享，不 per-profile。
- 兼容旧配置：无 `providers` 段时回退上面的扁平结构。

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
