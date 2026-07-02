#!/usr/bin/env python3
"""gen-fixtures.py — 从真实源目录生成极小测试用例

扫描源目录的目录结构与文件，在输出目录复刻同样结构：
- 视频文件：用 ffprobe 取真实时长，再用 ffmpeg 生成 1 帧黑屏极小视频
  （容器 duration 元数据 = 原时长，体积 ~1KB 与时长无关），扩展名保留原样。
- 非视频文件（字幕 .ass/.srt、图片、nfo 等）：原样复制，保留相对路径与文件名。
- 输出 manifest.json：记录每个视频的相对路径、真实时长（秒）、生成体积，供测试断言。

用途：为 melodyi-filebot 的 analyze / draft-plan / execute-plan 等命令构建
带真实目录结构与时长元数据、但几乎不占空间的测试影视库。真实测试时
把生成的 fixture 目录 copytree 到一次性 tmp_path 使用即可。

用法:
  python gen-fixtures.py <源目录> --name <用例名> [--out <fixtures根>] [--overwrite]

示例:
  python skills/melodyi-filebot/scripts/gen-fixtures.py \\
      "D:/download/机动战士高达seed+seed destiny  重制版 1080P" \\
      --name gundam-seed-hd

默认输出到 packages/melodyi-filebot/tests/fixtures/<name>/。

依赖：ffprobe / ffmpeg（已在 PATH），melodyi_filebot 包（pip install -e）。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# 复用包内常量与探针，保证与 analyze CLI 一致
from melodyi_filebot.planner import VIDEO_EXTS
from melodyi_filebot.structure import probe_duration_ffmpeg

# 默认 fixtures 根目录：仓库内 packages/melodyi-filebot/tests/fixtures
# 脚本位于 <repo>/skills/melodyi-filebot/scripts/gen-fixtures.py，parents[3] 即仓库根
_DEFAULT_OUT = (
    Path(__file__).resolve().parents[3]
    / "packages" / "melodyi-filebot" / "tests" / "fixtures"
)


def _gen_fake_video(out_path: Path, duration_seconds: int) -> int:
    """生成 1 帧黑屏极小视频，容器 duration = duration_seconds。

    用 lavfi color 源 + 超低帧率 r=1/d：只生成 1 帧数据（~1KB），
    但容器元数据 duration 报 d 秒。ffprobe 读 format=duration 即得期望时长。
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # duration 至少 1 秒，避免 r=1/0
    d = max(1, int(duration_seconds))
    cmd = [
        "ffmpeg", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"color=black:s=4x4:d={d}:r=1/{d}",
        "-c:v", "libx264",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out_path.stat().st_size


def _copy_file(src: Path, dst: Path) -> int:
    """原样复制非视频文件，保留相对路径。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst.stat().st_size


def generate_fixture(src_dir: Path, out_dir: Path) -> dict:
    """扫描 src_dir，在 out_dir 复刻结构（视频极小化，其余原样复制）。

    Returns:
        manifest dict：{videos: [{rel, duration_seconds, size_bytes}], companions: [...], skipped: [...]}
    """
    src_dir = src_dir.resolve()
    manifest = {"videos": [], "companions": [], "skipped": []}
    files = sorted(p for p in src_dir.rglob("*") if p.is_file())
    total = len(files)
    for i, src in enumerate(files, 1):
        rel = src.relative_to(src_dir).as_posix()
        dst = out_dir / rel
        ext = src.suffix.lower()
        if ext in VIDEO_EXTS:
            secs = probe_duration_ffmpeg(src)
            if secs is None:
                print(f"[{i}/{total}] 跳过（取不到时长）: {rel}", file=sys.stderr)
                manifest["skipped"].append({"rel": rel, "reason": "no_duration"})
                continue
            size = _gen_fake_video(dst, round(secs))
            manifest["videos"].append(
                {"rel": rel, "duration_seconds": secs, "size_bytes": size})
            print(f"[{i}/{total}] 视频 {rel}  ({secs:.1f}s → {size}B)")
        else:
            size = _copy_file(src, dst)
            manifest["companions"].append({"rel": rel, "size_bytes": size})
            print(f"[{i}/{total}] 复制 {rel}  ({size}B)")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="从真实源目录生成极小测试用例（视频极小化 + 伴生原样复制）")
    parser.add_argument("src_dir", type=Path, help="真实源目录路径")
    parser.add_argument("--name", required=True, help="用例名（fixture 子目录名）")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT,
                        help=f"fixtures 根目录（默认 {_DEFAULT_OUT}）")
    parser.add_argument("--overwrite", action="store_true",
                        help="覆盖已存在的用例目录（默认报错退出）")
    args = parser.parse_args()

    src_dir: Path = args.src_dir
    if not src_dir.is_dir():
        print(f"错误：源目录不存在: {src_dir}", file=sys.stderr)
        return 1
    out_dir: Path = (args.out / args.name).resolve()
    if out_dir.exists():
        if not args.overwrite:
            print(f"错误：用例目录已存在: {out_dir}\n"
                  f"加 --overwrite 覆盖，或换 --name", file=sys.stderr)
            return 1
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    print(f"源目录: {src_dir}")
    print(f"输出到: {out_dir}")
    manifest = generate_fixture(src_dir, out_dir)
    manifest["src_dir"] = str(src_dir)
    manifest["name"] = args.name

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    v = manifest["videos"]
    c = manifest["companions"]
    s = manifest["skipped"]
    total_dur = sum(x["duration_seconds"] for x in v)
    total_size = sum(x["size_bytes"] for x in v) + sum(x["size_bytes"] for x in c)
    print(f"\n完成：视频 {len(v)} 个（总时长 {total_dur:.0f}s），"
          f"伴生 {len(c)} 个，跳过 {len(s)} 个，"
          f"总体积 {total_size / 1024:.1f} KB")
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
