"""Bangumi v0 API 调用封装

匿名 + User-Agent 即可（已实测 200），P1 不需要 token。无 tmdbsimple 等价库，
自实现 httpx 调用，结构与 tmdb.py 对称（调用层），原始 dict 压缩交给 summarize。

与 TMDB overview 不同：bangumi summary 是填充源的核心价值，故模型完整保留 summary，
下游 --with-bangumi 再决定如何压缩不进上下文。
"""

from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from melodyi_filebot import summarize
from melodyi_filebot.models import BangumiEpisodeBrief, BangumiSubjectSummary

logger = logging.getLogger(__name__)

BASE_URL = "https://api.bgm.tv"
USER_AGENT = "melodyi-filebot/dev (https://github.com/melodyi)"
DEFAULT_TIMEOUT = 15.0
PAGE_LIMIT = 50  # /v0/episodes 每页上限
MAX_EPISODES = 2000  # 翻页累计上限，防止异常条目无限翻页

_client: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    """懒构造模块级 httpx.Client（测试可直接覆盖 bangumi._client 注入 fake）"""
    global _client
    if _client is None:
        _client = httpx.Client(
            base_url=BASE_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT,
        )
    return _client


def _request(method: str, path: str, **kwargs) -> dict:
    """统一请求入口：日志 + 404 友好提示 + 非 2xx raise

    Args:
        method: HTTP 方法
        path: 相对 BASE_URL 的路径
        **kwargs: 透传给 httpx.Client.request（json/params 等）

    Returns:
        响应 JSON dict

    Raises:
        RuntimeError: 404（资源不存在）
        httpx.HTTPStatusError: 其它非 2xx
    """
    client = _get_client()
    logger.info("Bangumi 请求: %s %s params=%s", method, path, kwargs.get("params"))
    resp = client.request(method, path, **kwargs)
    if resp.status_code == 404:
        logger.warning("Bangumi 资源不存在: %s %s", method, path)
        raise RuntimeError(f"Bangumi 未找到资源: {method} {path}")
    resp.raise_for_status()
    data = resp.json()
    logger.info("Bangumi 响应: %s %s 状态=%d", method, path, resp.status_code)
    return data


def search_anime(keyword: str) -> List[BangumiSubjectSummary]:
    """搜索动画条目（filter.type=[2] 限定动画）

    Bangumi v0 搜索端点硬性返回 ≤10 条/页（实测 perpage 参数被忽略），
    不支持自定义每页数；如需更多结果，未来再加翻页（YAGNI，暂不做）。

    Args:
        keyword: 搜索关键字

    Returns:
        条目摘要列表（≤10 条）
    """
    body = {
        "keyword": keyword,
        "filter": {"type": [2]},
    }
    logger.info("Bangumi 搜索动画开始: keyword=%r", keyword)
    data = _request("POST", "/v0/search/subjects", json=body)
    items = data.get("data", []) or []
    cands = summarize.bangumi_subjects_from_search(items)
    logger.info("Bangumi 搜索动画完成: 命中 %d 条", len(cands))
    return cands


def get_subject(subject_id: int) -> BangumiSubjectSummary:
    """获取条目详情

    Args:
        subject_id: Bangumi 条目 ID

    Returns:
        条目摘要
    """
    logger.info("获取 Bangumi 条目开始: id=%s", subject_id)
    data = _request("GET", f"/v0/subjects/{subject_id}")
    s = summarize.bangumi_subject_from_detail(data)
    logger.info("获取 Bangumi 条目完成: id=%s name_cn=%s eps=%d", subject_id, s.name_cn, s.eps)
    return s


def get_subject_episodes(
    subject_id: int, ep_type: int = 0
) -> List[BangumiEpisodeBrief]:
    """获取条目集列表（自动翻页）

    Args:
        subject_id: Bangumi 条目 ID
        ep_type: 集类型（0=本篇 1=特别篇 2=OP 3=ED 4=预告 5=MAD 6=其他 7=非正片）

    Returns:
        集摘要列表（累计到 total 或达 MAX_EPISODES 上限）
    """
    logger.info("获取 Bangumi 集列表开始: id=%s type=%s", subject_id, ep_type)
    collected: list = []
    offset = 0
    total = None
    while True:
        params = {
            "subject_id": subject_id,
            "type": ep_type,
            "limit": PAGE_LIMIT,
            "offset": offset,
        }
        data = _request("GET", "/v0/episodes", params=params)
        total = data.get("total", 0) or 0
        page = data.get("data", []) or []
        collected.extend(page)
        # 终止条件：已累计到 total / 本页空 / 触达上限
        if not page or len(collected) >= total or len(collected) >= MAX_EPISODES:
            break
        offset += len(page)
    if total is not None and len(collected) >= MAX_EPISODES and total > MAX_EPISODES:
        logger.warning(
            "Bangumi 集列表触达上限 %d（total=%d），已截断", MAX_EPISODES, total
        )
    briefs = summarize.bangumi_episodes_from_raw(collected)
    logger.info(
        "获取 Bangumi 集列表完成: id=%s type=%s 集数=%d", subject_id, ep_type, len(briefs)
    )
    return briefs
