"""摘要压缩

把 TMDB 原始 dict 压缩成进上下文的摘要模型。
关键：不外泄完整 overview，仅计算 overview_available/length。
overview 长度 <10 视为不可用（触发 Bangumi 补全的阈值，P1+ 使用）。
"""

from __future__ import annotations

from typing import List, Optional

from melodyi_filebot.models import (
    BangumiEpisodeBrief,
    BangumiSubjectSummary,
    CandidateSummary,
    EpisodeBrief,
    EpisodeGroupBrief,
    EpisodeGroupDetail,
    EpisodeGroupSub,
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
            episode_count=g.get("episode_count", 0) or 0,
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


def episode_group_from_detail(d: dict) -> EpisodeGroupDetail:
    """TMDB /tv/episode_group/{id} 响应 → EpisodeGroupDetail

    剧集组含嵌套子组（groups[]），每个子组含 episodes[]（带 season_number，因组可跨季）。

    Args:
        d: TMDB episode_group 详情响应

    Returns:
        剧集组详情（子组 + 集列表）
    """
    sub_groups = []
    for sg in (d.get("groups") or []):
        eps = [
            EpisodeBrief(
                episode_number=e.get("episode_number", 0) or 0,
                name=e.get("name", "") or "",
                air_date=e.get("air_date"),
                overview_length=_overview_len(e.get("overview")),
                runtime=e.get("runtime"),
                season_number=e.get("season_number"),
            )
            for e in (sg.get("episodes") or [])
        ]
        sub_groups.append(EpisodeGroupSub(name=sg.get("name", "") or "", episodes=eps))
    return EpisodeGroupDetail(
        id=str(d.get("id")),
        name=d.get("name", "") or "",
        type=d.get("type", 0) or 0,
        episode_count=d.get("episode_count", 0) or 0,
        group_count=d.get("group_count", 0) or 0,
        sub_groups=sub_groups,
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
    candidates = []
    for r in results:
        # multi 搜索时每条结果自带 media_type 字段，按其选字段；
        # tv/movie 搜索时用传入的 media_type 统一字段。
        effective_type = r.get("media_type", media_type) if media_type == "multi" else media_type
        # person 等非 tv/movie 类型无对应字段，统一按 movie 字段兜底（仅取 id/overview）
        use_tv = effective_type == "tv"
        date_field = "first_air_date" if use_tv else "release_date"
        name_field = "name" if use_tv else "title"
        orig_field = "original_name" if use_tv else "original_title"
        candidates.append(
            CandidateSummary(
                tmdb_id=r.get("id"),
                title=r.get(name_field, "") or "",
                original_title=r.get(orig_field, "") or "",
                year=_year_from_date(r.get(date_field)),
                overview_length=_overview_len(r.get("overview")),
                media_type=effective_type,
            )
        )
    return candidates


# ---------- Bangumi 压缩 ----------

def bangumi_subject_from_detail(d: dict) -> BangumiSubjectSummary:
    """Bangumi 条目原始 dict → BangumiSubjectSummary

    搜索响应与 subject 详情响应字段一致，共用此函数。

    Args:
        d: Bangumi /v0/subjects/{id} 或 /v0/search/subjects 的单条目

    Returns:
        条目摘要（含完整 summary）
    """
    summary = d.get("summary", "") or ""
    return BangumiSubjectSummary(
        subject_id=d.get("id"),
        type=d.get("type", 0) or 0,
        name=d.get("name", "") or "",
        name_cn=d.get("name_cn", "") or "",
        date=d.get("date"),
        eps=d.get("eps", 0) or 0,
        platform=d.get("platform", "") or "",
        summary=summary,
        summary_length=len(summary),
    )


def bangumi_subjects_from_search(items: list) -> List[BangumiSubjectSummary]:
    """搜索响应 data 列表 → 条目摘要列表"""
    return [bangumi_subject_from_detail(it) for it in (items or [])]


def bangumi_episodes_from_raw(items: list) -> List[BangumiEpisodeBrief]:
    """/v0/episodes 的 data 列表 → 集摘要列表"""
    result = []
    for e in (items or []):
        desc = e.get("desc", "") or ""
        result.append(
            BangumiEpisodeBrief(
                episode_id=e.get("id"),
                type=e.get("type", 0) or 0,
                name=e.get("name", "") or "",
                name_cn=e.get("name_cn", "") or "",
                sort=e.get("sort", 0) or 0,
                ep=e.get("ep"),
                airdate=e.get("airdate"),
                duration=e.get("duration"),
                desc=desc,
                desc_length=len(desc),
            )
        )
    return result
