"""文件名解析与计划构建

解析常见 release 命名中的季/集信息，构建重命名与目录整理计划。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from melodyi_filebot.models import BuildPlanResult, PlanOperation, ShowSummary

logger = logging.getLogger(__name__)

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".ts", ".m4v", ".wmv", ".flv"}

# S01E01 或 S01E01E02
_SXXEXX = re.compile(r"[Ss](\d{1,2})\s?[Ee](\d{1,3})(?:\s?[-]?\s?[Ee](\d{1,3}))?")
# S01E01-E02 范围
_SXXEXX_RANGE = re.compile(r"[Ss](\d{1,2})\s?[Ee](\d{1,3})\s?-\s?[Ee](\d{1,3})")
# 单独 E01
_EXX = re.compile(r"(?<![A-Za-z0-9])[Ee](\d{1,3})(?![A-Za-z0-9])")
# part-N / partN / .partN.
_PART = re.compile(r"[._-]part[._-]?(\d{1,2})", re.IGNORECASE)
# 方括号单集编号 [10]
_BRACKET_EP = re.compile(r"\[(\d{1,3})\]")


class ParsedFile(BaseModel):
    """解析后的文件信息"""

    path: str
    stem: str
    ext: str
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_end: Optional[int] = None  # 多集范围终点
    part: Optional[int] = None  # 分段编号


def parse_filename(filename: str) -> ParsedFile:
    """从文件名解析季/集信息

    支持常见格式：
        - Series S01E01.mkv
        - Series S01E01-E02.mkv（范围）
        - Series S01E01-part-1.mkv（分段）
        - [Studio] Title [10].mkv（方括号集号）

    Args:
        filename: 文件名（含扩展名）

    Returns:
        ParsedFile，未识别字段为 None
    """
    p = Path(filename)
    stem = p.stem
    ext = p.suffix

    season: Optional[int] = None
    episode: Optional[int] = None
    episode_end: Optional[int] = None

    m_range = _SXXEXX_RANGE.search(stem)
    m_single = _SXXEXX.search(stem)
    if m_range:
        season = int(m_range.group(1))
        episode = int(m_range.group(2))
        episode_end = int(m_range.group(3))
    elif m_single:
        season = int(m_single.group(1))
        episode = int(m_single.group(2))
        if m_single.group(3):
            episode_end = int(m_single.group(3))
    else:
        # 方括号集号（无季）
        m_bracket = _BRACKET_EP.search(stem)
        if m_bracket:
            episode = int(m_bracket.group(1))
        else:
            m_exx = _EXX.search(stem)
            if m_exx:
                episode = int(m_exx.group(1))

    part_m = _PART.search(stem)
    part = int(part_m.group(1)) if part_m else None

    return ParsedFile(
        path=str(filename),
        stem=stem,
        ext=ext,
        season=season,
        episode=episode,
        episode_end=episode_end,
        part=part,
    )
