"""路径分析（analyze 命令实现）

agent 执行 skill 的第一步：把用户给的路径展开成层级树，
视频额外带时长（ffprobe 取秒数 → "HH:MM:SS"），目录累计子树视频数。
深度过深（≥阈值）或文件过多（>阈值）时，只返回概要并停止，避免对超大树逐个取时长。
"""

from __future__ import annotations

import logging
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Callable, Optional

from melodyi_filebot.models import PathAnalysis, TreeNode
from melodyi_filebot.planner import VIDEO_EXTS

logger = logging.getLogger(__name__)

# 默认告警阈值：目录深度（根=1）与文件总数
DEFAULT_DEPTH_THRESHOLD = 5
DEFAULT_FILE_THRESHOLD = 5000


def format_duration(seconds: Optional[float]) -> Optional[str]:
    """秒（float）→ "HH:MM:SS"

    Args:
        seconds: 时长秒数，None 时返回 None

    Returns:
        "HH:MM:SS" 字符串，或 None
    """
    if seconds is None:
        return None
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def probe_duration_ffmpeg(path: Path) -> Optional[float]:
    """用 ffprobe 取视频时长（秒）

    Args:
        path: 视频文件路径

    Returns:
        时长秒数（float），失败返回 None
    """
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True, text=True, timeout=60, check=True,
        )
        text = out.stdout.strip()
        return float(text) if text else None
    except Exception as exc:  # noqa: BLE001 - ffprobe 缺失/超时/非视频均视为取不到时长
        logger.warning("ffprobe 取时长失败: %s (%s)", path, exc)
        return None


def _is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTS


def _walk_stats(root: Path):
    """轻量第一遍：递归统计文件/视频/目录数、最大深度、按扩展名/层分布

    不调用 ffprobe，用于先判断是否命中告警阈值。
    """
    total_files = 0
    total_videos = 0
    total_dirs = 0
    max_depth = 1
    by_ext: dict = defaultdict(int)
    by_depth: dict = defaultdict(int)
    by_depth["1"] += 1  # 根目录自身

    stack = [(root, 1)]
    while stack:
        current, depth = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            logger.warning("读取目录失败: %s (%s)", current, exc)
            continue
        for entry in entries:
            if entry.is_dir():
                child_depth = depth + 1
                total_dirs += 1
                max_depth = max(max_depth, child_depth)
                by_depth[str(child_depth)] += 1
                stack.append((entry, child_depth))
            elif entry.is_file():
                total_files += 1
                by_ext[entry.suffix.lower() or "(无扩展名)"] += 1
                if _is_video(entry):
                    total_videos += 1
    return total_files, total_videos, total_dirs, max_depth, dict(by_ext), dict(by_depth)


def _build_tree(
    current: Path, depth: int, probe: Callable[[Path], Optional[float]]
) -> TreeNode:
    """构建带时长的目录树（仅在未命中告警时调用）"""
    entries = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name))
    children = []
    video_count = 0
    for entry in entries:
        if entry.is_dir():
            child = _build_tree(entry, depth + 1, probe)
            video_count += child.video_count
            children.append(child)
        elif entry.is_file():
            is_vid = _is_video(entry)
            secs = probe(entry) if is_vid else None
            if is_vid:
                video_count += 1
            children.append(TreeNode(
                name=entry.name, type="file", path=str(entry),
                is_video=is_vid, duration_seconds=secs,
            ))
    return TreeNode(
        name=current.name, type="dir", path=str(current),
        video_count=video_count, children=children,
    )


def analyze_path(
    path: str,
    depth_threshold: int = DEFAULT_DEPTH_THRESHOLD,
    file_threshold: int = DEFAULT_FILE_THRESHOLD,
    probe: Optional[Callable[[Path], Optional[float]]] = None,
) -> PathAnalysis:
    """分析路径：展开层级树，视频带时长，目录累计视频数

    Args:
        path: 文件夹或文件路径（根目录记为第 1 层）
        depth_threshold: 目录深度告警阈值（达到即告警，默认 5）
        file_threshold: 文件总数告警阈值（超过即告警，默认 5000）
        probe: 取时长的函数（path -> 秒数），默认用 ffprobe

    Returns:
        PathAnalysis：正常返回 tree；命中告警则 truncated=True 且 tree=None，仅返回概要

    Raises:
        FileNotFoundError: 路径不存在
    """
    if probe is None:
        probe = probe_duration_ffmpeg
    root_path = Path(path)
    if not root_path.exists():
        raise FileNotFoundError(f"路径不存在: {path}")

    # 单文件：直接构造一个文件节点
    if root_path.is_file():
        is_vid = _is_video(root_path)
        node = TreeNode(
            name=root_path.name, type="file", path=str(root_path),
            is_video=is_vid,
            duration_seconds=probe(root_path) if is_vid else None,
        )
        return PathAnalysis(
            root=str(root_path), truncated=False,
            total_files=1, total_videos=1 if is_vid else 0,
            total_dirs=0, max_depth=1, tree=node,
        )

    # 第一遍：轻量统计
    total_files, total_videos, total_dirs, max_depth, by_ext, by_depth = _walk_stats(root_path)

    warnings = []
    if max_depth >= depth_threshold:
        warnings.append(f"目录深度达到 {max_depth} 层（阈值 {depth_threshold}），结构过深")
    if total_files > file_threshold:
        warnings.append(f"文件总数 {total_files} 超过 {file_threshold}，数量过多")

    if warnings:
        logger.warning("analyze 命中告警，返回概要: root=%s warnings=%s", path, warnings)
        return PathAnalysis(
            root=str(root_path), truncated=True,
            total_files=total_files, total_videos=total_videos,
            total_dirs=total_dirs, max_depth=max_depth,
            warnings=warnings, by_ext=by_ext, by_depth=by_depth,
        )

    # 第二遍：构建带时长的完整树
    logger.info("analyze 构建详细树: root=%s, 文件=%d, 视频=%d", path, total_files, total_videos)
    tree = _build_tree(root_path, 1, probe)
    return PathAnalysis(
        root=str(root_path), truncated=False,
        total_files=total_files, total_videos=total_videos,
        total_dirs=total_dirs, max_depth=max_depth, tree=tree,
    )


def render_text(result: PathAnalysis) -> str:
    """把 PathAnalysis 渲染成树状文本（默认输出）

    - 首层显示绝对路径，深层只显示文件/目录名
    - 视频时长用 HH:MM:SS；目录标注子树累计视频数
    - 命中告警时只输出概要（不展开树）
    """
    lines: list = [f"路径: {result.root}"]
    lines.append(
        f"统计: 文件 {result.total_files} · 视频 {result.total_videos} · "
        f"目录 {result.total_dirs} · 最大深度 {result.max_depth}"
    )
    for w in result.warnings:
        lines.append(f"[告警] {w}")

    if result.truncated:
        if result.by_ext:
            ext_str = " · ".join(
                f"{k}={v}" for k, v in sorted(result.by_ext.items(), key=lambda x: -x[1])
            )
            lines.append(f"按扩展名: {ext_str}")
        if result.by_depth:
            depth_str = " · ".join(
                f"L{k}={v}" for k, v in sorted(result.by_depth.items(), key=lambda x: int(x[0]))
            )
            lines.append(f"按目录层: {depth_str}")
        lines.append("（结构过大/过深，未展开完整树。建议缩小范围或分批处理）")
        return "\n".join(lines)

    tree = result.tree
    if tree is None:
        return "\n".join(lines)

    lines.append("")
    if tree.type == "file":
        # 单文件：直接显示其绝对路径与时长
        if tree.is_video:
            dur = format_duration(tree.duration_seconds)
            tag = f"  ({dur})" if dur else "  (时长未知)"
        else:
            tag = ""
        lines.append(f"{tree.path}{tag}")
        return "\n".join(lines)

    # 目录树：根显示绝对路径，子节点用树状缩进
    root_tag = f"  [视频 {tree.video_count}]" if tree.video_count else ""
    lines.append(f"{tree.path}/{root_tag}")
    _render_subtree(tree, "", lines)
    return "\n".join(lines)


def _render_subtree(node: TreeNode, prefix: str, lines: list) -> None:
    """递归渲染目录的子节点（目录优先，再文件）"""
    children = node.children or []
    for i, child in enumerate(children):
        last = i == len(children) - 1
        connector = "└── " if last else "├── "
        if child.type == "dir":
            tag = f"  [视频 {child.video_count}]" if child.video_count else ""
            lines.append(f"{prefix}{connector}{child.name}/{tag}")
            ext = "    " if last else "│   "
            _render_subtree(child, prefix + ext, lines)
        else:
            if child.is_video:
                dur = format_duration(child.duration_seconds)
                tag = f"  ({dur})" if dur else "  (时长未知)"
            else:
                tag = ""
            lines.append(f"{prefix}{connector}{child.name}{tag}")
