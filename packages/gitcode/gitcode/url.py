"""PR 链接解析：从 GitCode PR URL 提取 owner / repo / number

支持的 URL 格式：
  - https://gitcode.net/{owner}/{repo}/-/merge_requests/{n}
  - https://gitcode.com/{owner}/{repo}/pulls/{n}
  - https://gitcode.com/{owner}/{repo}/-/merge_requests/{n}
  - https://gitcode.com/{owner}/{repo}/merge_requests/{n}   （API html_url 实际形态，无 -/）

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


@dataclass(frozen=True)
class RepoRef:
    """仓库定位二元组"""
    owner: str
    repo: str


class UrlParseError(ValueError):
    """PR 链接无法解析"""


# owner/repo 路径段（owner、repo 均允许字母数字._-）
_SEG = r"[A-Za-z0-9._-]+"

# 合法路径形态。-/merge_requests 形态必须排在 merge_requests 之前，
# 否则 -（合法段字符）会被无 -/ 模式错配为 repo。
_PATTERNS = [
    re.compile(rf"^/(?:.*/)?({_SEG})/({_SEG})/-/merge_requests/(\d+)(?:/.*)?$"),
    re.compile(rf"^/(?:.*/)?({_SEG})/({_SEG})/merge_requests/(\d+)(?:/.*)?$"),
    re.compile(rf"^/(?:.*/)?({_SEG})/({_SEG})/pulls/(\d+)(?:/.*)?$"),
]

# 仓库首页形态：/{owner}/{repo}，取路径前两段，尾部可带 /、/-/...、子路径
_REPO_PATTERN = re.compile(rf"^/({_SEG})/({_SEG})(?:/.*)?$")

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


def parse_repo_url(url: str) -> RepoRef:
    """解析 GitCode 仓库首页链接，返回 RepoRef(owner, repo)

    支持形态：https://gitcode.com/{owner}/{repo}，尾部可带 /、/-/...、子路径、.git。
    仓库段尾部 .git 会被去除。

    Raises:
        UrlParseError: 域名非 gitcode、路径不足 owner/repo 两段。
    """
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise UrlParseError(f"非 GitCode 域名: {host or '空'}")

    m = _REPO_PATTERN.match(parsed.path)
    if not m:
        raise UrlParseError(f"无法从 URL 解析 owner/repo: {url}")
    owner, repo = m.group(1), m.group(2)
    if repo.endswith(".git"):
        repo = repo[:-4]
    return RepoRef(owner=owner, repo=repo)
