import base64
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


def load_image(source):
    """Load an image from a local file or URL.

    Returns a (base64_data, mime_type) tuple.
    """
    if source.startswith("http://") or source.startswith("https://"):
        return _load_from_url(source)
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


def _load_from_url(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read()
            mime_type = response.getheader("Content-Type", "")
    except Exception as e:
        print(f"Error: Failed to download image: {e}", file=sys.stderr)
        sys.exit(1)

    b64_data = base64.b64encode(content).decode("utf-8")
    return b64_data, mime_type
