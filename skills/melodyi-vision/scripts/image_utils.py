import base64
import ssl
import sys
import urllib.request
from pathlib import Path


SUPPORTED_FORMATS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def load_image(source, verify_ssl: bool = True, proxy: str = None):
    """Load an image from a local file or URL.

    Args:
        source: 本地文件路径或图片 URL。
        verify_ssl: 下载 URL 图片时是否校验 SSL（默认校验）。
        proxy: HTTP 代理地址；None 表示未配置，走 urllib 默认行为。

    Returns a (base64_data, mime_type) tuple.
    """
    if source.startswith("http://") or source.startswith("https://"):
        return _load_from_url(source, verify_ssl=verify_ssl, proxy=proxy)
    else:
        return _load_from_file(source)


def _load_from_file(path_str):
    path = Path(path_str)
    if not path.exists():
        print(f"Error: File not found: {path_str}", file=sys.stderr)
        sys.exit(1)

    ext = path.suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(ext.lstrip(".") for ext in SUPPORTED_FORMATS))
        print(
            f"Error: Unsupported format: {ext.lstrip('.')}. Supported: {supported}",
            file=sys.stderr,
        )
        sys.exit(1)

    content = path.read_bytes()
    b64_data = base64.b64encode(content).decode("utf-8")
    return b64_data, SUPPORTED_FORMATS[ext]


def _load_from_url(url, verify_ssl: bool = True, proxy: str = None):
    try:
        if proxy is None:
            # 未配置代理：直接 urlopen（保持默认行为，与既有测试 monkeypatch 点兼容）
            # verify_ssl=True 时 context 为 None，不传 context kwarg，保持 urllib 默认校验行为
            context = None if verify_ssl else ssl._create_unverified_context()
            if context is None:
                response_ctx = urllib.request.urlopen(url, timeout=30)
            else:
                response_ctx = urllib.request.urlopen(url, timeout=30, context=context)
        else:
            # 配置了代理：经 ProxyHandler 构造 opener；opener.open 不接受
            # context kwarg，关闭 SSL 校验场景经 HTTPSHandler 挂进 opener
            handlers = [
                urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            ]
            context = None if verify_ssl else ssl._create_unverified_context()
            if context is not None:
                handlers.append(urllib.request.HTTPSHandler(context=context))
            opener = urllib.request.build_opener(*handlers)
            response_ctx = opener.open(url, timeout=30)
        with response_ctx as response:
            content = response.read()
            mime_type = response.getheader("Content-Type", "")
    except Exception as e:
        print(f"Error: Failed to download image: {e}", file=sys.stderr)
        sys.exit(1)

    b64_data = base64.b64encode(content).decode("utf-8")
    return b64_data, mime_type
