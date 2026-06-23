"""摘要压缩

把 TMDB 原始 dict 压缩成进上下文的摘要模型。
关键：不外泄完整 overview，仅计算 overview_available/length。
overview 长度 <10 视为不可用（触发 Bangumi 补全的阈值，P1+ 使用）。
"""

from __future__ import annotations

from typing import List, Optional

from melodyi_filebot.models import (
    CandidateSummary,
    EpisodeGroupBrief,
    SeasonSummary,
    ShowSummary,
)

OVERVIEW_MIN_LENGTH = 10


def _year_from_date(date_str: Optional[str]) -> Optional[int]:
    """从 YYYY-MM-DD 提取年份"""
    if not date_str or len(date_str) < 4:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return None


def _overview_len(overview: Optional[str]) -> int:
    return len(overview or "")


def _overview_available(overview: Optional[str]) -> bool:
    return _overview_len(overview) >= OVERVIEW_MIN_LENGTH


def show_summary_from_detail(detail: dict) -> ShowSummary:
    """TV.info 响应 → ShowSummary

    Args:
        detail: TMDB TV.info 原始响应（含 seasons、episode_groups）

    Returns:
        ShowSummary 摘要
    """
    seasons_raw = detail.get("seasons", []) or []
    seasons = [
        SeasonSummary(
            season_number=s.get("season_number", 0),
            name=s.get("name", "") or "",
            episode_count=s.get("episode_count", 0) or 0,
            first_air_date=s.get("air_date"),
            last_air_date=s.get("air_date"),
            overview_available=_overview_available(s.get("overview")),
        )
        for s in seasons_raw
    ]
    groups_raw = (detail.get("episode_groups") or {}).get("results", []) or []
    episode_groups = [
        EpisodeGroupBrief(
            id=str(g["id"]),
            name=g.get("name", "") or "",
            type=g.get("type", 0) or 0,
        )
        for g in groups_raw
    ]
    overview = detail.get("overview")
    return ShowSummary(
        tmdb_id=detail.get("id"),
        title=detail.get("name", "") or "",
        original_title=detail.get("original_name", "") or "",
        year=_year_from_date(detail.get("first_air_date")),
        total_seasons=len(seasons),
        total_episodes=sum(s.episode_count for s in seasons),
        overview_available=_overview_available(overview),
        overview_length=_overview_len(overview),
        seasons=seasons,
        episode_groups=episode_groups,
    )


def candidates_from_search(search_resp: dict, media_type: str) -> List[CandidateSummary]:
    """search 响应 → 候选摘要列表

    Args:
        search_resp: TMDB search 响应
        media_type: "tv" | "movie"

    Returns:
        候选摘要列表
    """
    results = search_resp.get("results", []) or []
    date_field = "first_air_date" if media_type == "tv" else "release_date"
    name_field = "name" if media_type == "tv" else "title"
    orig_field = "original_name" if media_type == "tv" else "original_title"
    candidates = []
    for r in results:
        candidates.append(
            CandidateSummary(
                tmdb_id=r.get("id"),
                title=r.get(name_field, "") or "",
                original_title=r.get(orig_field, "") or "",
                year=_year_from_date(r.get(date_field)),
                overview_length=_overview_len(r.get("overview")),
                media_type=media_type,
            )
        )
    return candidates
