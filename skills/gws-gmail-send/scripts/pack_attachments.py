#!/usr/bin/env python3
"""gws-gmail-send 附件两轮压缩打包工具。

绕开 Gmail 附件类型/文件名扫描：第一轮把入参文件/文件夹打成无密码 zip，
第二轮用密码把该 zip 再包一层 zip。最终产物为外层密码 zip，密码回显给调用方，
便于在邮件正文中告知收件人解压方式。

zip 格式默认只加密内容、不加密文件名，因此单层密码 zip 仍会暴露内部文件名；
两轮设计让外层 zip 只暴露 ``inner.zip`` 这个名字，真实文件名藏在被加密的内层 zip 里，
Gmail 无法进一步枚举，从而绕开基于文件名的扫描。

用法::

    python pack_attachments.py FILE [FILE ...] [-p PASSWORD] [-o OUTPUT] [--7z PATH]

stdout 输出两行，供调用方解析::

    ARCHIVE=<最终外层 zip 绝对路径>
    PASSWORD=<密码>
"""

from __future__ import annotations

import argparse
import secrets
import shutil
import string
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

DEFAULT_7Z = "7z"
# 仅字母+数字，避免特殊字符在邮件正文/复制粘贴时出问题
PASSWORD_ALPHABET = string.ascii_letters + string.digits
PASSWORD_LENGTH = 16
ARCHIVE_FORMAT = "zip"
INNER_ARCHIVE_NAME = "inner.zip"


class PackError(RuntimeError):
    """打包过程中的错误。"""


def generate_password(length: int = PASSWORD_LENGTH) -> str:
    """生成随机密码（字母+数字）。"""
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def resolve_7z(candidate: str) -> str:
    """定位 7z 可执行文件，找不到时报错。"""
    found = shutil.which(candidate)
    if not found:
        raise PackError(
            f"未找到 7z 可执行文件：{candidate}（请安装 7-Zip 或通过 --7z 指定路径）"
        )
    return found


def run_7z(seven_zip: str, args: list[str]) -> None:
    """调用 7z，失败则抛出 PackError。

    通过参数列表传参（不走 shell），避免密码进入 shell 解析或泄露到 shell 进程信息。
    """
    cmd = [seven_zip, *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise PackError(
            f"7z 执行失败（返回码 {result.returncode}）\n"
            f"命令：{' '.join(cmd)}\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )


def default_output_path() -> Path:
    """默认产物路径：当前工作目录下带时间戳的 zip。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path.cwd() / f"gmail_attachments_{ts}.zip"


def pack(
    paths: list[Path],
    *,
    password: str | None,
    output: Path | None,
    seven_zip: str = DEFAULT_7Z,
) -> tuple[Path, str]:
    """执行两轮打包，返回 (最终 zip 路径, 密码)。"""
    if not paths:
        raise PackError("至少提供一个文件或文件夹路径")
    for p in paths:
        if not p.exists():
            raise PackError(f"路径不存在：{p}")

    seven_zip = resolve_7z(seven_zip)

    pwd = password if password else generate_password()
    out_path = output.resolve() if output else default_output_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 用临时目录存放中间产物 inner.zip，完成后清理
    with tempfile.TemporaryDirectory() as tmp:
        inner = Path(tmp) / INNER_ARCHIVE_NAME
        # 第一轮：无密码 zip，把入参打包
        run_7z(seven_zip, ["a", f"-t{ARCHIVE_FORMAT}", str(inner), *[str(p) for p in paths]])
        # 第二轮：用密码把 inner.zip 打成外层 zip
        run_7z(seven_zip, ["a", f"-t{ARCHIVE_FORMAT}", f"-p{pwd}", str(out_path), str(inner)])

    return out_path, pwd


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="gws-gmail-send 附件两轮压缩打包工具（绕开 Gmail 文件名扫描）",
    )
    parser.add_argument("paths", nargs="+", help="一个或多个文件/文件夹路径")
    parser.add_argument(
        "-p", "--password", default=None,
        help="外层 zip 密码；不指定则随机生成并回显",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="最终外层 zip 路径；不指定则写入当前目录 gmail_attachments_<时间戳>.zip",
    )
    parser.add_argument(
        "--7z", dest="seven_zip", default=DEFAULT_7Z,
        help=f"7z 可执行文件路径或名称（默认 {DEFAULT_7Z}）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        out_path, pwd = pack(
            [Path(p) for p in args.paths],
            password=args.password,
            output=Path(args.output) if args.output else None,
            seven_zip=args.seven_zip,
        )
    except PackError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    # 两行机器可解析输出
    print(f"ARCHIVE={out_path}")
    print(f"PASSWORD={pwd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
