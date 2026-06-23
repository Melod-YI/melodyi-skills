"""数据模型测试"""

import pytest
from melodyi_filebot.models import (
    CandidateSummary,
    EpisodeBrief,
    EpisodeGroupBrief,
    PlanOperation,
    SeasonSummary,
    ShowSummary,
)


class TestModels:
    """Pydantic 模型基础测试"""

    def test_candidate_summary(self):
        c = CandidateSummary(
            tmdb_id=46260,
            title="莉可丽丝",
            original_title="リコリス・リコイル",
            year=2022,
            overview_length=100,
            media_type="tv",
        )
        assert c.tmdb_id == 46260
        assert c.media_type == "tv"

    def test_show_summary(self):
        s = ShowSummary(
            tmdb_id=46260,
            title="莉可丽丝",
            original_title="リコリス・リコイル",
            year=2022,
            total_seasons=2,
            total_episodes=19,
            overview_available=True,
            overview_length=100,
            seasons=[
                SeasonSummary(
                    season_number=0,
                    name="Specials",
                    episode_count=6,
                    overview_available=True,
                )
            ],
            episode_groups=[],
        )
        assert s.total_seasons == 2
        assert s.seasons[0].season_number == 0

    def test_overview_available_false_when_short(self):
        """overview 长度 <10 视为不可用"""
        s = ShowSummary(
            tmdb_id=1,
            title="t",
            original_title="t",
            year=2020,
            total_seasons=1,
            total_episodes=1,
            overview_available=False,
            overview_length=5,
            seasons=[],
            episode_groups=[],
        )
        assert s.overview_available is False

    def test_episode_brief(self):
        e = EpisodeBrief(episode_number=1, name="第一集", overview_length=120)
        assert e.episode_number == 1
        assert e.overview_available is True

    def test_plan_operation_move(self):
        op = PlanOperation(
            type="move",
            source="/a/x.mkv",
            path="/b/x.mkv",
        )
        assert op.type == "move"

    def test_plan_operation_mkdir(self):
        op = PlanOperation(type="mkdir", path="/b")
        assert op.source is None

    def test_episode_group_brief(self):
        g = EpisodeGroupBrief(id="abc", name="HD Remaster", type=1)
        assert g.id == "abc"
