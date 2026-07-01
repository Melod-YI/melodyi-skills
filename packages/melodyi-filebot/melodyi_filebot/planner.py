"""文件名解析与计划构建

解析常见 release 命名中的季/集信息，构建重命名与目录整理计划。
"""

from __future__ import annotations

import logging
import os
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


def _companion_ops(
    video_source: str, video_target: str, video_target_name: str
) -> List[PlanOperation]:
    """为视频 move 生成伴生文件 move 操作（字幕等 sidecar）

    伴生 = 同目录下「视频 stem.」前缀的非视频文件（由 fsops.find_companions 发现）。
    目标名 = 改名后视频 stem + 原后缀（语言 token 等原样保留），落到视频目标同目录。

    Args:
        video_source: 视频源路径
        video_target: 视频目标完整路径
        video_target_name: 视频目标文件名（含扩展名）

    Returns:
        伴生 move 操作列表
    """
    from melodyi_filebot.fsops import find_companions  # 延迟导入，避免与 fsops 循环
    companions = find_companions(video_source)
    if not companions:
        return []
    target_dir = os.path.dirname(video_target)
    video_stem = Path(video_source).stem
    new_stem = Path(video_target_name).stem
    ops: List[PlanOperation] = []
    for comp in companions:
        suffix_part = Path(comp).name[len(video_stem):]
        comp_target = os.path.join(target_dir, new_stem + suffix_part)
        ops.append(PlanOperation(type="move", source=os.path.normpath(comp), path=comp_target))
        logger.info("伴生改名: %s -> %s", comp, comp_target)
    return ops


def draft_plan(
    folder_spec: dict,
    language: str = "zh-CN",
    fetch_show_summary=None,
    fetch_season_episodes=None,
    fetch_bangumi_episodes=None,
) -> "Plan":
    """folder→target 输入 → Plan（调 API 解析来源）

    Args:
        folder_spec: {show: {tmdb_id, bangumi_subject_id?}, folders: [{path, target, bangumi_subject_id?}]}
        language: 语言
        fetch_*: 可注入的 fetch 函数（单测用）；默认接 tmdb/bangumi 模块

    Returns:
        Plan（纯映射，含来源 spec 与 warnings）
    """
    from melodyi_filebot.models import (
        Plan, ShowRef, SeasonEntry, EpisodeEntry, FileTarget, NfoSource,
    )
    if fetch_show_summary is None:
        from melodyi_filebot import tmdb as _tmdb
        fetch_show_summary = _tmdb.get_show_summary
    if fetch_season_episodes is None:
        from melodyi_filebot import tmdb as _tmdb
        fetch_season_episodes = _tmdb.get_season_episodes
    if fetch_bangumi_episodes is None:
        from melodyi_filebot import bangumi as _bg
        fetch_bangumi_episodes = _bg.get_subject_episodes

    logger.info("draft_plan 开始: folder_spec=%s, language=%s", folder_spec, language)
    show_spec = folder_spec["show"]
    tmdb_id = show_spec["tmdb_id"]
    show_bg = show_spec.get("bangumi_subject_id")
    show = fetch_show_summary(tmdb_id, language=language)
    show_ref = ShowRef(
        tmdb_id=tmdb_id, bangumi_subject_id=show_bg,
        title=show.title, original_title=show.original_title,
        year=show.year, language=language,
    )
    seasons_seen: dict = {}  # season -> SeasonEntry
    episodes: list = []
    warnings: list = []
    for folder in folder_spec["folders"]:
        folder_bg = folder.get("bangumi_subject_id", show_bg)
        target = folder["target"]
        folder_path = Path(folder["path"])
        files = [str(p) for p in sorted(folder_path.iterdir())
                 if p.suffix.lower() in VIDEO_EXTS] if folder_path.is_dir() else []
        # 安全默认：避免后续分支未赋值时引用未定义变量
        tmdb_season_present = False
        use_bangumi = False
        if target["kind"] == "season":
            sn = target["season"]
            try:
                tmdb_eps = {e.episode_number: e for e in fetch_season_episodes(tmdb_id, sn, language=language)}
                tmdb_season_present = True
            except RuntimeError:
                tmdb_eps = {}
                tmdb_season_present = False
                warnings.append(f"TMDB 无第 {sn} 季，来源切 bangumi: {folder['path']}")
                logger.warning("TMDB 无第 %d 季，来源切 bangumi: %s", sn, folder['path'])
            # 仅当 TMDB 无季且有 bangumi 来源时才切到 bangumi；否则保持 tmdb（generate-nfo 时将失败）
            use_bangumi = (not tmdb_season_present) and folder_bg is not None
            if not tmdb_season_present and not folder_bg:
                warnings.append(f"TMDB 无第 {sn} 季且无 bangumi 来源，generate-nfo 时将失败: {folder['path']}")
                logger.warning("TMDB 无第 %d 季且无 bangumi 来源: %s", sn, folder['path'])
            if sn not in seasons_seen:
                src = NfoSource(
                    provider="bangumi" if use_bangumi else "tmdb",
                    tmdb_id=tmdb_id if not use_bangumi else None,
                    season=sn if not use_bangumi else None,
                    bangumi_subject_id=folder_bg if use_bangumi else None,
                )
                seasons_seen[sn] = SeasonEntry(season=sn, source=src)
        elif target["kind"] == "episode_group":
            # episode_group 完整解析留后；此处按文件序号 + season 占位
            tmdb_eps = {}
            sn = target.get("season", 1)
            tmdb_season_present = True
            if sn not in seasons_seen:
                seasons_seen[sn] = SeasonEntry(
                    season=sn, source=NfoSource(provider="tmdb", tmdb_id=tmdb_id, season=sn))
        else:
            warnings.append(f"未知 target.kind: {target['kind']}")
            logger.warning("未知 target.kind: %s", target['kind'])
            continue
        # bangumi 集列表（按集号映射）
        bg_eps = {}
        if folder_bg:
            for be in fetch_bangumi_episodes(folder_bg):
                ep_num = be.ep or int(be.sort)
                if ep_num is not None:
                    bg_eps[ep_num] = be
        for f in files:
            parsed = parse_filename(f)
            ep = parsed.episode
            if ep is None:
                warnings.append(f"无法解析集号: {f}")
                logger.warning("无法解析集号: %s", f)
                continue
            # TMDB 季存在时校验集号是否在 TMDB 集列表中
            if tmdb_season_present and ep not in tmdb_eps:
                warnings.append(f"TMDB 第 {sn} 季无第 {ep} 集: {f}")
                logger.warning("TMDB 第 %d 季无第 %d 集: %s", sn, ep, f)
            bg_ep = bg_eps.get(ep)
            src = NfoSource(
                provider="bangumi" if use_bangumi else "tmdb",
                tmdb_id=tmdb_id if not use_bangumi else None,
                season=sn if not use_bangumi else None,
                episode=ep if not use_bangumi else None,
                bangumi_subject_id=folder_bg,
                bangumi_episode_id=bg_ep.episode_id if bg_ep else None,
            )
            if not tmdb_season_present and not bg_ep:
                warnings.append(f"bangumi 未匹配到第 {ep} 集: {f}")
                logger.warning("bangumi 未匹配到第 %d 集: %s", ep, f)
            episodes.append(EpisodeEntry(
                file=os.path.normpath(f),
                target=FileTarget(season=sn, episode=ep,
                                  episode_end=parsed.episode_end, part=parsed.part),
                source=src,
            ))
    logger.info("draft_plan 完成: 季数=%d, 集数=%d, 警告数=%d",
                len(seasons_seen), len(episodes), len(warnings))
    return Plan(show=show_ref, seasons=list(seasons_seen.values()),
                episodes=episodes, warnings=warnings)


def build_plan_from_plan(plan: "Plan", dest_root: str, with_nfo: bool = True) -> BuildPlanResult:
    """Plan → BuildPlanResult（move + nfo 操作）

    Args:
        plan: 纯映射 Plan（agent 编辑后）
        dest_root: 目标媒体根目录
        with_nfo: 是否生成 nfo 操作

    Returns:
        BuildPlanResult（operations + nfo_operations，spec_applied="plan"）
    """
    from melodyi_filebot.models import ShowSummary, NfoOperation, NfoSource
    logger.info("按 Plan 构建执行清单: tmdb_id=%s, 集数=%d, nfo=%s",
                plan.show.tmdb_id, len(plan.episodes), with_nfo)
    # 用 ShowRef 构造 ShowSummary 复用既有命名函数
    show = ShowSummary(
        tmdb_id=plan.show.tmdb_id, title=plan.show.title,
        original_title=plan.show.original_title, year=plan.show.year,
        total_seasons=len(plan.seasons), total_episodes=len(plan.episodes),
        seasons=[], episode_groups=[],
    )
    dest_root = os.path.normpath(dest_root)
    show_dir = os.path.join(dest_root, _show_folder(show))
    operations: List[PlanOperation] = [PlanOperation(type="mkdir", path=show_dir)]
    nfo_operations: list = []
    warnings: list = list(plan.warnings)
    created_seasons: set = set()
    for m in plan.episodes:
        # Plan 已由 agent 终稿，FileTarget.episode 为必填 int，此处无需再校验缺失
        season = m.target.season
        season_dir = os.path.join(show_dir, _season_folder(season))
        if season not in created_seasons:
            operations.append(PlanOperation(type="mkdir", path=season_dir))
            created_seasons.add(season)
        ext = Path(m.file).suffix
        target_name = _episode_filename(
            show, season, m.target.episode, m.target.episode_end, m.target.part, ext)
        target = os.path.join(season_dir, target_name)
        operations.append(PlanOperation(type="move", source=os.path.normpath(m.file), path=target))
        operations.extend(_companion_ops(m.file, target, target_name))
        if with_nfo:
            ep_nfo_path = target.rsplit(".", 1)[0] + ".nfo"
            nfo_operations.append(NfoOperation(
                type="episode", path=ep_nfo_path, season=season, episode=m.target.episode,
                source=m.source, video_path=os.path.normpath(m.file)))
    if with_nfo:
        # tvshow nfo
        show_source = NfoSource(provider="tmdb", tmdb_id=plan.show.tmdb_id,
                                bangumi_subject_id=plan.show.bangumi_subject_id)
        nfo_operations.insert(0, NfoOperation(
            type="tvshow", path=os.path.join(show_dir, "tvshow.nfo"), source=show_source))
        # season nfo（每个出现的季）
        season_sources = {s.season: s.source for s in plan.seasons}
        for sn in sorted(created_seasons):
            nfo_operations.append(NfoOperation(
                type="season", path=os.path.join(show_dir, _season_folder(sn), "season.nfo"),
                season=sn, source=season_sources.get(sn, NfoSource(provider="tmdb", tmdb_id=plan.show.tmdb_id, season=sn))))
    logger.info("按 Plan 构建执行清单完成: 操作数=%d, nfo 操作数=%d",
                len(operations), len(nfo_operations))
    return BuildPlanResult(operations=operations, nfo_operations=nfo_operations,
                           spec_applied="plan", warnings=warnings)
