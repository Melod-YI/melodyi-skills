"""文件名解析与计划构建

解析常见 release 命名中的季/集信息，构建重命名与目录整理计划。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from melodyi_filebot.models import BuildPlanResult, CandidateSummary, PlanOperation, ShowSummary

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


_INVALID_CHARS = '<>:"/\\|?*'


def _sanitize(name: str) -> str:
    """清理 Jellyfin 不允许的文件名字符"""
    for ch in _INVALID_CHARS:
        name = name.replace(ch, "_")
    return name.strip().rstrip(".")


def _show_folder(show: ShowSummary) -> str:
    """剧文件夹名：剧名 (年) [tmdbid-xxx]"""
    year = f" ({show.year})" if show.year else ""
    return _sanitize(f"{show.title}{year} [tmdbid-{show.tmdb_id}]")


def _season_folder(season_number: int) -> str:
    """季文件夹名：Season 01（补零到 2 位）"""
    return f"Season {season_number:02d}"


def _episode_filename(
    show: ShowSummary, season: int, episode: int, episode_end: Optional[int], part: Optional[int], ext: str
) -> str:
    """集文件名：剧名 (年) S01E01[-E02][-part1].ext"""
    year = f" ({show.year})" if show.year else ""
    base = f"{_sanitize(show.title)}{year} S{season:02d}E{episode:02d}"
    if episode_end:
        base += f"-E{episode_end:02d}"
    if part:
        base += f"-part-{part}"
    return base + ext


def build_plan_tv(
    files: List[str],
    show: ShowSummary,
    dest_root: str,
    language: str = "zh-CN",
) -> BuildPlanResult:
    """构建剧集重命名与目录整理计划（标准流程，P0 不含 NFO）

    Args:
        files: 源视频文件绝对路径列表
        show: TMDB 剧摘要
        dest_root: 目标媒体根目录
        language: 语言

    Returns:
        BuildPlanResult，含 mkdir/move 操作与警告
    """
    logger.info("构建剧集计划开始: show=%s, 文件数=%d", show.title, len(files))
    operations: List[PlanOperation] = []
    warnings: List[str] = []

    show_folder = _show_folder(show)
    show_dir = f"{dest_root}/{show_folder}"
    operations.append(PlanOperation(type="mkdir", path=show_dir))

    created_seasons: set = set()
    for f in files:
        parsed = parse_filename(f)
        if parsed.episode is None:
            warnings.append(f"无法解析集号，跳过: {f}")
            logger.warning("无法解析集号: %s", f)
            continue
        season = parsed.season if parsed.season is not None else 1
        season_dir = f"{show_dir}/{_season_folder(season)}"
        if season not in created_seasons:
            operations.append(PlanOperation(type="mkdir", path=season_dir))
            created_seasons.add(season)

        target_name = _episode_filename(
            show, season, parsed.episode, parsed.episode_end, parsed.part, parsed.ext
        )
        target = f"{season_dir}/{target_name}"
        operations.append(PlanOperation(type="move", source=f, path=target))

    logger.info(
        "构建剧集计划完成: show=%s, 操作数=%d, 警告数=%d",
        show.title, len(operations), len(warnings),
    )
    return BuildPlanResult(operations=operations, spec_applied="standard", warnings=warnings)


def build_plan_movie(
    files: List[str], movie: CandidateSummary, dest_root: str
) -> BuildPlanResult:
    """构建电影重命名计划（P0 不含 NFO）

    Args:
        files: 源视频文件路径列表（取第一个为正片，其余作 warning）
        movie: TMDB 电影候选摘要
        dest_root: 目标媒体根目录

    Returns:
        BuildPlanResult
    """
    logger.info("构建电影计划开始: movie=%s, 文件数=%d", movie.title, len(files))
    operations: List[PlanOperation] = []
    warnings: List[str] = []

    year = f" ({movie.year})" if movie.year else ""
    folder = _sanitize(f"{movie.title}{year} [tmdbid-{movie.tmdb_id}]")
    movie_dir = f"{dest_root}/{folder}"
    operations.append(PlanOperation(type="mkdir", path=movie_dir))

    if not files:
        warnings.append("未找到视频文件")
        logger.warning("未找到视频文件: movie=%s", movie.title)
        logger.info("构建电影计划完成（无文件）: movie=%s", movie.title)
        return BuildPlanResult(operations=operations, spec_applied="standard", warnings=warnings)

    target_name = _sanitize(f"{movie.title}{year}") + Path(files[0]).suffix
    target = f"{movie_dir}/{target_name}"
    operations.append(PlanOperation(type="move", source=files[0], path=target))
    for extra in files[1:]:
        warnings.append(f"电影存在多个视频文件，已忽略: {extra}")
        logger.warning("电影多文件忽略: %s", extra)

    logger.info("构建电影计划完成: movie=%s", movie.title)
    return BuildPlanResult(operations=operations, spec_applied="standard", warnings=warnings)
