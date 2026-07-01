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
