"""PR 链接解析：从 GitCode PR URL 提取 owner / repo / number

支持的 URL 格式：
  - https://gitcode.net/{owner}/{repo}/-/merge_requests/{n}
  - https://gitcode.com/{owner}/{repo}/pulls/{n}
  - https://gitcode.com/{owner}/{repo}/-/merge_requests/{n}

URL 尾部可带 /diffs 等后缀，number 取路径中对应的数字段。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class PRRef:
    """PR 定位三元组"""
    owner: str
    repo: str
    number: str


class UrlParseError(ValueError):
    """PR 链接无法解析"""


# owner/repo 路径段（owner、repo 均允许字母数字._-）
_SEG = r"[A-Za-z0-9._-]+"

# 三种合法路径形态
_PATTERNS = [
    re.compile(rf"^/(?:.*/)?({_SEG})/({_SEG})/-/merge_requests/(\d+)(?:/.*)?$"),
    re.compile(rf"^/(?:.*/)?({_SEG})/({_SEG})/pulls/(\d+)(?:/.*)?$"),
]

_ALLOWED_HOSTS = {"gitcode.com", "gitcode.net"}


def parse_pr_url(url: str) -> PRRef:
    """解析 GitCode PR 链接，返回 PRRef(owner, repo, number)

    Raises:
        UrlParseError: 域名非 gitcode、路径不匹配 PR 形态、或无 number。
    """
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise UrlParseError(f"非 GitCode 域名: {host or '空'}")

    path = parsed.path
    for pat in _PATTERNS:
        m = pat.match(path)
        if m:
            owner, repo, number = m.group(1), m.group(2), m.group(3)
            return PRRef(owner=owner, repo=repo, number=number)

    raise UrlParseError(f"无法从 URL 解析 owner/repo/number: {url}")
