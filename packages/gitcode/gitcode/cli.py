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
