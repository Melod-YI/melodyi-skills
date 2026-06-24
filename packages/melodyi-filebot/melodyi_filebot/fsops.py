"""文件系统操作

扫描、执行计划、事务日志、回滚。唯一触碰文件系统的模块。
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import List

from melodyi_filebot.models import BuildPlanResult, PlanOperation
from melodyi_filebot.planner import VIDEO_EXTS

logger = logging.getLogger(__name__)


def scan_video_files(root: str) -> List[str]:
    """递归扫描目录下的视频文件

    Args:
        root: 扫描根目录

    Returns:
        视频文件绝对路径列表

    Raises:
        FileNotFoundError: 目录不存在
    """
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"目录不存在: {root}")
    files = sorted(
        str(p)
        for p in root_path.rglob("*")
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    )
    logger.info("扫描完成: root=%s, 视频文件数=%d", root, len(files))
    return files


def find_companions(video_path: str) -> List[str]:
    """查找视频的伴生文件（字幕等 sidecar）

    伴生 = 与视频同目录、文件名以「视频 stem + '.'」开头的非视频文件。
    要求 stem 后紧跟 '.'，确保伴生的前缀是视频 stem 的完整 dotted 段，
    避免对 `Show S01E01` 的视频误 claim `Show S01E01-part-1.ass` 这类部分前缀。

    Args:
        video_path: 视频文件绝对路径

    Returns:
        伴生文件绝对路径列表（升序）。目录不存在时返回空列表。
    """
    p = Path(video_path)
    d = p.parent
    if not d.exists():
        logger.info("查找伴生跳过（目录不存在）: %s", video_path)
        return []
    vstem = p.stem
    video_name = p.name
    companions = []
    for sibling in d.iterdir():
        if not sibling.is_file():
            continue
        name = sibling.name
        if name == video_name:
            continue  # 视频自身
        if not name.startswith(vstem):
            continue
        # stem 后必须紧跟 '.'（完整 dotted 段，排除部分前缀匹配）
        if len(name) <= len(vstem) or name[len(vstem)] != ".":
            continue
        if sibling.suffix.lower() in VIDEO_EXTS:
            continue  # 同前缀的其他视频不当伴生
        companions.append(str(sibling))
    companions.sort()
    logger.info("查找伴生: video=%s, 伴生数=%d", video_path, len(companions))
    return companions


def _validate(plan: BuildPlanResult) -> None:
    """dry-run 前置校验：源存在、目标无冲突

    Raises:
        FileNotFoundError: 源文件不存在
        FileExistsError: 目标已存在
    """
    move_targets: set = set()
    for op in plan.operations:
        if op.type == "move":
            if not Path(op.source).exists():
                raise FileNotFoundError(f"源文件不存在: {op.source}")
            if op.path in move_targets:
                raise FileExistsError(f"目标路径重复: {op.path}")
            move_targets.add(op.path)
            if Path(op.path).exists():
                raise FileExistsError(f"目标已存在: {op.path}")


def execute_plan(
    plan: BuildPlanResult,
    dry_run: bool = True,
    snapshot_path: str = None,
) -> dict:
    """执行计划

    Args:
        plan: 构建好的计划
        dry_run: True 只校验不执行；False 真正执行
        snapshot_path: 事务日志保存路径（dry_run=False 时写入）

    Returns:
        dry_run=True 返回 None；dry_run=False 返回 snapshot dict
    """
    _validate(plan)
    if dry_run:
        logger.info("dry-run 校验通过，未执行任何操作")
        return None

    logger.info("执行计划开始: 操作数=%d", len(plan.operations))
    log: List[dict] = []
    for op in plan.operations:
        if op.type == "mkdir":
            Path(op.path).mkdir(parents=True, exist_ok=True)
            log.append({"type": "mkdir", "path": op.path, "inverse": None})
            logger.info("创建目录: %s", op.path)
        elif op.type == "move":
            Path(op.path).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(op.source, op.path)
            log.append({"type": "move", "path": op.path, "source": op.source, "inverse": "move_back"})
            logger.info("移动文件: %s -> %s", op.source, op.path)

    snapshot = {"operations": list(reversed(log))}
    if snapshot_path:
        Path(snapshot_path).write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("事务日志已写入: %s", snapshot_path)
    logger.info("执行计划完成")
    return snapshot


def undo(snapshot: dict) -> None:
    """按事务日志逆序回放逆操作

    Args:
        snapshot: execute_plan 返回的事务日志 dict
    """
    ops = snapshot.get("operations", [])
    logger.info("回滚开始: 逆操作数=%d", len(ops))
    for op in ops:
        if op["type"] == "move":
            # 逆操作：把目标移回源
            shutil.move(op["path"], op["source"])
            logger.info("回滚移动: %s -> %s", op["path"], op["source"])
        elif op["type"] == "mkdir":
            # 仅当目录为空时删除
            p = Path(op["path"])
            try:
                p.rmdir()
                logger.info("回滚删除目录: %s", op["path"])
            except OSError:
                logger.info("目录非空，保留: %s", op["path"])
    logger.info("回滚完成")


def undo_from_file(snapshot_path: str) -> None:
    """从事务日志文件回滚

    Args:
        snapshot_path: 事务日志文件路径
    """
    data = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    undo(data)
