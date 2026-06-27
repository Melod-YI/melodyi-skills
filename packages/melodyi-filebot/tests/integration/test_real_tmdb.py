"""真实 TMDB API 集成测试

默认 skip，需 `pytest --run-integration` 启用，且需配置 TMDB_API_KEY
（环境变量或 ~/.melodyi-skills/melodyi-filebot/config.yaml）。

兼容性设计：
- 调用密度高，每次 API 调用前后加间隔，防止限流。
- 断言只验证「已知条目存在 + 关键字段正确」，对结果数量/顺序/多余条目容忍。
- TMDB 结果可能新增条目，故一律用「存在性」而非「精确计数」断言。
"""

from __future__ import annotations

import os
import time
from typing import List, Optional

import pytest

from melodyi_filebot import config, tmdb
from melodyi_filebot.models import CandidateSummary

pytestmark = [pytest.mark.integration]

# 调用间隔（秒）。可通过环境变量 INTEGRATION_CALL_DELAY 调整。
CALL_DELAY = float(os.environ.get("INTEGRATION_CALL_DELAY", "1.5"))

# 已知稳定锚点（刀剑神域系列，tmdb_id 长期稳定）
SAO_TV_ID = 45782
SAO_MOVIE_ID = 413594  # 刀剑神域：序列之争


def _has_api_key() -> bool:
    return bool(config.load_tmdb_api_key())


# 无 key 时整体跳过，避免 --run-integration 但未配 key 时报一堆 error
pytestmark_with_key = pytest.mark.skipif(
    not _has_api_key(), reason="未配置 TMDB_API_KEY，跳过真实 API 集成测试"
)
pytestmark.append(pytestmark_with_key)


@pytest.fixture(autouse=True)
def _pace_calls():
    """每个测试前后各等待，降低调用密度"""
    time.sleep(CALL_DELAY)
    yield
    time.sleep(CALL_DELAY)


def _find_by_id(cands: List[CandidateSummary], tmdb_id: int) -> Optional[CandidateSummary]:
    return next((c for c in cands if c.tmdb_id == tmdb_id), None)


class TestSearch:
    """真实搜索测试（容忍多余条目）"""

    def test_search_tv_finds_known_entry(self):
        """tv 搜索应包含刀剑神域主剧，字段正确"""
        cands = tmdb.search("刀剑神域", media_type="tv", language="zh-CN")
        entry = _find_by_id(cands, SAO_TV_ID)
        assert entry is not None, f"未找到 tmdb_id={SAO_TV_ID}"
        assert entry.media_type == "tv"
        assert entry.title, "title 不应为空"
        assert entry.year == 2012

    def test_search_multi_distinguishes_types(self):
        """multi 搜索时 tv/movie 条目各自按正确字段解析、media_type 反映真实类型

        回归用例：修复前 tv 条目走 movie 字段分支导致 title/year 为空、
        media_type 错误存为 'multi'。
        """
        cands = tmdb.search("刀剑神域", media_type="multi", language="zh-CN")
        tv = _find_by_id(cands, SAO_TV_ID)
        assert tv is not None, f"未找到 tv 条目 tmdb_id={SAO_TV_ID}"
        assert tv.media_type == "tv"
        assert tv.title, "tv 条目 title 不应为空"
        assert tv.year == 2012

        movie = _find_by_id(cands, SAO_MOVIE_ID)
        assert movie is not None, f"未找到 movie 条目 tmdb_id={SAO_MOVIE_ID}"
        assert movie.media_type == "movie"
        assert movie.title, "movie 条目 title 不应为空"


class TestFetchSummary:
    """真实详情摘要测试"""

    def test_show_summary_structure(self):
        """剧摘要结构完整"""
        s = tmdb.get_show_summary(SAO_TV_ID, language="zh-CN")
        assert s.tmdb_id == SAO_TV_ID
        assert s.title, "title 不应为空"
        assert s.total_seasons >= 1
        assert s.total_episodes > 0
        # 第一季应存在
        assert any(season.season_number == 1 for season in s.seasons), "应包含第一季"

    def test_season_episodes_non_empty(self):
        """第一季集列表非空，且含第 1 集"""
        eps = tmdb.get_season_episodes(SAO_TV_ID, 1, language="zh-CN")
        assert len(eps) > 0
        assert any(e.episode_number == 1 for e in eps), "应包含第 1 集"
