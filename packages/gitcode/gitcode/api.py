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

    def get_comments(self, owner: str, repo: str, number: str) -> list:
        """获取 PR 评论列表：GET /repos/{owner}/{repo}/pulls/{number}/comments

        返回原始评论对象数组，含 id/body/path/position/user 等字段，
        供调用方（cli --mine 或 agent）进一步筛选。
        """
        return self._request(
            "GET", f"/repos/{owner}/{repo}/pulls/{number}/comments"
        )

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
