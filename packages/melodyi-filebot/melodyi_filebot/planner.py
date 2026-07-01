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


def build_plan_tv(
    files: List[str],
    show: ShowSummary,
    dest_root: str,
    language: str = "zh-CN",
    season_hint: Optional[int] = None,
) -> BuildPlanResult:
    """构建剧集重命名与目录整理计划（标准流程，P0 不含 NFO）

    Args:
        files: 源视频文件绝对路径列表
        show: TMDB 剧摘要
        dest_root: 目标媒体根目录
        language: 语言
        season_hint: 季提示。文件名未带季标记时用此季号，而非默认 1；
            文件名有显式季标记（如 S00 特别篇）仍以文件名为准。

    Returns:
        BuildPlanResult，含 mkdir/move 操作与警告
    """
    logger.info("构建剧集计划开始: show=%s, 文件数=%d, season_hint=%s", show.title, len(files), season_hint)
    operations: List[PlanOperation] = []
    warnings: List[str] = []

    # 归一化目标根目录：去尾斜杠、折叠重复分隔符、转平台原生分隔符
    dest_root = os.path.normpath(dest_root)
    show_folder = _show_folder(show)
    show_dir = os.path.join(dest_root, show_folder)
    operations.append(PlanOperation(type="mkdir", path=show_dir))

    created_seasons: set = set()
    for f in files:
        parsed = parse_filename(f)
        if parsed.episode is None:
            warnings.append(f"无法解析集号，跳过: {f}")
            logger.warning("无法解析集号: %s", f)
            continue
        # 季号优先级：文件名显式季标记 > season_hint > 默认 1
        if parsed.season is not None:
            season = parsed.season
        elif season_hint is not None:
            season = season_hint
        else:
            season = 1
        season_dir = os.path.join(show_dir, _season_folder(season))
        if season not in created_seasons:
            operations.append(PlanOperation(type="mkdir", path=season_dir))
            created_seasons.add(season)

        target_name = _episode_filename(
            show, season, parsed.episode, parsed.episode_end, parsed.part, parsed.ext
        )
        target = os.path.join(season_dir, target_name)
        operations.append(PlanOperation(type="move", source=os.path.normpath(f), path=target))
        operations.extend(_companion_ops(f, target, target_name))

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

    dest_root = os.path.normpath(dest_root)
    year = f" ({movie.year})" if movie.year else ""
    folder = _sanitize(f"{movie.title}{year} [tmdbid-{movie.tmdb_id}]")
    movie_dir = os.path.join(dest_root, folder)
    operations.append(PlanOperation(type="mkdir", path=movie_dir))

    if not files:
        warnings.append("未找到视频文件")
        logger.warning("未找到视频文件: movie=%s", movie.title)
        logger.info("构建电影计划完成（无文件）: movie=%s", movie.title)
        return BuildPlanResult(operations=operations, spec_applied="standard", warnings=warnings)

    target_name = _sanitize(f"{movie.title}{year}") + Path(files[0]).suffix
    target = os.path.join(movie_dir, target_name)
    operations.append(PlanOperation(type="move", source=os.path.normpath(files[0]), path=target))
    operations.extend(_companion_ops(files[0], target, target_name))
    for extra in files[1:]:
        warnings.append(f"电影存在多个视频文件，已忽略: {extra}")
        logger.warning("电影多文件忽略: %s", extra)

    logger.info("构建电影计划完成: movie=%s", movie.title)
    return BuildPlanResult(operations=operations, spec_applied="standard", warnings=warnings)


def draft_map_tv(
    files: List[str],
    tmdb_id: int,
    season_hint: Optional[int] = None,
    language: str = "zh-CN",
) -> "PlanMap":
    """生成剧的文件→季/集 映射初版（供 agent/用户编辑）

    扫描+解析文件名，输出每个文件的解析猜测；无法解析的项 season/episode 为 None，
    由 agent 对照 fetch-summary 后补全。不调用 TMDB，仅透传 tmdb_id。

    Args:
        files: 源视频文件绝对路径列表
        tmdb_id: TMDB 剧 ID
        season_hint: 季提示（文件名无季标记时填入）
        language: 语言

    Returns:
        PlanMap 初版
    """
    from melodyi_filebot.models import FileMapping, PlanMap
    logger.info("生成映射初版开始: tmdb_id=%s, 文件数=%d, season_hint=%s", tmdb_id, len(files), season_hint)
    mappings: List[FileMapping] = []
    for f in files:
        parsed = parse_filename(f)
        season = parsed.season if parsed.season is not None else season_hint
        mappings.append(
            FileMapping(
                file=os.path.normpath(f),
                season=season,
                episode=parsed.episode,
                episode_end=parsed.episode_end,
                part=parsed.part,
            )
        )
    logger.info("生成映射初版完成: 映射数=%d", len(mappings))
    return PlanMap(media_type="tv", tmdb_id=tmdb_id, language=language, mappings=mappings)


def build_plan_tv_from_map(
    plan_map: "PlanMap",
    show: ShowSummary,
    dest_root: str,
) -> BuildPlanResult:
    """按显式映射构建剧集计划（override，不解析文件名）

    Args:
        plan_map: 显式文件→季/集 映射
        show: TMDB 剧摘要（用于目录命名）
        dest_root: 目标媒体根目录

    Returns:
        BuildPlanResult，spec_applied="override"
    """
    logger.info("按映射构建剧集计划开始: show=%s, 映射数=%d", show.title, len(plan_map.mappings))
    dest_root = os.path.normpath(dest_root)
    show_dir = os.path.join(dest_root, _show_folder(show))
    operations: List[PlanOperation] = [PlanOperation(type="mkdir", path=show_dir)]
    warnings: List[str] = []

    created_seasons: set = set()
    for m in plan_map.mappings:
        if m.episode is None:
            warnings.append(f"映射缺少集号，跳过: {m.file}")
            logger.warning("映射缺少集号: %s", m.file)
            continue
        season = m.season if m.season is not None else 1
        season_dir = os.path.join(show_dir, _season_folder(season))
        if season not in created_seasons:
            operations.append(PlanOperation(type="mkdir", path=season_dir))
            created_seasons.add(season)
        ext = Path(m.file).suffix
        target_name = _episode_filename(show, season, m.episode, m.episode_end, m.part, ext)
        target = os.path.join(season_dir, target_name)
        operations.append(PlanOperation(type="move", source=os.path.normpath(m.file), path=target))
        operations.extend(_companion_ops(m.file, target, target_name))

    logger.info("按映射构建剧集计划完成: 操作数=%d, 警告数=%d", len(operations), len(warnings))
    return BuildPlanResult(operations=operations, spec_applied="override", warnings=warnings)


def build_plan_movie_from_map(
    plan_map: "PlanMap",
    movie: CandidateSummary,
    dest_root: str,
) -> BuildPlanResult:
    """按显式映射构建电影计划（override，第一个映射为正片）

    Args:
        plan_map: 显式文件映射
        movie: TMDB 电影摘要
        dest_root: 目标媒体根目录

    Returns:
        BuildPlanResult，spec_applied="override"
    """
    logger.info("按映射构建电影计划开始: movie=%s, 映射数=%d", movie.title, len(plan_map.mappings))
    dest_root = os.path.normpath(dest_root)
    year = f" ({movie.year})" if movie.year else ""
    folder = _sanitize(f"{movie.title}{year} [tmdbid-{movie.tmdb_id}]")
    movie_dir = os.path.join(dest_root, folder)
    operations: List[PlanOperation] = [PlanOperation(type="mkdir", path=movie_dir)]
    warnings: List[str] = []

    if not plan_map.mappings:
        warnings.append("映射为空，未生成 move 操作")
        logger.warning("映射为空: movie=%s", movie.title)
        return BuildPlanResult(operations=operations, spec_applied="override", warnings=warnings)

    main = plan_map.mappings[0]
    target_name = _sanitize(f"{movie.title}{year}") + Path(main.file).suffix
    target = os.path.join(movie_dir, target_name)
    operations.append(PlanOperation(type="move", source=os.path.normpath(main.file), path=target))
    operations.extend(_companion_ops(main.file, target, target_name))
    for extra in plan_map.mappings[1:]:
        warnings.append(f"电影存在多个视频文件，已忽略: {extra.file}")
        logger.warning("电影多文件忽略: %s", extra.file)

    logger.info("按映射构建电影计划完成: movie=%s", movie.title)
    return BuildPlanResult(operations=operations, spec_applied="override", warnings=warnings)


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
        if m.target.episode is None:
            warnings.append(f"映射缺少集号，跳过: {m.file}")
            continue
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
                source=m.source))
    if with_nfo:
        # tvshow nfo
        show_source = NfoSource(provider="tmdb", tmdb_id=plan.show.tmdb_id,
                                bangumi_subject_id=plan.show.bangumi_subject_id)
        nfo_operations.insert(0, NfoOperation(
            type="tvshow", path=os.path.join(show_dir, "tvshow.nfo"), source=show_source))
        # season nfo（每个出现的季）
        season_sources = {s.season: s.source for s in plan.seasons}
        for sn in created_seasons:
            nfo_operations.append(NfoOperation(
                type="season", path=os.path.join(show_dir, _season_folder(sn), "season.nfo"),
                season=sn, source=season_sources.get(sn, NfoSource(provider="tmdb", tmdb_id=plan.show.tmdb_id, season=sn))))
    logger.info("按 Plan 构建执行清单完成: 操作数=%d, nfo 操作数=%d",
                len(operations), len(nfo_operations))
    return BuildPlanResult(operations=operations, nfo_operations=nfo_operations,
                           spec_applied="plan", warnings=warnings)
