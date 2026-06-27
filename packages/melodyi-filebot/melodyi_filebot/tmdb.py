"""TMDB 调用封装

初期通过 import tmdbsimple 调用 TMDB API。后续若用到的 API 很少，可考虑自实现。
所有方法返回原始 dict 或摘要模型，完整 overview 不外泄给 agent。
"""

from __future__ import annotations

import logging
from typing import List, Optional

import tmdbsimple as tmdbsimple

from melodyi_filebot import config
from melodyi_filebot.models import CandidateSummary, ShowSummary, EpisodeBrief, EpisodeGroupDetail
from melodyi_filebot import summarize

logger = logging.getLogger(__name__)

_api_key: Optional[str] = None


def _ensure_key() -> str:
    """确保 API key 已加载并设置到 tmdbsimple

    Returns:
        API key

    Raises:
        RuntimeError: 未配置 API key
    """
    global _api_key
    if _api_key is None:
        _api_key = config.load_tmdb_api_key()
    if not _api_key:
        raise RuntimeError(
            "未配置 TMDB_API_KEY。请设置环境变量或在 ~/.melodyi-skills/melodyi-filebot/config.yaml 中配置 tmdb_api_key。"
        )
    tmdbsimple.API_KEY = _api_key
    return _api_key


def search(
    query: str,
    media_type: str = "tv",
    language: str = "zh-CN",
    year: Optional[int] = None,
) -> List[CandidateSummary]:
    """关键字搜索 TMDB

    Args:
        query: 搜索关键字
        media_type: "tv" | "movie" | "multi"
        language: 语言（默认 zh-CN）
        year: 年份过滤（仅 tv/movie）

    Returns:
        候选摘要列表
    """
    _ensure_key()
    logger.info("TMDB 搜索开始: query=%r, type=%s, lang=%s", query, media_type, language)
    s = tmdbsimple.Search()
    kwargs = {"query": query, "language": language}
    if year is not None and media_type == "tv":
        kwargs["first_air_date_year"] = year
    elif year is not None and media_type == "movie":
        kwargs["year"] = year

    if media_type == "tv":
        resp = s.tv(**kwargs)
    elif media_type == "movie":
        resp = s.movie(**kwargs)
    elif media_type == "multi":
        resp = s.multi(**kwargs)
    else:
        raise ValueError(f"不支持的 media_type: {media_type}")

    cands = summarize.candidates_from_search(resp, media_type=media_type)
    logger.info("TMDB 搜索完成: 命中 %d 条", len(cands))
    return cands


def get_show_summary(tmdb_id: int, language: str = "zh-CN") -> ShowSummary:
    """获取剧摘要

    Args:
        tmdb_id: TMDB 剧 ID
        language: 语言

    Returns:
        ShowSummary 摘要
    """
    _ensure_key()
    logger.info("获取剧详情开始: id=%s, lang=%s", tmdb_id, language)
    tv = tmdbsimple.TV(id=tmdb_id)
    detail = tv.info(append_to_response="episode_groups", language=language)
    summary = summarize.show_summary_from_detail(detail)
    logger.info("获取剧详情完成: id=%s, 季数=%d", tmdb_id, summary.total_seasons)
    return summary


def get_season_episodes(
    tmdb_id: int, season_number: int, language: str = "zh-CN"
) -> List[EpisodeBrief]:
    """获取某季集摘要（懒加载用）

    Args:
        tmdb_id: TMDB 剧 ID
        season_number: 季号
        language: 语言

    Returns:
        集摘要列表
    """
    _ensure_key()
    logger.info("获取季集列表开始: id=%s, season=%s", tmdb_id, season_number)
    seasons = tmdbsimple.TV_Seasons(tv_id=tmdb_id, season_number=season_number)
    detail = seasons.info(language=language)
    eps = detail.get("episodes", []) or []
    briefs = [
        EpisodeBrief(
            episode_number=e.get("episode_number", 0),
            name=e.get("name", "") or "",
            air_date=e.get("air_date"),
            overview_length=len(e.get("overview") or ""),
            runtime=e.get("runtime"),
        )
        for e in eps
    ]
    logger.info("获取季集列表完成: id=%s, season=%s, 集数=%d", tmdb_id, season_number, len(briefs))
    return briefs


def get_movie_summary(tmdb_id: int, language: str = "zh-CN") -> CandidateSummary:
    """获取电影摘要

    Args:
        tmdb_id: TMDB 电影 ID
        language: 语言

    Returns:
        CandidateSummary（media_type="movie"）
    """
    _ensure_key()
    logger.info("获取电影详情开始: id=%s, lang=%s", tmdb_id, language)
    m = tmdbsimple.Movies(id=tmdb_id)
    detail = m.info(language=language)
    cands = summarize.candidates_from_search({"results": [detail]}, media_type="movie")
    movie = cands[0] if cands else CandidateSummary(
        tmdb_id=tmdb_id, title="", original_title="", media_type="movie"
    )
    logger.info("获取电影详情完成: id=%s", tmdb_id)
    return movie


def get_episode_group(group_id: str, language: str = "zh-CN") -> EpisodeGroupDetail:
    """获取剧集组详情（含子组与集列表）

    用于非标场景1（如重置版归在剧集组）：取 group 的子组结构 + 每集信息。

    Args:
        group_id: TMDB 剧集组 ID
        language: 语言

    Returns:
        EpisodeGroupDetail（子组 + 集列表，集带 season_number）
    """
    _ensure_key()
    logger.info("获取剧集组详情开始: group_id=%s, lang=%s", group_id, language)
    eg = tmdbsimple.TV_Episode_Groups(id=group_id)
    detail = eg.info(language=language)
    result = summarize.episode_group_from_detail(detail)
    logger.info(
        "获取剧集组详情完成: group_id=%s, 子组数=%d, 集数=%d",
        group_id, result.group_count, result.episode_count,
    )
    return result
