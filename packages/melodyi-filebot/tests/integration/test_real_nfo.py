"""真实 NFO 生成集成测试（调真实 TMDB/bangumi）

默认 skip，需 `pytest --run-integration` 启用，且需配置 TMDB_API_KEY
（环境变量或 ~/.melodyi-skills/melodyi-filebot/config.yaml）。

兼容性设计（同 test_real_tmdb.py / test_real_bangumi.py）：
- 调用密度高，每次 API 调用前后加间隔，防止限流。
- 断言只验证「NFO XML 关键结构 + 字段存在」，对结果数值/多余字段容忍。
- 莉可丽丝为 2022 年已完结番剧，tmdb_id/bangumi_id 长期稳定。
"""

from __future__ import annotations

import os
import time

import pytest

from melodyi_filebot import bangumi, config, nfo, tmdb
from melodyi_filebot.models import NfoOperation, NfoSource

pytestmark = [pytest.mark.integration]

# 调用间隔（秒）。可通过环境变量 INTEGRATION_CALL_DELAY 调整。
CALL_DELAY = float(os.environ.get("INTEGRATION_CALL_DELAY", "1.5"))

# 莉可丽丝（已完结，锚点稳定；与 test_nfo.py / test_planner.py 一致）
LYCORIS_TMDB = 154494
LYCORIS_BG = 364450


def _has_api_key() -> bool:
    return bool(config.load_tmdb_api_key())


# 无 key 时整体跳过，避免 --run-integration 但未配 key 时报一堆 error
pytestmark_with_key = pytest.mark.skipif(
    not _has_api_key(), reason="未配置 TMDB_API_KEY，跳过真实 API 集成测试"
)
pytestmark.append(pytestmark_with_key)


@pytest.fixture(autouse=True)
def _pace_calls():
    """每个测试前后各等待，降低调用密度（真实 TMDB + bangumi 双源）"""
    time.sleep(CALL_DELAY)
    yield
    time.sleep(CALL_DELAY)


@pytest.fixture(autouse=True)
def _reset_bangumi_client():
    """每个测试前后重置模块级 client（确保用真实 httpx.Client）"""
    bangumi._client = None
    yield
    bangumi._client = None


class TestRealNfo:
    def test_tvshow_nfo_from_real_tmdb(self):
        """真实 TMDB 全量详情 → tvshow NFO XML（含 lockdata/uniqueid/字段）"""
        show = tmdb.get_show_detail_full(LYCORIS_TMDB, language="zh-CN")
        bg = bangumi.get_subject(LYCORIS_BG)
        xml = nfo.build_tvshow_xml(
            show, nfo._bg_to_dict(bg) if hasattr(bg, "__dict__") else bg,
            "zh-CN", dateadded="2026-07-01 12:00:00",
        )
        assert "<tvshow>" in xml and "</tvshow>" in xml
        assert f"<tmdbid>{LYCORIS_TMDB}</tmdbid>" in xml
        assert "<lockdata>true</lockdata>" in xml
        assert '<uniqueid type="tmdbid" default="true">' in xml
        assert "<plot>" in xml  # 有简介

    def test_generate_tvshow_nfo_dry_run(self):
        """generate_nfo dry-run：真实拉取但不写盘"""
        op = NfoOperation(
            type="tvshow", path="/tmp/test_tvshow.nfo",
            source=NfoSource(provider="tmdb", tmdb_id=LYCORIS_TMDB,
                             bangumi_subject_id=LYCORIS_BG),
        )
        path = nfo.generate_nfo(op, language="zh-CN", dry_run=True,
                                dateadded="2026-07-01 12:00:00")
        assert path == "/tmp/test_tvshow.nfo"

    def test_episode_nfo_from_real_season(self):
        """真实季详情 → episode NFO XML（含 streamdetails 占位检查）"""
        season = tmdb.get_season_detail(LYCORIS_TMDB, 1, language="zh-CN")
        ep = next(e for e in season.get("episodes", []) if e.get("episode_number") == 1)
        xml = nfo.build_episode_xml(
            ep, bangumi_data=None, show_title="莉可丽丝",
            target_season=1, target_episode=1, stream_details=None,
            tmdb_id=LYCORIS_TMDB, dateadded="2026-07-01 12:00:00",
        )
        assert "<episodedetails>" in xml
        assert "<season>1</season>" in xml
        assert "<episode>1</episode>" in xml
        assert "<showtitle>莉可丽丝</showtitle>" in xml
