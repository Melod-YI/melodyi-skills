"""NFO 生成：按来源拉取字段 → Jellyfin NFO XML

分两层：
- build_*_xml(data, bangumi_data): 纯数据→XML（易测，mock 数据）
- generate_nfo(op): 按 NfoOperation 来源拉取 + 调 build + 写文件（Task 9）
"""

from __future__ import annotations

import logging
from typing import Optional
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

TMDB_IMG_BASE = "https://image.tmdb.org/t/p/original"
OVERVIEW_MIN_LENGTH = 10


def _img_url(path: Optional[str]) -> Optional[str]:
    return f"{TMDB_IMG_BASE}{path}" if path else None


def _fill_overview(tmdb_overview: Optional[str], bangumi_text: Optional[str]) -> str:
    """TMDB overview 空/<10 用 bangumi 同义字段补"""
    ov = (tmdb_overview or "").strip()
    if len(ov) >= OVERVIEW_MIN_LENGTH:
        return ov
    bg = (bangumi_text or "").strip()
    return bg if len(bg) >= OVERVIEW_MIN_LENGTH else ov


def _el(tag: str, text) -> str:
    """生成 <tag>escaped text</tag>，text 为 None/空则返回空元素 <tag/>"""
    if text is None or text == "":
        return f"<{tag} />"
    return f"<{tag}>{escape(str(text))}</{tag}>"


def _bg_duration_to_minutes(duration: Optional[str]) -> Optional[int]:
    """bangumi duration '00:24:00' → 分钟数（24）；解析失败返回 None"""
    if not duration:
        return None
    try:
        parts = duration.split(":")
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return h * 60 + m + (1 if s >= 30 else 0)  # 秒数四舍五入
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(parts[0])
    except (ValueError, AttributeError):
        return None


def build_tvshow_xml(show: dict, bangumi_data: Optional[dict], language: str,
                     dateadded: Optional[str] = None) -> str:
    """TMDB show dict + 可选 bangumi dict → tvshow.nfo XML"""
    bg = bangumi_data or {}
    plot = _fill_overview(show.get("overview"), bg.get("summary"))
    title = show.get("name") or bg.get("name_cn") or ""
    original = show.get("original_name") or bg.get("name") or ""
    ext = show.get("external_ids") or {}
    parts = ['<?xml version="1.0" encoding="utf-8" standalone="yes"?>', "<tvshow>"]
    parts.append(_el("plot", plot))
    parts.append(_el("outline", plot))
    parts.append("<lockdata>true</lockdata>")
    if dateadded:
        parts.append(_el("dateadded", dateadded))
    parts.append(_el("title", title))
    parts.append(_el("originaltitle", original))
    for w in (show.get("created_by") or []):
        parts.append(_el("writer", w.get("name")))
        parts.append(_el("credits", w.get("name")))
    parts.append(_el("rating", show.get("vote_average")))
    parts.append(_el("year", (show.get("first_air_date") or "")[:4] or None))
    parts.append(_el("premiered", show.get("first_air_date")))
    parts.append(_el("enddate", show.get("last_air_date")))
    parts.append(_el("releasedate", show.get("first_air_date")))
    ert = show.get("episode_run_time")
    runtime = ert[0] if isinstance(ert, list) and ert else ert
    parts.append(_el("runtime", runtime))
    for g in (show.get("genres") or []):
        parts.append(_el("genre", g.get("name")))
    for k in ((show.get("keywords") or {}).get("results") or []):
        parts.append(_el("tag", k.get("name")))
    for n in (show.get("networks") or []):
        parts.append(_el("studio", n.get("name")))
    cr = (show.get("content_ratings") or {}).get("results") or []
    if cr:
        parts.append(_el("mpaa", cr[0].get("rating")))
    parts.append(_el("imdb_id", ext.get("imdb_id")))
    parts.append(_el("tmdbid", show.get("id")))
    parts.append(_el("tvdbid", ext.get("tvdb_id")))
    # uniqueid：TMDB 为默认标识，bangumi id 附加（type=bgm）
    if show.get("id") is not None:
        parts.append(f'<uniqueid type="tmdbid" default="true">{show.get("id")}</uniqueid>')
    bg_id = bg.get("id")
    if bg_id:
        parts.append(f'<uniqueid type="bgm">{bg_id}</uniqueid>')
    poster = _img_url(show.get("poster_path"))
    fanart = _img_url(show.get("backdrop_path"))
    if poster or fanart:
        parts.append("<art>")
        if poster:
            parts.append(_el("poster", poster))
        if fanart:
            parts.append(_el("fanart", fanart))
        parts.append("</art>")
    for a in ((show.get("aggregate_credits") or {}).get("cast") or []):
        roles = a.get("roles") or [{}]
        char = roles[0].get("character") if roles else None
        parts.append("<actor>")
        parts.append(_el("name", a.get("name")))
        parts.append(_el("role", char))
        parts.append(_el("type", "Actor"))
        parts.append(_el("sortorder", a.get("order")))
        parts.append(_el("thumb", _img_url(a.get("profile_path"))))
        parts.append("</actor>")
    parts.append(_el("season", -1))
    parts.append(_el("episode", -1))
    parts.append(_el("status", "Continuing" if show.get("in_production") else "Ended"))
    parts.append("</tvshow>")
    return "\n".join(parts)


def build_season_xml(season: dict, bangumi_data: Optional[dict],
                     show_actors: Optional[list], season_number: int,
                     tmdb_id: Optional[int] = None,
                     bangumi_subject_id: Optional[int] = None,
                     dateadded: Optional[str] = None) -> str:
    """季详情 + 可选 bangumi subject → season.nfo XML"""
    bg = bangumi_data or {}
    plot = _fill_overview(season.get("overview"), bg.get("summary"))
    title = season.get("name") or bg.get("name_cn") or f"第 {season_number} 季"
    parts = ['<?xml version="1.0" encoding="utf-8" standalone="yes"?>', "<season>"]
    parts.append(_el("plot", plot))
    parts.append(_el("outline", plot))
    parts.append("<lockdata>true</lockdata>")
    if dateadded:
        parts.append(_el("dateadded", dateadded))
    parts.append(_el("title", title))
    air = season.get("air_date") or bg.get("date")
    parts.append(_el("year", (air or "")[:4] or None))
    parts.append(_el("premiered", air))
    parts.append(_el("releasedate", air))
    poster = _img_url(season.get("poster_path"))
    if poster:
        parts.append("<art>")
        parts.append(_el("poster", poster))
        parts.append("</art>")
    # uniqueid：TMDB 季标识为默认，bangumi subject id 附加（type=bgm）
    if tmdb_id is not None:
        parts.append(f'<uniqueid type="tmdbid" default="true">{tmdb_id}-{season_number}</uniqueid>')
    if bangumi_subject_id is not None:
        parts.append(f'<uniqueid type="bgm">{bangumi_subject_id}</uniqueid>')
    for a in (show_actors or []):
        roles = a.get("roles") or [{}]
        char = roles[0].get("character") if roles else a.get("character")
        parts.append("<actor>")
        parts.append(_el("name", a.get("name")))
        parts.append(_el("role", char))
        parts.append(_el("type", "Actor"))
        parts.append(_el("sortorder", a.get("order")))
        parts.append(_el("thumb", _img_url(a.get("profile_path"))))
        parts.append("</actor>")
    parts.append(_el("seasonnumber", season_number))
    parts.append("</season>")
    return "\n".join(parts)


def _streamdetails_xml(sd: dict) -> str:
    v = sd.get("video") or {}
    a = sd.get("audio") or {}
    parts = ["<fileinfo><streamdetails>"]
    if v:
        parts.append("<video>")
        for tag in ["codec", "width", "height", "aspect", "framerate", "duration", "duration_seconds"]:
            if v.get(tag) is not None:
                # duration_seconds → durationinseconds 标签名
                el_tag = "durationinseconds" if tag == "duration_seconds" else tag
                parts.append(_el(el_tag, v.get(tag)))
        parts.append("</video>")
    if a:
        parts.append("<audio>")
        for tag in ["codec", "channels", "samplingrate"]:
            if a.get(tag) is not None:
                parts.append(_el(tag, a.get(tag)))
        parts.append("</audio>")
    parts.append("</streamdetails></fileinfo>")
    return "\n".join(parts)


def build_episode_xml(ep: dict, bangumi_data: Optional[dict], show_title: str,
                      target_season: int, target_episode: int,
                      stream_details: Optional[dict],
                      tmdb_id: Optional[int] = None,
                      dateadded: Optional[str] = None) -> str:
    """集详情 + 可选 bangumi + 展示身份 + ffprobe → episodedetails XML"""
    bg = bangumi_data or {}
    plot = _fill_overview(ep.get("overview"), bg.get("desc"))
    title = ep.get("name") or bg.get("name_cn") or ""
    src_season = ep.get("season_number")
    src_episode = ep.get("episode_number")
    parts = ['<?xml version="1.0" encoding="utf-8" standalone="yes"?>', "<episodedetails>"]
    parts.append(_el("plot", plot))
    parts.append("<lockdata>true</lockdata>")
    if dateadded:
        parts.append(_el("dateadded", dateadded))
    parts.append(_el("title", title))
    for c in (ep.get("crew") or []):
        if c.get("job") == "Director":
            parts.append(_el("director", c.get("name")))
            parts.append(_el("credits", c.get("name")))
        elif c.get("job") == "Writer":
            parts.append(_el("writer", c.get("name")))
            parts.append(_el("credits", c.get("name")))
    parts.append(_el("rating", ep.get("vote_average")))
    air = ep.get("air_date") or bg.get("airdate")
    parts.append(_el("year", (air or "")[:4] or None))
    runtime = ep.get("runtime")
    if runtime is None:
        runtime = _bg_duration_to_minutes(bg.get("duration"))
    parts.append(_el("runtime", runtime))
    parts.append(_el("showtitle", show_title))
    parts.append(_el("episode", target_episode))
    parts.append(_el("season", target_season))
    parts.append(_el("aired", air))
    # 特别篇重排：target≠source 时写 displayseason/displayepisode
    if src_season is not None and src_episode is not None \
            and (src_season != target_season or src_episode != target_episode):
        parts.append(_el("displayseason", src_season))
        parts.append(_el("displayepisode", src_episode))
    still = _img_url(ep.get("still_path"))
    if still:
        parts.append("<art>")
        parts.append(_el("poster", still))
        parts.append("</art>")
    # uniqueid
    if tmdb_id is not None and src_season is not None and src_episode is not None:
        parts.append(f'<uniqueid type="tmdbid" default="true">{tmdb_id}-{src_season}-{src_episode}</uniqueid>')
    bg_ep_id = bg.get("id")
    if bg_ep_id:
        parts.append(f'<uniqueid type="bgm">{bg_ep_id}</uniqueid>')
    # guest_stars：character 顶层（与 aggregate_credits 的 roles 嵌套不同）
    for a in (ep.get("guest_stars") or []):
        parts.append("<actor>")
        parts.append(_el("name", a.get("name")))
        parts.append(_el("role", a.get("character")))
        parts.append(_el("type", "GuestStar"))
        parts.append(_el("sortorder", a.get("order")))
        parts.append(_el("thumb", _img_url(a.get("profile_path"))))
        parts.append("</actor>")
    if stream_details:
        parts.append(_streamdetails_xml(stream_details))
    parts.append("</episodedetails>")
    return "\n".join(parts)
