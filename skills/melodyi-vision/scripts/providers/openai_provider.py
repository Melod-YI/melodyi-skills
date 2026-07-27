"""OpenAI Chat Completions vision provider."""
import json
import sys
import urllib.error
import urllib.request

from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """Sends images to the OpenAI Chat Completions API for analysis.

    默认使用流式（SSE）调用：在请求体中置 ``stream: true``，逐块解析
    ``choices[0].delta.content`` 并在内部累加，最终返回完整文本。流式可降低首
    token 延迟并避免长输出超时。若 ``stream=False`` 则退回一次性返回的普通调用。
    """

    def __init__(self, api_key: str, api_base: str, model: str, max_tokens: int,
                 stream: bool = True):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.stream = stream

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
        if self.stream:
            body["stream"] = True
        encoded_body = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                # 流式响应为 SSE 文本流，显式声明避免某些代理/网关缓冲整包
                "Accept": "text/event-stream" if self.stream else "application/json",
            },
            method="POST",
        )

        try:
            resp = urllib.request.urlopen(req, data=encoded_body, timeout=120)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            print(f"Error: API returned {exc.code}: {error_body}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as exc:
            print(f"Error: API request failed: {exc.reason}", file=sys.stderr)
            sys.exit(1)

        if self.stream:
            return self._read_stream(resp)
        return self._read_non_stream(resp)

    def _read_non_stream(self, resp) -> str:
        """一次性读取并解析非流式 JSON 响应。"""
        try:
            with resp:
                raw = resp.read()
        except urllib.error.URLError as exc:
            print(f"Error: API response read failed: {exc.reason}", file=sys.stderr)
            sys.exit(1)

        try:
            data = json.loads(raw)
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            print("Error: Failed to parse API response", file=sys.stderr)
            sys.exit(1)

    def _read_stream(self, resp) -> str:
        """读取 SSE 流，累加每个 chunk 的 ``delta.content``，返回完整文本。

        OpenAI 兼容的 SSE 每行形如 ``data: {json}``，``delta.content`` 为本块增量
        文本；流以 ``data: [DONE]`` 结束。空内容（如仅含 role 的首块）的 delta
        不含 content 字段，跳过即可。
        """
        chunks = []
        try:
            with resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                    # 空行（SSE 事件分隔）或非 data 行（注释/心跳）忽略
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        payload = json.loads(data)
                    except json.JSONDecodeError:
                        # 跳过无法解析的行，避免单块异常中断整段输出
                        continue
                    try:
                        delta = payload["choices"][0]["delta"]
                        content = delta.get("content")
                    except (KeyError, IndexError, TypeError):
                        content = None
                    if content:
                        chunks.append(content)
        except urllib.error.URLError as exc:
            print(f"Error: API stream read failed: {exc.reason}", file=sys.stderr)
            sys.exit(1)

        result = "".join(chunks)
        if not result:
            print("Error: API stream returned empty content", file=sys.stderr)
            sys.exit(1)
        return result
