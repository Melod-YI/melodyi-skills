"""真实 Bangumi API 集成测试

默认 skip，需 `pytest --run-integration` 启用。Bangumi 匿名 + UA 即可，无需 key。

兼容性设计（同 test_real_tmdb.py）：
- 调用密度高，每次 API 调用前后加间隔，防止限流。
- 断言只验证「已知条目存在 + 关键字段正确」，对结果数量/顺序/多余条目容忍。
- 莉可丽丝为 2022 年已完结番剧，eps=13 长期稳定。
"""

from __future__ import annotations

import os
import time

import pytest

from melodyi_filebot import bangumi

pytestmark = [pytest.mark.integration]

# 调用间隔（秒）。可通过环境变量 INTEGRATION_CALL_DELAY 调整。
CALL_DELAY = float(os.environ.get("INTEGRATION_CALL_DELAY", "1.5"))

# 莉可丽丝（已完结，锚点稳定）
LYCORIS_ID = 364450
LYCORIS_EPS = 13


@pytest.fixture(autouse=True)
def _reset_and_pace():
    """每个测试前后重置模块级 client（确保用真实 httpx.Client）并等待防限流"""
    bangumi._client = None
    time.sleep(CALL_DELAY)
    yield
    bangumi._client = None
    time.sleep(CALL_DELAY)


class TestSearchAnime:
    """真实搜索测试（容忍多余条目）"""

    def test_search_finds_lycoris(self):
        cands = bangumi.search_anime("莉可丽丝")
        entry = next((c for c in cands if c.subject_id == LYCORIS_ID), None)
        assert entry is not None, f"未找到 subject_id={LYCORIS_ID}"
        assert entry.name_cn == "莉可丽丝"
        assert entry.type == 2  # 动画
        assert entry.eps == LYCORIS_EPS


class TestGetSubject:
    """真实条目详情测试"""

    def test_subject_fields(self):
        s = bangumi.get_subject(LYCORIS_ID)
        assert s.subject_id == LYCORIS_ID
        assert s.name_cn == "莉可丽丝"
        assert s.eps == LYCORIS_EPS
        assert s.date == "2022-07-02"
        assert s.summary_length > 0


class TestGetSubjectEpisodes:
    """真实集列表测试"""

    def test_episodes_structure(self):
        eps = bangumi.get_subject_episodes(LYCORIS_ID, ep_type=0)
        assert len(eps) >= LYCORIS_EPS
        # 含第 1 集，且放送日期正确
        e1 = next((e for e in eps if e.ep == 1), None)
        assert e1 is not None, "应包含第 1 集"
        assert e1.airdate == "2022-07-02"
        assert e1.duration  # 时长字段存在

    def test_404_raises(self):
        with pytest.raises(RuntimeError, match="Bangumi 未找到资源"):
            bangumi.get_subject(999999999)
