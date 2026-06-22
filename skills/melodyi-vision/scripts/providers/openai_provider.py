"""OpenAI Chat Completions vision provider."""
import json
import sys
import urllib.error
import urllib.request

from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """Sends images to the OpenAI Chat Completions API for analysis."""

    def __init__(self, api_key: str, api_base: str, model: str, max_tokens: int):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens

    def _build_request_body(self, image_data: str, mime_type: str, prompt: str) -> dict:
        """Build the JSON payload for the OpenAI Chat Completions endpoint."""
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

    def understand(self, image_data: str, mime_type: str, prompt: str) -> str:
        """Analyze an image via the OpenAI Chat Completions API.

        Args:
            image_data: Base64-encoded image bytes.
            mime_type:  MIME type of the image (e.g. ``image/png``).
            prompt:     A text prompt guiding what to describe.

        Returns:
            A textual description of the image.
        """
        url = f"{self.api_base}/chat/completions"
        body = self._build_request_body(image_data, mime_type, prompt)
        encoded_body = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, data=encoded_body, timeout=120) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            print(f"Error: API returned {exc.code}: {error_body}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as exc:
            print(f"Error: API request failed: {exc.reason}", file=sys.stderr)
            sys.exit(1)

        try:
            data = json.loads(raw)
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            print("Error: Failed to parse API response", file=sys.stderr)
            sys.exit(1)
