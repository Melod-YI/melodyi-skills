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


class TestEpisodeGroupModels:
    """剧集组相关模型测试"""

    def test_brief_type_name_mapped(self):
        """type=6 应映射为「制作顺序」"""
        g = EpisodeGroupBrief(id="abc", name="All Episodes + OVAs", type=6, episode_count=19)
        assert g.type_name == "制作顺序"
        assert g.episode_count == 19

    def test_brief_type_name_known_values(self):
        assert EpisodeGroupBrief(id="x", name="x", type=1).type_name == "首播顺序"
        assert EpisodeGroupBrief(id="x", name="x", type=3).type_name == "DVD"
        assert EpisodeGroupBrief(id="x", name="x", type=7).type_name == "TV"

    def test_brief_type_name_unknown_falls_back_to_number(self):
        g = EpisodeGroupBrief(id="x", name="x", type=99)
        assert g.type_name == "99"

    def test_episode_brief_season_number_optional(self):
        """剧集组内集带季号；普通季集为 None"""
        e = EpisodeBrief(episode_number=1, name="x", season_number=2)
        assert e.season_number == 2
        e2 = EpisodeBrief(episode_number=1, name="x")
        assert e2.season_number is None

    def test_episode_group_detail(self):
        from melodyi_filebot.models import EpisodeGroupDetail, EpisodeGroupSub
        d = EpisodeGroupDetail(
            id="g1", name="All", type=6, episode_count=19, group_count=2,
            sub_groups=[EpisodeGroupSub(name="正片", episodes=[
                EpisodeBrief(episode_number=1, name="e1", season_number=1, overview_length=50)
            ])],
        )
        assert d.type_name == "制作顺序"
        assert d.group_count == 2
        assert d.sub_groups[0].name == "正片"
        assert d.sub_groups[0].episodes[0].season_number == 1


class TestPlanModels:
    """P2 Plan 结构测试"""

    def test_file_target(self):
        from melodyi_filebot.models import FileTarget
        t = FileTarget(season=1, episode=5, episode_end=None, part=None)
        assert t.season == 1 and t.episode == 5

    def test_nfo_source_tmdb(self):
        from melodyi_filebot.models import NfoSource
        s = NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1)
        assert s.provider == "tmdb" and s.tmdb_id == 154494

    def test_nfo_source_bangumi(self):
        from melodyi_filebot.models import NfoSource
        s = NfoSource(provider="bangumi", bangumi_subject_id=364450, bangumi_episode_id=1111258)
        assert s.bangumi_subject_id == 364450

    def test_episode_entry_three_blocks(self):
        """集三块：file / target / source"""
        from melodyi_filebot.models import EpisodeEntry, FileTarget, NfoSource
        e = EpisodeEntry(
            file="D:/src/ep01.mkv",
            target=FileTarget(season=1, episode=1),
            source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1),
        )
        assert e.file.endswith("ep01.mkv")
        assert e.target.season == 1
        assert e.source.tmdb_id == 154494

    def test_plan_structure(self):
        from melodyi_filebot.models import Plan, ShowRef, SeasonEntry, EpisodeEntry, FileTarget, NfoSource
        p = Plan(
            show=ShowRef(tmdb_id=154494, bangumi_subject_id=364450,
                         title="莉可丽丝", year=2022, language="zh-CN"),
            seasons=[SeasonEntry(season=1, source=NfoSource(provider="tmdb", tmdb_id=154494, season=1))],
            episodes=[EpisodeEntry(
                file="D:/src/ep01.mkv",
                target=FileTarget(season=1, episode=1),
                source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1),
            )],
            warnings=[],
        )
        assert p.show.tmdb_id == 154494
        assert len(p.seasons) == 1
        assert p.episodes[0].source.tmdb_id == 154494

    def test_nfo_operation(self):
        from melodyi_filebot.models import NfoOperation, NfoSource
        op = NfoOperation(type="episode", path=".../S01E01.nfo", season=1, episode=1,
                          source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1))
        assert op.type == "episode"

    def test_build_plan_result_has_nfo_operations(self):
        from melodyi_filebot.models import BuildPlanResult, NfoOperation, NfoSource
        r = BuildPlanResult(operations=[], nfo_operations=[
            NfoOperation(type="tvshow", path=".../tvshow.nfo",
                         source=NfoSource(provider="tmdb", tmdb_id=154494))
        ])
        assert len(r.nfo_operations) == 1
        # 默认空
        assert BuildPlanResult(operations=[]).nfo_operations == []
