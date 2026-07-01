"""planner 测试"""

import pytest

from melodyi_filebot.planner import ParsedFile, parse_filename


class TestParseFilename:
    """文件名 S/E 解析测试"""

    def test_standard_sxxexx(self):
        p = parse_filename("Gundam.Build.Fighters.2013.S01E01.2160p.WEB-DL.mp4")
        assert p.season == 1
        assert p.episode == 1
        assert p.episode_end is None
        assert p.part is None
        assert p.ext == ".mp4"

    def test_chinese_title_sxxexx(self):
        p = parse_filename("莉可丽丝 S01E01.mkv")
        assert p.season == 1
        assert p.episode == 1

    def test_multi_episode_range(self):
        p = parse_filename("Series A S01E01-E02.mkv")
        assert p.season == 1
        assert p.episode == 1
        assert p.episode_end == 2

    def test_part_split(self):
        p = parse_filename("Series A S01E01-part-1.mkv")
        assert p.season == 1
        assert p.episode == 1
        assert p.part == 1

    def test_part_split_dot(self):
        p = parse_filename("Series A S01E01.part2.mkv")
        assert p.season == 1
        assert p.episode == 1
        assert p.part == 2

    def test_bracket_episode_number(self):
        """方括号单集编号 [10]"""
        p = parse_filename("[VCB-Studio] Amagami SS+ Plus [10][Ma10p_1080p].mkv")
        assert p.season is None  # 无季信息
        assert p.episode == 10

    def test_returns_none_for_unknown(self):
        p = parse_filename("random video file.mp4")
        assert p.season is None
        assert p.episode is None

    def test_stem_extraction(self):
        p = parse_filename("Show S01E01.mkv")
        assert "Show" in p.stem


class TestDraftPlan:
    """draft_plan: folder→target 输入 → Plan（含来源解析）"""

    def _folder_spec(self, tmp_path):
        (tmp_path / "E01.mkv").write_bytes(b"x")
        (tmp_path / "E02.mkv").write_bytes(b"x")
        return {
            "show": {"tmdb_id": 154494, "bangumi_subject_id": 364450},
            "folders": [{"path": str(tmp_path), "target": {"kind": "season", "season": 1}}],
        }

    def _fake_show(self):
        from melodyi_filebot.models import ShowSummary, SeasonSummary
        return ShowSummary(tmdb_id=154494, title="莉可丽丝", original_title="リコリス",
                           year=2022, total_seasons=1, total_episodes=2,
                           seasons=[SeasonSummary(season_number=1, name="S1", episode_count=2)])

    def test_season_target_resolves_episode_sources(self, tmp_path):
        from melodyi_filebot import planner
        spec = self._folder_spec(tmp_path)
        def fake_season_eps(tid, sn, language="zh-CN"):
            from melodyi_filebot.models import EpisodeBrief
            return [EpisodeBrief(episode_number=1, name="e1", overview_length=50),
                    EpisodeBrief(episode_number=2, name="e2", overview_length=50)]
        def fake_show(tid, language="zh-CN"):
            return self._fake_show()
        def fake_bg_eps(sid, ep_type=0):
            from melodyi_filebot.models import BangumiEpisodeBrief
            return [BangumiEpisodeBrief(episode_id=111, name="e1", name_cn="e1", sort=1, ep=1, desc="x"*20),
                    BangumiEpisodeBrief(episode_id=222, name="e2", name_cn="e2", sort=2, ep=2, desc="x"*20)]
        plan = planner.draft_plan(
            spec, language="zh-CN",
            fetch_show_summary=fake_show, fetch_season_episodes=fake_season_eps,
            fetch_bangumi_episodes=fake_bg_eps,
        )
        assert plan.show.tmdb_id == 154494
        assert plan.show.bangumi_subject_id == 364450
        assert len(plan.episodes) == 2
        e1 = plan.episodes[0]
        assert e1.source.tmdb_id == 154494 and e1.source.season == 1 and e1.source.episode == 1
        assert e1.source.bangumi_subject_id == 364450 and e1.source.bangumi_episode_id == 111
        assert e1.target.season == 1 and e1.target.episode == 1
        assert len(plan.seasons) == 1 and plan.seasons[0].season == 1

    def test_unparsable_file_warning(self, tmp_path):
        from melodyi_filebot import planner
        (tmp_path / "no_episode_number.mkv").write_bytes(b"x")
        spec = {"show": {"tmdb_id": 1},
                "folders": [{"path": str(tmp_path), "target": {"kind": "season", "season": 1}}]}
        plan = planner.draft_plan(
            spec, language="zh-CN",
            fetch_show_summary=lambda tid, language="zh-CN": self._fake_show(),
            fetch_season_episodes=lambda tid, sn, language="zh-CN": [],
            fetch_bangumi_episodes=lambda sid, ep_type=0: [],
        )
        assert plan.warnings  # 有告警
        assert plan.episodes == []

    def test_tmdb_missing_season_uses_bangumi(self, tmp_path):
        """物语：TMDB 无该季 → source.tmdb=null，bangumi 为主"""
        from melodyi_filebot import planner
        (tmp_path / "E01.mkv").write_bytes(b"x")
        spec = {"show": {"tmdb_id": 1, "bangumi_subject_id": 999},
                "folders": [{"path": str(tmp_path),
                             "target": {"kind": "season", "season": 3},
                             "bangumi_subject_id": 999}]}
        def fake_show(tid, language="zh-CN"):
            from melodyi_filebot.models import ShowSummary
            return ShowSummary(tmdb_id=1, title="物语", original_title="", year=2009,
                               total_seasons=1, total_episodes=1, seasons=[])
        def fake_season_eps(tid, sn, language="zh-CN"):
            raise RuntimeError("TMDB 无此季")
        def fake_bg_eps(sid, ep_type=0):
            from melodyi_filebot.models import BangumiEpisodeBrief
            return [BangumiEpisodeBrief(episode_id=555, name="e1", name_cn="e1", sort=1, ep=1, desc="x"*20)]
        plan = planner.draft_plan(
            spec, language="zh-CN",
            fetch_show_summary=fake_show, fetch_season_episodes=fake_season_eps,
            fetch_bangumi_episodes=fake_bg_eps,
        )
        s3 = next(s for s in plan.seasons if s.season == 3)
        assert s3.source.provider == "bangumi" and s3.source.bangumi_subject_id == 999
        e = plan.episodes[0]
        assert e.source.tmdb_id is None
        assert e.source.provider == "bangumi"
        assert e.source.bangumi_episode_id == 555
        assert any("TMDB 无第 3 季" in w for w in plan.warnings)

    def test_episode_group_target_placeholder(self, tmp_path):
        """episode_group target：占位 source（provider=tmdb），target.season 默认 1"""
        from melodyi_filebot import planner
        (tmp_path / "E01.mkv").write_bytes(b"x")
        spec = {"show": {"tmdb_id": 154494},
                "folders": [{"path": str(tmp_path),
                             "target": {"kind": "episode_group", "group_id": "abc"}}]}
        plan = planner.draft_plan(
            spec, language="zh-CN",
            fetch_show_summary=lambda tid, language="zh-CN": self._fake_show(),
            fetch_season_episodes=lambda tid, sn, language="zh-CN": [],
            fetch_bangumi_episodes=lambda sid, ep_type=0: [],
        )
        assert len(plan.episodes) == 1
        e = plan.episodes[0]
        assert e.source.provider == "tmdb"
        assert e.source.tmdb_id == 154494
        assert e.target.season == 1  # 默认
        assert e.target.episode == 1

    def test_tmdb_missing_season_no_bangumi_warns(self, tmp_path):
        """TMDB 无季且无 bangumi → 不产生 broken bangumi source，告警"""
        from melodyi_filebot import planner
        (tmp_path / "E01.mkv").write_bytes(b"x")
        spec = {"show": {"tmdb_id": 1},
                "folders": [{"path": str(tmp_path), "target": {"kind": "season", "season": 5}}]}
        def fake_show(tid, language="zh-CN"):
            from melodyi_filebot.models import ShowSummary
            return ShowSummary(tmdb_id=1, title="x", original_title="", year=2020,
                               total_seasons=1, total_episodes=1, seasons=[])
        def fake_season_eps(tid, sn, language="zh-CN"):
            raise RuntimeError("TMDB 无此季")
        plan = planner.draft_plan(
            spec, language="zh-CN",
            fetch_show_summary=fake_show, fetch_season_episodes=fake_season_eps,
            fetch_bangumi_episodes=lambda sid, ep_type=0: [],
        )
        # 不应出现 provider=bangumi 但所有 id 为 None 的 broken source
        assert all(e.source.provider != "bangumi" or e.source.bangumi_subject_id is not None
                   for e in plan.episodes)
        assert any("无 bangumi 来源" in w for w in plan.warnings)


class TestBuildPlanFromPlan:
    """build_plan_from_plan: Plan → BuildPlanResult（move + nfo 操作）"""

    def _plan(self, tmp_path):
        from melodyi_filebot.models import (
            Plan, ShowRef, SeasonEntry, EpisodeEntry, FileTarget, NfoSource)
        src = tmp_path / "src"
        src.mkdir()
        (src / "E01.mkv").write_bytes(b"x")
        return Plan(
            show=ShowRef(tmdb_id=154494, title="莉可丽丝", year=2022, language="zh-CN"),
            seasons=[SeasonEntry(season=1, source=NfoSource(provider="tmdb", tmdb_id=154494, season=1))],
            episodes=[EpisodeEntry(
                file=str(src / "E01.mkv"),
                target=FileTarget(season=1, episode=1),
                source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1))],
            warnings=[],
        )

    def test_generates_move_and_nfo_ops(self, tmp_path):
        from melodyi_filebot import planner
        plan = self._plan(tmp_path)
        dest = tmp_path / "dest"
        result = planner.build_plan_from_plan(plan, str(dest), with_nfo=True)
        # fs 操作：mkdir 剧 + mkdir 季 + move 视频
        assert any(o.type == "mkdir" and "tmdbid-154494" in o.path for o in result.operations)
        assert any(o.type == "mkdir" and "Season 01" in o.path for o in result.operations)
        assert any(o.type == "move" for o in result.operations)
        # nfo 操作：1 tvshow + 1 season + 1 episode
        assert any(o.type == "tvshow" for o in result.nfo_operations)
        assert any(o.type == "season" and o.season == 1 for o in result.nfo_operations)
        ep_nfo = next(o for o in result.nfo_operations if o.type == "episode")
        assert ep_nfo.path.endswith(".nfo")
        assert "S01E01" in ep_nfo.path
        assert ep_nfo.source.tmdb_id == 154494

    def test_no_nfo_ops_when_with_nfo_false(self, tmp_path):
        from melodyi_filebot import planner
        plan = self._plan(tmp_path)
        result = planner.build_plan_from_plan(plan, str(tmp_path / "dest"), with_nfo=False)
        assert result.nfo_operations == []

    def test_episode_nfo_path_matches_video_stem(self, tmp_path):
        """集 nfo 路径 = 视频 move 目标 stem + .nfo"""
        from melodyi_filebot import planner
        plan = self._plan(tmp_path)
        result = planner.build_plan_from_plan(plan, str(tmp_path / "dest"), with_nfo=True)
        move = next(o for o in result.operations if o.type == "move")
        ep_nfo = next(o for o in result.nfo_operations if o.type == "episode")
        assert ep_nfo.path == move.path.rsplit(".", 1)[0] + ".nfo"

    def test_spec_applied_is_plan(self, tmp_path):
        from melodyi_filebot import planner
        plan = self._plan(tmp_path)
        result = planner.build_plan_from_plan(plan, str(tmp_path / "dest"), with_nfo=True)
        assert result.spec_applied == "plan"

    def test_tvshow_nfo_first(self, tmp_path):
        """tvshow nfo 操作应在 nfo_operations 首位"""
        from melodyi_filebot import planner
        plan = self._plan(tmp_path)
        result = planner.build_plan_from_plan(plan, str(tmp_path / "dest"), with_nfo=True)
        assert result.nfo_operations[0].type == "tvshow"

    def test_companion_follows_video_rename(self, tmp_path):
        """伴生字幕随视频改名，语言 token 后缀保留"""
        from melodyi_filebot import planner
        from melodyi_filebot.models import (
            Plan, ShowRef, SeasonEntry, EpisodeEntry, FileTarget, NfoSource)
        src = tmp_path / "src"; src.mkdir()
        video = src / "Show S01E01.mkv"; video.write_bytes(b"x")
        sub = src / "Show S01E01.zh.ass"; sub.write_bytes(b"x")  # 伴生字幕
        plan = Plan(
            show=ShowRef(tmdb_id=1, title="剧", year=2022, language="zh-CN"),
            seasons=[SeasonEntry(season=1, source=NfoSource(provider="tmdb", tmdb_id=1, season=1))],
            episodes=[EpisodeEntry(file=str(video),
                target=FileTarget(season=1, episode=1),
                source=NfoSource(provider="tmdb", tmdb_id=1, season=1, episode=1))],
            warnings=[])
        result = planner.build_plan_from_plan(plan, str(tmp_path / "dest"), with_nfo=False)
        moves = [o for o in result.operations if o.type == "move"]
        # 视频改名
        video_move = next(o for o in moves if o.source.endswith(".mkv"))
        assert "S01E01" in video_move.path and "剧 (2022)" in video_move.path
        # 字幕伴生改名：目标名 = 改名后视频 stem + 原后缀（.zh.ass）
        sub_move = next(o for o in moves if o.source.endswith(".ass"))
        assert sub_move.path.endswith(".zh.ass")
        # 字幕目标与视频同目录、同 stem 前缀
        assert sub_move.path.startswith(str(tmp_path / "dest"))
        sub_stem = sub_move.path.rsplit(".zh.ass", 1)[0]
        assert sub_stem == video_move.path.rsplit(".mkv", 1)[0]

    def test_companion_partial_prefix_excluded(self, tmp_path):
        """stem 后非紧跟 '.' 的文件不算伴生（如 Show S01E01-extra.ass）"""
        from melodyi_filebot import planner
        from melodyi_filebot.models import (
            Plan, ShowRef, SeasonEntry, EpisodeEntry, FileTarget, NfoSource)
        src = tmp_path / "src"; src.mkdir()
        video = src / "Show S01E01.mkv"; video.write_bytes(b"x")
        non_companion = src / "Show S01E01-extra.ass"; non_companion.write_bytes(b"x")  # stem 后是 - 不是 .
        plan = Plan(
            show=ShowRef(tmdb_id=1, title="剧", year=2022, language="zh-CN"),
            seasons=[SeasonEntry(season=1, source=NfoSource(provider="tmdb", tmdb_id=1, season=1))],
            episodes=[EpisodeEntry(file=str(video),
                target=FileTarget(season=1, episode=1),
                source=NfoSource(provider="tmdb", tmdb_id=1, season=1, episode=1))],
            warnings=[])
        result = planner.build_plan_from_plan(plan, str(tmp_path / "dest"), with_nfo=False)
        moves = [o for o in result.operations if o.type == "move"]
        # 只有视频 move，无伴生（-extra.ass 不算伴生）
        assert len(moves) == 1
        assert moves[0].source.endswith(".mkv")
