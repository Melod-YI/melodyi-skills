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
    files = [
        str(p)
        for p in root_path.rglob("*")
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    ]
    logger.info("扫描完成: root=%s, 视频文件数=%d", root, len(files))
    return files


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
