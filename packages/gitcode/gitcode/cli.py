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
