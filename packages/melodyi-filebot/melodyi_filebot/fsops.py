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
