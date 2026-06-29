# gitcode skill 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把源 skill 中 agent 直接 curl GitCode API + 读 config 取 token 的操作，封装成可安装的 `packages/gitcode` CLI 包，并提供 `skills/gitcode-pr-review` 轻量 skill 调用它。

**Architecture:** 扁平布局的 Python 包（同 `melodyi-filebot`），`click` 命令组提供 6 个子命令（user/pr/files/comments/comment/resolve），`httpx` 封装 GitCode v5 API，token 在包内部按 env > config.json 读取、经 `Authorization: Bearer` 头发送，绝不暴露给 agent。stdout 输出 JSON，stderr 输出日志，退出码区分成功/业务错误/token 缺失。

**Tech Stack:** Python >=3.10、click>=8.0、httpx>=0.25、pytest、httpx.MockTransport

参考样板：`packages/melodyi-filebot/`（扁平布局、click group + `--verbose`、`config.py` env>config、`_report_error` 友好报错）。

约定：
- 文档/注释/提交信息用中文，标识符用英文
- 日志默认仅 ERROR（静默），`--verbose/-v` 输出 INFO
- 业务错误用 `click.echo(err=True)` + 退出码，非 traceback

---

## 文件结构

```
packages/gitcode/
  pyproject.toml              # 包定义；入口 gitcode=gitcode.cli:cli；依赖 click、httpx
  gitcode/
    __init__.py               # __version__
    __main__.py               # python -m gitcode 支持
    cli.py                    # click 命令组 + 6 个子命令；日志配置；友好报错
    config.py                 # CONFIG_PATH 常量 + load_token(config_path=None)
    api.py                    # API_BASE、APIError、GitCodeClient
    url.py                    # PRRef + parse_pr_url() + UrlParseError
  tests/
    test_url.py
    test_config.py
    test_api.py
    test_cli.py
skills/gitcode-pr-review/
  SKILL.md                    # 检视+验收 使用手册，调用 gitcode CLI
```

接口约定（全计划一致，勿改名）：

- `url.py`：`PRRef(owner: str, repo: str, number: str)`、`parse_pr_url(url: str) -> PRRef`、`UrlParseError(ValueError)`
- `config.py`：`CONFIG_PATH: Path`、`load_token(config_path: Optional[Path] = None) -> Optional[str]`
- `api.py`：`API_BASE = "https://api.gitcode.com/api/v5"`、`APIError(Exception)`（属性 `status_code`、`message`）、`GitCodeClient(token: str, transport=None)`，方法：
  - `get_user() -> dict`
  - `get_pr(owner, repo, number) -> dict`
  - `get_files(owner, repo, number) -> list`
  - `get_comments(owner, repo, number) -> list`
  - `post_comment(owner, repo, number, *, body, path, position, commit_id=None) -> dict`
  - `resolve_comment(owner, repo, number, discussion_id, *, resolved=True) -> dict`
- `cli.py`：`cli`（click group，选项 `--config PATH`、`--verbose/-v`），子命令 `user / pr / files / comments / comment / resolve`

---

## Task 1: 脚手架与包安装

**Files:**
- Create: `packages/gitcode/pyproject.toml`
- Create: `packages/gitcode/gitcode/__init__.py`
- Create: `packages/gitcode/gitcode/__main__.py`
- Create: `packages/gitcode/gitcode/cli.py`（仅 group 骨架）
- Create: `packages/gitcode/gitcode/config.py`（空占位，后续 Task 3 填充）
- Create: `packages/gitcode/gitcode/api.py`（空占位）
- Create: `packages/gitcode/gitcode/url.py`（空占位）

- [ ] **Step 1: 写 pyproject.toml**

```toml
[project]
name = "gitcode"
version = "0.1.0"
description = "GitCode PR 代码检视 CLI：封装 GitCode API 调用与 token 管理"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "httpx>=0.25",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]

[project.scripts]
gitcode = "gitcode.cli:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["gitcode"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 写 __init__.py**

```python
"""gitcode: GitCode PR 代码检视 CLI"""

__version__ = "0.1.0"
```

- [ ] **Step 3: 写 __main__.py**

```python
"""支持 python -m gitcode 调用"""

from gitcode.cli import cli

if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: 写 cli.py 骨架**

```python
"""CLI 命令行入口

子命令：user / pr / files / comments / comment / resolve

日志风格参考 melodyi-filebot：默认静默（仅 ERROR），--verbose/-v 输出 INFO；
业务错误用 click.echo(err=True) + sys.exit 友好报错，非 traceback。
"""

from __future__ import annotations

import json
import logging
import sys

import click

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    """配置日志：默认仅 ERROR（静默），--verbose 输出 INFO 级日志"""
    level = logging.INFO if verbose else logging.ERROR
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(level)


def _print_json(data) -> None:
    """把结构化结果以 UTF-8 JSON 输出到 stdout（ensure_ascii=False 保留中文）"""
    click.echo(json.dumps(data, ensure_ascii=False, indent=2))


@click.group()
@click.version_option(package_name="gitcode", prog_name="gitcode")
@click.option("--config", "config_path", type=click.Path(exists=False), default=None,
              help="配置文件路径（默认 ~/.melodyi-skills/gitcode/config.json）")
@click.option("--verbose", "-v", is_flag=True, help="输出详细日志（默认仅输出错误）")
def cli(config_path, verbose):
    """gitcode: GitCode PR 代码检视 CLI"""
    _configure_logging(verbose)


if __name__ == "__main__":
    cli()
```

- [ ] **Step 5: 写空占位模块**（config.py / api.py / url.py 各放一个模块文档字符串，后续 task 填充）

`packages/gitcode/gitcode/url.py`：
```python
"""PR 链接解析：从 GitCode PR URL 提取 owner / repo / number"""
```
`packages/gitcode/gitcode/config.py`：
```python
"""配置读取：token 优先级 环境变量 GITCODE_TOKEN > ~/.melodyi-skills/gitcode/config.json"""
```
`packages/gitcode/gitcode/api.py`：
```python
"""GitCode v5 API 客户端：httpx 封装，token 经 Authorization: Bearer 头发送"""
```

- [ ] **Step 6: 安装并验证**

Run: `pip install -e packages/gitcode`
Then: `gitcode --help`
Expected: 输出 usage 与 group 选项 `--config`、`--verbose`，退出码 0。

- [ ] **Step 7: Commit**

```bash
git add packages/gitcode
git commit -m "feat(gitcode): 初始化 gitcode CLI 包骨架"
```

---

## Task 2: PR 链接解析 url.parse_pr_url

**Files:**
- Create: `packages/gitcode/tests/test_url.py`
- Modify: `packages/gitcode/gitcode/url.py`

- [ ] **Step 1: 写失败测试**

`packages/gitcode/tests/test_url.py`：
```python
"""parse_pr_url 单元测试"""

import pytest

from gitcode.url import PRRef, parse_pr_url, UrlParseError


@pytest.mark.parametrize("url,expected", [
    ("https://gitcode.net/owner/repo/-/merge_requests/123",
     PRRef("owner", "repo", "123")),
    ("https://gitcode.com/owner/repo/pulls/456",
     PRRef("owner", "repo", "456")),
    ("https://gitcode.com/owner/repo/-/merge_requests/789",
     PRRef("owner", "repo", "789")),
    ("https://gitcode.com/owner/repo/-/merge_requests/789/diffs",
     PRRef("owner", "repo", "789")),
    ("http://gitcode.com/Owner/Repo.Name/-/merge_requests/1",
     PRRef("Owner", "Repo.Name", "1")),
])
def test_parse_pr_url_valid(url, expected):
    assert parse_pr_url(url) == expected


@pytest.mark.parametrize("url", [
    "not a url",
    "https://gitcode.com/owner/repo",          # 无 number
    "https://gitcode.com/owner/repo/issues/1", # 非 PR 路径
    "https://example.com/owner/repo/pulls/1",  # 非 gitcode 域名
])
def test_parse_pr_url_invalid(url):
    with pytest.raises(UrlParseError):
        parse_pr_url(url)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest packages/gitcode/tests/test_url.py -v`
Expected: FAIL（`ImportError` 或函数未实现）

- [ ] **Step 3: 实现 url.py**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest packages/gitcode/tests/test_url.py -v`
Expected: PASS（全部用例）

- [ ] **Step 5: Commit**

```bash
git add packages/gitcode/gitcode/url.py packages/gitcode/tests/test_url.py
git commit -m "feat(gitcode): 实现 PR 链接解析 parse_pr_url"
```

---

## Task 3: token 读取 config.load_token

**Files:**
- Create: `packages/gitcode/tests/test_config.py`
- Modify: `packages/gitcode/gitcode/config.py`

- [ ] **Step 1: 写失败测试**

`packages/gitcode/tests/test_config.py`：
```python
"""load_token 单元测试：优先级 env > config 文件"""

import json

from gitcode.config import load_token


def test_env_takes_priority(monkeypatch, tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"gitcode_token": "from-file"}), encoding="utf-8")
    monkeypatch.setenv("GITCODE_TOKEN", "from-env")
    assert load_token(cfg) == "from-env"


def test_reads_from_config_file(monkeypatch, tmp_path):
    monkeypatch.delenv("GITCODE_TOKEN", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"gitcode_token": "from-file"}), encoding="utf-8")
    assert load_token(cfg) == "from-file"


def test_strips_whitespace(monkeypatch, tmp_path):
    monkeypatch.delenv("GITCODE_TOKEN", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"gitcode_token": "  spaced  "}), encoding="utf-8")
    assert load_token(cfg) == "spaced"


def test_missing_token_returns_none(monkeypatch, tmp_path):
    monkeypatch.delenv("GITCODE_TOKEN", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"other": "x"}), encoding="utf-8")
    assert load_token(cfg) is None


def test_missing_file_returns_none(monkeypatch, tmp_path):
    monkeypatch.delenv("GITCODE_TOKEN", raising=False)
    assert load_token(tmp_path / "nope.json") is None


def test_env_empty_falls_back_to_file(monkeypatch, tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"gitcode_token": "from-file"}), encoding="utf-8")
    monkeypatch.setenv("GITCODE_TOKEN", "   ")  # 空白视作未设置
    assert load_token(cfg) == "from-file"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest packages/gitcode/tests/test_config.py -v`
Expected: FAIL（`load_token` 未实现）

- [ ] **Step 3: 实现 config.py**

```python
"""配置读取：token 优先级 环境变量 GITCODE_TOKEN > ~/.melodyi-skills/gitcode/config.json

与其他 melodyi skill 共用 ~/.melodyi-skills/ 根目录。token 是账号级凭据，
未来 submit/review/merge 等 skill 共用同一份配置，故目录名为 gitcode。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".melodyi-skills" / "gitcode"
CONFIG_PATH = CONFIG_DIR / "config.json"


def load_token(config_path: Optional[Path] = None) -> Optional[str]:
    """读取 GitCode token

    优先级：环境变量 GITCODE_TOKEN > 配置文件（config_path 或默认 CONFIG_PATH）
    中的 gitcode_token 字段。空字符串视作未设置。

    Returns:
        token 字符串，未配置时返回 None
    """
    env_token = os.environ.get("GITCODE_TOKEN")
    if env_token and env_token.strip():
        logger.info("token 来源: 环境变量 GITCODE_TOKEN")
        return env_token.strip()

    path = Path(config_path) if config_path else CONFIG_PATH
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("配置文件 %s 解析失败: %s", path, e)
            return None
        token = data.get("gitcode_token") if isinstance(data, dict) else None
        if token and str(token).strip():
            logger.info("token 来源: 配置文件 %s", path)
            return str(token).strip()

    logger.info("token 未配置")
    return None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest packages/gitcode/tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/gitcode/gitcode/config.py packages/gitcode/tests/test_config.py
git commit -m "feat(gitcode): 实现 token 读取 load_token"
```

---

## Task 4: API 客户端核心 + get_user

**Files:**
- Create: `packages/gitcode/tests/test_api.py`
- Modify: `packages/gitcode/gitcode/api.py`

- [ ] **Step 1: 写失败测试（核心请求 + get_user）**

`packages/gitcode/tests/test_api.py`：
```python
"""GitCodeClient 单元测试：用 httpx.MockTransport 注入假响应，验证请求构造与响应解析"""

import httpx
import pytest

from gitcode.api import API_BASE, APIError, GitCodeClient


def _client(handler):
    return GitCodeClient("tok-123", transport=httpx.MockTransport(handler))


def test_get_user_request_and_parse():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"login": "alice", "id": 7})

    client = _client(handler)
    data = client.get_user()

    assert data == {"login": "alice", "id": 7}
    assert captured["url"] == f"{API_BASE}/user"
    assert captured["method"] == "GET"
    assert captured["auth"] == "Bearer tok-123"


def test_api_error_on_401():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")
    client = _client(handler)
    with pytest.raises(APIError) as exc:
        client.get_user()
    assert exc.value.status_code == 401


def test_api_error_on_404():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")
    client = _client(handler)
    with pytest.raises(APIError) as exc:
        client.get_user()
    assert exc.value.status_code == 404
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest packages/gitcode/tests/test_api.py -v`
Expected: FAIL（`GitCodeClient` 等未实现）

- [ ] **Step 3: 实现 api.py（核心 + get_user）**

```python
"""GitCode v5 API 客户端

用 httpx 封装 GitCode API。token 经 Authorization: Bearer 请求头发送，
不进 URL/查询串/日志。请求体用 json= 自动 UTF-8 编码，中文无需临时文件。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://api.gitcode.com/api/v5"


class APIError(Exception):
    """GitCode API 返回 4xx/5xx 或网络错误"""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"GitCode API {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class GitCodeClient:
    """GitCode v5 API 客户端

    Args:
        token: GitCode 个人访问令牌
        transport: 可选 httpx transport，测试时注入 MockTransport
    """

    def __init__(self, token: str, transport: Optional[httpx.BaseTransport] = None):
        self._token = token
        # 不设 base_url：httpx 的 base_url+绝对路径(/user)会按 RFC3986 替换掉 /api/v5，
        # 故在 _request 里手动拼完整 URL，避免路径丢失。
        self._client = httpx.Client(transport=transport, timeout=30.0)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json_body: Optional[Any] = None,
    ) -> Any:
        """统一请求入口：注入认证头、记录日志、处理错误状态码

        path 以 "/" 开头，拼到 API_BASE 之后形成完整 URL。

        Returns:
            响应 JSON（空响应体返回 {}）
        """
        headers = {"Authorization": f"Bearer {self._token}"}
        url = f"{API_BASE}{path}"
        logger.info("%s %s", method, url)
        try:
            resp = self._client.request(
                method, url, params=params, json=json_body, headers=headers
            )
        except httpx.HTTPError as e:
            raise APIError(0, f"网络错误: {e}") from e

        if resp.status_code >= 400:
            raise APIError(resp.status_code, resp.text)

        if not resp.content:
            return {}
        return resp.json()

    def get_user(self) -> dict:
        """获取当前 token 对应用户：GET /user"""
        return self._request("GET", "/user")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest packages/gitcode/tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/gitcode/gitcode/api.py packages/gitcode/tests/test_api.py
git commit -m "feat(gitcode): 实现 API 客户端核心与 get_user"
```

---

## Task 5: get_pr 与 get_files

**Files:**
- Modify: `packages/gitcode/tests/test_api.py`
- Modify: `packages/gitcode/gitcode/api.py`

- [ ] **Step 1: 追加失败测试**

在 `packages/gitcode/tests/test_api.py` 末尾追加：
```python
def test_get_pr_request_and_parse():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"number": 123, "title": "feat: x"})

    client = _client(handler)
    data = client.get_pr("owner", "repo", "123")

    assert data == {"number": 123, "title": "feat: x"}
    assert captured["url"] == f"{API_BASE}/repos/owner/repo/pulls/123"


def test_get_files_request_and_parse():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=[{"filename": "a.py"}, {"filename": "b.py"}])

    client = _client(handler)
    data = client.get_files("owner", "repo", "123")

    assert [f["filename"] for f in data] == ["a.py", "b.py"]
    assert captured["url"] == f"{API_BASE}/repos/owner/repo/pulls/123/files"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest packages/gitcode/tests/test_api.py -v`
Expected: FAIL（`get_pr`/`get_files` 不存在）

- [ ] **Step 3: 实现两个方法**

在 `packages/gitcode/gitcode/api.py` 的 `GitCodeClient` 类中，`get_user` 方法之后追加：
```python
    def get_pr(self, owner: str, repo: str, number: str) -> dict:
        """获取 PR 详情：GET /repos/{owner}/{repo}/pulls/{number}"""
        return self._request(
            "GET", f"/repos/{owner}/{repo}/pulls/{number}"
        )

    def get_files(self, owner: str, repo: str, number: str) -> list:
        """获取 PR 变更文件列表：GET /repos/{owner}/{repo}/pulls/{number}/files"""
        return self._request(
            "GET", f"/repos/{owner}/{repo}/pulls/{number}/files"
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest packages/gitcode/tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/gitcode/gitcode/api.py packages/gitcode/tests/test_api.py
git commit -m "feat(gitcode): 实现 get_pr 与 get_files"
```

---

## Task 6: get_comments（含 --mine 过滤逻辑）

说明：`--mine` 过滤逻辑放在 cli 层（需要同时取 user 与 comments），api 层只提供 `get_comments`。本任务实现 api 层 `get_comments`，cli 层过滤在 Task 9 实现。先在 api 测试里验证请求构造与原始列表透传。

**Files:**
- Modify: `packages/gitcode/tests/test_api.py`
- Modify: `packages/gitcode/gitcode/api.py`

- [ ] **Step 1: 追加失败测试**

在 `packages/gitcode/tests/test_api.py` 末尾追加：
```python
def test_get_comments_request_and_parse():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=[
            {"id": 1, "body": "x", "user": {"login": "alice"}},
            {"id": 2, "body": "y", "user": {"login": "bob"}},
        ])

    client = _client(handler)
    data = client.get_comments("owner", "repo", "123")

    assert len(data) == 2
    assert data[0]["user"]["login"] == "alice"
    assert captured["url"] == f"{API_BASE}/repos/owner/repo/pulls/123/comments"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest packages/gitcode/tests/test_api.py -v`
Expected: FAIL（`get_comments` 不存在）

- [ ] **Step 3: 实现 get_comments**

在 `packages/gitcode/gitcode/api.py` 的 `GitCodeClient` 类中追加：
```python
    def get_comments(self, owner: str, repo: str, number: str) -> list:
        """获取 PR 评论列表：GET /repos/{owner}/{repo}/pulls/{number}/comments

        返回原始评论对象数组，含 id/body/path/position/user 等字段，
        供调用方（cli --mine 或 agent）进一步筛选。
        """
        return self._request(
            "GET", f"/repos/{owner}/{repo}/pulls/{number}/comments"
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest packages/gitcode/tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/gitcode/gitcode/api.py packages/gitcode/tests/test_api.py
git commit -m "feat(gitcode): 实现 get_comments"
```

---

## Task 7: post_comment

**Files:**
- Modify: `packages/gitcode/tests/test_api.py`
- Modify: `packages/gitcode/gitcode/api.py`

- [ ] **Step 1: 追加失败测试**

在 `packages/gitcode/tests/test_api.py` 末尾追加：
```python
def test_post_comment_request_body():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = request.read()
        return httpx.Response(201, json={"id": 99, "body": "**[严重]** 问题"})

    client = _client(handler)
    data = client.post_comment(
        "owner", "repo", "123",
        body="**[严重]** 问题", path="src/a.py", position=10,
    )

    assert data == {"id": 99, "body": "**[严重]** 问题"}
    assert captured["method"] == "POST"
    assert captured["url"] == f"{API_BASE}/repos/owner/repo/pulls/123/comments"
    # 中文经 json= 自动 UTF-8 编码，能正确还原
    import json as _json
    assert _json.loads(captured["body"]) == {
        "body": "**[严重]** 问题", "path": "src/a.py", "position": 10,
    }


def test_post_comment_with_commit_id():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read()
        return httpx.Response(201, json={})

    client = _client(handler)
    client.post_comment(
        "owner", "repo", "123",
        body="b", path="p", position=1, commit_id="abc",
    )
    import json as _json
    assert _json.loads(captured["body"])["commit_id"] == "abc"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest packages/gitcode/tests/test_api.py -v`
Expected: FAIL（`post_comment` 不存在）

- [ ] **Step 3: 实现 post_comment**

在 `packages/gitcode/gitcode/api.py` 的 `GitCodeClient` 类中追加：
```python
    def post_comment(
        self,
        owner: str,
        repo: str,
        number: str,
        *,
        body: str,
        path: str,
        position: int,
        commit_id: Optional[str] = None,
    ) -> dict:
        """提交行内评论：POST /repos/{owner}/{repo}/pulls/{number}/comments

        body 中文由 httpx json= 自动 UTF-8 编码，无需临时文件。
        position 为 PR 分支版本文件中的绝对行号（1-based）。
        """
        payload: dict = {"body": body, "path": path, "position": position}
        if commit_id:
            payload["commit_id"] = commit_id
        return self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{number}/comments",
            json_body=payload,
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest packages/gitcode/tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/gitcode/gitcode/api.py packages/gitcode/tests/test_api.py
git commit -m "feat(gitcode): 实现 post_comment"
```

---

## Task 8: resolve_comment

**Files:**
- Modify: `packages/gitcode/tests/test_api.py`
- Modify: `packages/gitcode/gitcode/api.py`

- [ ] **Step 1: 追加失败测试**

在 `packages/gitcode/tests/test_api.py` 末尾追加：
```python
def test_resolve_comment_request():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = request.read()
        return httpx.Response(200, json={"resolved": True})

    client = _client(handler)
    data = client.resolve_comment("owner", "repo", "123", "disc-1")

    assert data == {"resolved": True}
    assert captured["method"] == "PUT"
    assert captured["url"] == f"{API_BASE}/repos/owner/repo/pulls/123/comments/disc-1"
    import json as _json
    assert _json.loads(captured["body"]) == {"resolved": True}


def test_resolve_comment_false():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read()
        return httpx.Response(200, json={})

    client = _client(handler)
    client.resolve_comment("owner", "repo", "123", "disc-1", resolved=False)
    import json as _json
    assert _json.loads(captured["body"]) == {"resolved": False}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest packages/gitcode/tests/test_api.py -v`
Expected: FAIL（`resolve_comment` 不存在）

- [ ] **Step 3: 实现 resolve_comment**

在 `packages/gitcode/gitcode/api.py` 的 `GitCodeClient` 类中追加：
```python
    def resolve_comment(
        self,
        owner: str,
        repo: str,
        number: str,
        discussion_id: str,
        *,
        resolved: bool = True,
    ) -> dict:
        """更新评论解决状态：PUT /repos/{owner}/{repo}/pulls/{number}/comments/{discussion_id}

        discussion_id 取自 get_comments 返回的评论 id 字段。
        """
        return self._request(
            "PUT",
            f"/repos/{owner}/{repo}/pulls/{number}/comments/{discussion_id}",
            json_body={"resolved": resolved},
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest packages/gitcode/tests/test_api.py -v`
Expected: PASS（全部 api 测试通过）

- [ ] **Step 5: Commit**

```bash
git add packages/gitcode/gitcode/api.py packages/gitcode/tests/test_api.py
git commit -m "feat(gitcode): 实现 resolve_comment"
```

---

## Task 9: CLI 子命令接线（含 --mine 过滤、退出码、body-file）

**Files:**
- Create: `packages/gitcode/tests/test_cli.py`
- Modify: `packages/gitcode/gitcode/cli.py`

说明：用 click `CliRunner` 测试。token 来源经 `--config` 指向临时配置文件；缺失 token 退出码 2；API 错误退出码 1。`--mine` 过滤在 cli 层：先取 user.login，再过滤 comments。

- [ ] **Step 1: 写失败测试**

`packages/gitcode/tests/test_cli.py`：
```python
"""CLI 子命令测试：CliRunner + monkeypatch GitCodeClient"""

import json

import httpx
from click.testing import CliRunner

from gitcode.cli import cli


def _write_cfg(tmp_path, token="tok-123"):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"gitcode_token": token}), encoding="utf-8")
    return cfg


def _patch_client(monkeypatch, handler):
    """把 GitCodeClient 替换为注入 MockTransport 的实例"""
    import gitcode.cli as cli_mod

    real_init = cli_mod.GitCodeClient.__init__

    def fake_init(self, token, transport=None):
        real_init(self, token, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(cli_mod.GitCodeClient, "__init__", fake_init)


def test_user_command_outputs_json(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(200, json={"login": "alice"}))
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(cli, ["--config", str(cfg), "user"])

    assert result.exit_code == 0
    assert json.loads(result.output) == {"login": "alice"}


def test_missing_token_exits_2(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(200, json={}))
    cfg = tmp_path / "config.json"  # 不写入 token
    cfg.write_text("{}", encoding="utf-8")

    result = CliRunner().invoke(cli, ["--config", str(cfg), "user"])

    assert result.exit_code == 2
    assert "token" in result.output.lower()


def test_api_error_exits_1(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(401, text="no auth"))
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(cli, ["--config", str(cfg), "user"])

    assert result.exit_code == 1
    assert "401" in result.output


def test_pr_command_uses_url(tmp_path, monkeypatch):
    captured = {}

    def handler(req):
        captured["url"] = str(req.url)
        return httpx.Response(200, json={"title": "t"})

    _patch_client(monkeypatch, handler)
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(
        cli, ["--config", str(cfg), "pr",
              "https://gitcode.com/owner/repo/-/merge_requests/123"]
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {"title": "t"}
    assert captured["url"].endswith("/repos/owner/repo/pulls/123")


def test_invalid_url_exits_1(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(200, json={}))
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(
        cli, ["--config", str(cfg), "pr", "https://example.com/x"]
    )
    assert result.exit_code == 1


def test_comments_mine_filters_by_user(tmp_path, monkeypatch):
    calls = []

    def handler(req):
        calls.append(str(req.url))
        if req.url.path.endswith("/user"):
            return httpx.Response(200, json={"login": "alice"})
        return httpx.Response(200, json=[
            {"id": 1, "user": {"login": "alice"}},
            {"id": 2, "user": {"login": "bob"}},
        ])

    _patch_client(monkeypatch, handler)
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(
        cli, ["--config", str(cfg), "comments", "--mine",
              "https://gitcode.com/owner/repo/-/merge_requests/123"]
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert [c["id"] for c in data] == [1]


def test_comment_body_file(tmp_path, monkeypatch):
    captured = {}

    def handler(req):
        captured["body"] = req.read()
        return httpx.Response(201, json={"id": 99})

    _patch_client(monkeypatch, handler)
    cfg = _write_cfg(tmp_path)
    body_file = tmp_path / "body.md"
    body_file.write_text("**[严重]** 中文问题", encoding="utf-8")

    result = CliRunner().invoke(cli, [
        "--config", str(cfg), "comment",
        "https://gitcode.com/owner/repo/-/merge_requests/123",
        "--path", "src/a.py", "--position", "10",
        "--body-file", str(body_file),
    ])

    assert result.exit_code == 0
    assert json.loads(result.output) == {"id": 99}
    assert json.loads(captured["body"])["body"] == "**[严重]** 中文问题"


def test_comment_requires_body(tmp_path, monkeypatch):
    _patch_client(monkeypatch, lambda req: httpx.Response(201, json={}))
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(cli, [
        "--config", str(cfg), "comment",
        "https://gitcode.com/owner/repo/-/merge_requests/123",
        "--path", "src/a.py", "--position", "10",
    ])
    assert result.exit_code == 2


def test_resolve_command(tmp_path, monkeypatch):
    captured = {}

    def handler(req):
        captured["method"] = req.method
        captured["url"] = str(req.url)
        return httpx.Response(200, json={"resolved": True})

    _patch_client(monkeypatch, handler)
    cfg = _write_cfg(tmp_path)

    result = CliRunner().invoke(cli, [
        "--config", str(cfg), "resolve",
        "https://gitcode.com/owner/repo/-/merge_requests/123",
        "--discussion-id", "disc-1",
    ])

    assert result.exit_code == 0
    assert captured["method"] == "PUT"
    assert captured["url"].endswith("/comments/disc-1")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest packages/gitcode/tests/test_cli.py -v`
Expected: FAIL（子命令未实现）

- [ ] **Step 3: 实现 cli.py 全部子命令**

把 `packages/gitcode/gitcode/cli.py` 替换为：
```python
"""CLI 命令行入口

子命令：user / pr / files / comments / comment / resolve

日志风格参考 melodyi-filebot：默认静默（仅 ERROR），--verbose/-v 输出 INFO；
业务错误用 click.echo(err=True) + sys.exit 友好报错，非 traceback。
退出码：0 成功 / 1 业务或网络错误 / 2 token 缺失或参数错误。
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

from gitcode.api import APIError, GitCodeClient
from gitcode.config import load_token
from gitcode.url import UrlParseError, parse_pr_url

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    """配置日志：默认仅 ERROR（静默），--verbose 输出 INFO 级日志"""
    level = logging.INFO if verbose else logging.ERROR
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(level)


def _print_json(data) -> None:
    """把结构化结果以 UTF-8 JSON 输出到 stdout（ensure_ascii=False 保留中文）"""
    click.echo(json.dumps(data, ensure_ascii=False, indent=2))


def _fail(message: str, code: int) -> None:
    """友好报错并以指定退出码终止"""
    click.echo(f"错误: {message}", err=True)
    sys.exit(code)


@click.group()
@click.version_option(package_name="gitcode", prog_name="gitcode")
@click.option("--config", "config_path", type=click.Path(exists=False), default=None,
              help="配置文件路径（默认 ~/.melodyi-skills/gitcode/config.json）")
@click.option("--verbose", "-v", is_flag=True, help="输出详细日志（默认仅输出错误）")
@click.pass_context
def cli(ctx, config_path, verbose):
    """gitcode: GitCode PR 代码检视 CLI"""
    _configure_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = Path(config_path) if config_path else None


def _build_client(ctx) -> GitCodeClient:
    """读取 token 并构造客户端；token 缺失则退出码 2"""
    token = load_token(ctx.obj.get("config_path"))
    if not token:
        _fail("未配置 token：请设置环境变量 GITCODE_TOKEN 或在 "
              "~/.melodyi-skills/gitcode/config.json 填写 gitcode_token", 2)
    return GitCodeClient(token)


def _ref(url: str):
    """解析 PR URL；失败退出码 1"""
    try:
        return parse_pr_url(url)
    except UrlParseError as e:
        _fail(str(e), 1)


@cli.command()
@click.pass_context
def user(ctx):
    """获取当前 token 对应用户"""
    client = _build_client(ctx)
    try:
        _print_json(client.get_user())
    except APIError as e:
        _fail(str(e), 1)


@cli.command()
@click.argument("url")
@click.pass_context
def pr(ctx, url):
    """获取 PR 详情（URL 形式传入）"""
    client = _build_client(ctx)
    r = _ref(url)
    try:
        _print_json(client.get_pr(r.owner, r.repo, r.number))
    except APIError as e:
        _fail(str(e), 1)


@cli.command()
@click.argument("url")
@click.pass_context
def files(ctx, url):
    """获取 PR 变更文件列表"""
    client = _build_client(ctx)
    r = _ref(url)
    try:
        _print_json(client.get_files(r.owner, r.repo, r.number))
    except APIError as e:
        _fail(str(e), 1)


@cli.command()
@click.argument("url")
@click.option("--mine", is_flag=True, help="仅返回当前用户提交的评论")
@click.pass_context
def comments(ctx, url, mine):
    """获取 PR 评论列表"""
    client = _build_client(ctx)
    r = _ref(url)
    try:
        comments_data = client.get_comments(r.owner, r.repo, r.number)
        if mine:
            login = client.get_user().get("login")
            comments_data = [
                c for c in comments_data
                if (c.get("user") or {}).get("login") == login
            ]
        _print_json(comments_data)
    except APIError as e:
        _fail(str(e), 1)


@cli.command()
@click.argument("url")
@click.option("--path", "file_path", required=True, help="文件相对路径")
@click.option("--position", type=int, required=True, help="PR 分支版本绝对行号(1-based)")
@click.option("--commit-id", default=None, help="提交 SHA（默认最新）")
@click.option("--body", default=None, help="评论内容（与 --body-file 二选一）")
@click.option("--body-file", "body_file", type=click.Path(exists=True), default=None,
              help="评论内容文件路径（与 --body 二选一，长内容/中文推荐）")
@click.pass_context
def comment(ctx, url, file_path, position, commit_id, body, body_file):
    """提交行内评论"""
    if not body and not body_file:
        _fail("必须提供 --body 或 --body-file 之一", 2)
    if body and body_file:
        _fail("--body 与 --body-file 互斥，请只提供一个", 2)
    content = body if body else Path(body_file).read_text(encoding="utf-8")

    client = _build_client(ctx)
    r = _ref(url)
    try:
        result = client.post_comment(
            r.owner, r.repo, r.number,
            body=content, path=file_path, position=position, commit_id=commit_id,
        )
        _print_json(result)
    except APIError as e:
        _fail(str(e), 1)


@cli.command()
@click.argument("url")
@click.option("--discussion-id", required=True, help="评论讨论 ID（取自 comments 输出的 id）")
@click.option("--resolved/--unresolved", default=True, help="标记为已解决/未解决（默认已解决）")
@click.pass_context
def resolve(ctx, url, discussion_id, resolved):
    """更新评论解决状态"""
    client = _build_client(ctx)
    r = _ref(url)
    try:
        result = client.resolve_comment(
            r.owner, r.repo, r.number, discussion_id, resolved=resolved
        )
        _print_json(result)
    except APIError as e:
        _fail(str(e), 1)


if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: 运行 CLI 测试确认通过**

Run: `pytest packages/gitcode/tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: 运行全部测试**

Run: `pytest packages/gitcode/tests -v`
Expected: 全部 PASS

- [ ] **Step 6: 手动验证入口**

Run: `gitcode --help` 与 `gitcode comment --help`
Expected: 列出全部子命令与各选项帮助，退出码 0。

- [ ] **Step 7: Commit**

```bash
git add packages/gitcode/gitcode/cli.py packages/gitcode/tests/test_cli.py
git commit -m "feat(gitcode): 实现全部 CLI 子命令与退出码"
```

---

## Task 10: skill SKILL.md 与包 CLAUDE.md

**Files:**
- Create: `skills/gitcode-pr-review/SKILL.md`
- Create: `packages/gitcode/CLAUDE.md`

- [ ] **Step 1: 写 skills/gitcode-pr-review/SKILL.md**

```markdown
---
name: gitcode-pr-review
description: GitCode PR 代码检视工具。支持检视 PR 代码并提交评论，以及验收已提交的检视意见。当用户提供 GitCode PR 链接并请求代码检视或验收检视意见时调用。
---

# GitCode PR 代码检视工具

基于 `gitcode` CLI（需先 `pip install -e packages/gitcode`）封装 GitCode API。
所有 API 调用、token 读取由 CLI 内部处理——**不要**自行 curl 接口或读取配置中的秘钥。

## 前置

- 已安装 `gitcode` CLI（`pip install -e packages/gitcode`）
- token 已配置：环境变量 `GITCODE_TOKEN`，或 `~/.melodyi-skills/gitcode/config.json` 的 `gitcode_token`
- 验证配置：`gitcode user` 能返回当前用户即正常

## CLI 速查

| 命令 | 作用 | stdout |
|---|---|---|
| `gitcode user` | 当前 token 用户 | JSON |
| `gitcode pr <url>` | PR 详情（标题/描述/分支/状态） | JSON |
| `gitcode files <url>` | 变更文件列表 | JSON |
| `gitcode comments <url> [--mine]` | 评论列表；`--mine` 仅本人 | JSON |
| `gitcode comment <url> --path P --position N (--body T \| --body-file F) [--commit-id SHA]` | 提交行内评论 | JSON |
| `gitcode resolve <url> --discussion-id D [--unresolved]` | 更新评论解决状态 | JSON |

`<url>` 直接传用户给的 PR 链接，CLI 内部解析 owner/repo/number。

退出码：`0` 成功 / `1` 业务或网络错误 / `2` token 未配置或参数错误。

## 模式一：代码检视

示例请求：
- "请检视这个 PR: https://gitcode.com/owner/repo/-/merge_requests/123"

执行步骤：

1. **获取 PR 详情与变更文件**
   ```bash
   gitcode pr "<url>"            # 取标题、描述、源/目标分支
   gitcode files "<url>"         # 取变更文件列表
   ```

2. **进入/克隆代码目录**（git 操作，由 agent 执行）
   - 目录不存在则克隆：`git clone https://gitcode.com/{owner}/{repo}.git`
   - 已存在则拉取：`git fetch origin`
   - 切换到 PR 分支：`git checkout {source_branch} && git pull origin {source_branch}`
     或 `git fetch origin pull/{number}/head:pr-{number} && git checkout pr-{number}`
   - 非交互式 git 注意事项见末尾

3. **分析代码变更**
   - 用 Read 工具逐个读取变更文件，行号即 `comment --position` 所需的 PR 分支绝对行号（1-based）
   - 检视意见分两级：
     - **严重**：功能/性能/bug/安全等必须修复的问题 → 直接提交行内评论
     - **建议**：风格/命名/可维护性等改进 → 汇总后由用户选择提交

4. **提交检视意见**
   - 先查已有评论避免重复：`gitcode comments "<url>"`
   - **严重**级别直接提交（长内容/中文用 `--body-file`）：
     ```bash
     # 先把评论写入临时文件，再用 --body-file 提交
     gitcode comment "<url>" --path src/a.py --position 10 --body-file /tmp/c1.md
     ```
     评论内容以 `**[严重]** 问题描述及修改建议` 开头。
   - **建议**级别不直接提交，按严重度排序输出汇总：
     ```
     === 检视意见汇总 ===

     --- 严重级别（已自动提交）---
     1. [文件路径:行号] **[严重]** 问题描述

     --- 建议级别（待确认）---
     2. [文件路径:行号] **[建议]** 改进建议

     请输入需要提交的建议级别意见编号（如: 2），或输入 none 跳过：
     ```
     用户选择后，仅对选中项用 `gitcode comment ... --body-file` 提交。

## 模式二：验收检视意见

示例请求：
- "验收这个 PR 的检视意见: <url>"

执行步骤：

1. **获取本人提交的评论**
   ```bash
   gitcode comments "<url>" --mine
   ```

2. **逐条验证是否已修复**
   - 对每条评论，用 Read 检查对应 `path`:`position` 的当前代码
   - 判断问题是否已解决

3. **更新解决状态**
   - 已修复：`gitcode resolve "<url>" --discussion-id <id>`（默认 resolved）
   - 未修复：`gitcode resolve "<url>" --discussion-id <id> --unresolved`
   - `<id>` 取自 `comments` 输出中的 `id` 字段

## 评论格式

评论必须以级别标记开头：

```markdown
**[严重]** 问题描述及修改建议

**[建议]** 改进建议内容
```

## 检视要点

- 正确性：逻辑、边界、错误处理 → 严重
- 安全：输入验证、敏感信息、权限 → 严重
- 性能：算法效率、资源使用 → 严重
- 风格/命名/可维护性/可读性 → 建议

## 错误处理

| 退出码/状态 | 处理 |
|---|---|
| 退出码 2（token 缺失） | 提示用户配置 `GITCODE_TOKEN` 或 config.json |
| 401 | token 无效或过期 |
| 403 | token 权限不足 |
| 404 | 检查 owner/repo/number |
| 429 | 等待后重试 |

## 非交互式 git 注意事项

- 禁止 `git rebase -i`、无 `-m` 的 `git commit`、`git add -p` 等会弹编辑器的命令
- `git log`/`git diff` 必须禁用分页器：`git --no-pager log` 或设 `GIT_PAGER=cat`
- `git commit` 必须带 `-m`
- 私有仓克隆需带认证 URL（`https://token@gitcode.com/...`）或预配 credential helper，不要交互输入凭据
```

- [ ] **Step 2: 写 packages/gitcode/CLAUDE.md**

```markdown
# CLAUDE.md

本文件为 Claude Code 在 `packages/gitcode` 下工作时提供指导。

## 项目概述

`gitcode` 是 GitCode PR 代码检视的 CLI 包，封装 GitCode v5 API 调用与 token 管理。
配套轻量 skill `skills/gitcode-pr-review` 通过调用已安装的 `gitcode` CLI 完成检视/验收。
未来可拆分 `gitcode-submit`、`gitcode-merge` 等 skill，共享本包与同一份账号级 token 配置。

## 常用命令

```bash
# 安装（开发模式）
pip install -e packages/gitcode

# 运行测试
pytest packages/gitcode/tests -v

# 验证配置
gitcode user
```

## 配置

token 优先级：环境变量 `GITCODE_TOKEN` > `~/.melodyi-skills/gitcode/config.json` 的 `gitcode_token`。
CLI 提供 `--config PATH` 指定配置文件路径（不提供 `--token`，避免秘钥落入命令行）。

## 架构

- `url.py`：`parse_pr_url()` 从 PR URL 解析 owner/repo/number
- `config.py`：`load_token()` 读取 token（env > config）
- `api.py`：`GitCodeClient(httpx)` 封装端点，token 经 `Authorization: Bearer` 头发送；
  `APIError` 承载 4xx/5xx 与网络错误
- `cli.py`：click 命令组，6 个子命令；stdout 输出 JSON，stderr 日志；
  退出码 0/1/2；`--mine` 在 cli 层过滤（取 user.login 后筛 comments）

## 设计决策

- httpx（非 stdlib urllib）：JSON 自动 UTF-8 编码、MockTransport 便于测试、符合项目约定；
  包形态下安装成本不再是缺点
- 评论 body 支持 `--body` 与 `--body-file`，长内容/中文推荐 `--body-file`
- API 返回原始 JSON 透传，过滤/分析交给调用方（cli 或 agent）
```

- [ ] **Step 3: 验证 skill 可被发现与调用**

Run: `gitcode --help` 确认子命令齐全；`ls skills/gitcode-pr-review`
Expected: `SKILL.md` 存在；`gitcode --help` 列出 user/pr/files/comments/comment/resolve。

- [ ] **Step 4: Commit**

```bash
git add skills/gitcode-pr-review packages/gitcode/CLAUDE.md
git commit -m "feat(gitcode): 新增 gitcode-pr-review skill 与包开发指南"
```

---

## 完成标准

- `pytest packages/gitcode/tests -v` 全部通过
- `gitcode --help` 列出 6 个子命令
- `pip install -e packages/gitcode` 后 `gitcode user`（用真实 token）能返回用户信息（冒烟验证，可选）
- `skills/gitcode-pr-review/SKILL.md` 与 `packages/gitcode/CLAUDE.md` 就位
