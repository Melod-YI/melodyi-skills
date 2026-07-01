"""planner 测试"""

import os

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


from melodyi_filebot.models import ShowSummary, SeasonSummary
from melodyi_filebot.planner import build_plan_tv


def _show_summary() -> ShowSummary:
    return ShowSummary(
        tmdb_id=46260,
        title="莉可丽丝",
        original_title="リコリス・リコイル",
        year=2022,
        total_seasons=1,
        total_episodes=13,
        overview_available=True,
        overview_length=100,
        seasons=[
            SeasonSummary(season_number=0, name="Specials", episode_count=6),
            SeasonSummary(season_number=1, name="Season 1", episode_count=13),
        ],
        episode_groups=[],
    )


class TestBuildPlanTv:
    """build_plan_tv 测试"""

    def test_standard_season1(self, tmp_path):
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        f1 = show_dir / "莉可丽丝 S01E01.mkv"
        f2 = show_dir / "莉可丽丝 S01E02.mkv"
        f1.write_bytes(b"x")
        f2.write_bytes(b"x")

        result = build_plan_tv(
            files=[str(f1), str(f2)],
            show=_show_summary(),
            dest_root=str(tmp_path / "dest"),
            language="zh-CN",
        )
        # 期望：mkdir 剧集目录 + mkdir Season 01 + 2 个 move
        assert any(op.type == "mkdir" and "[tmdbid-46260]" in op.path for op in result.operations)
        assert any(op.type == "mkdir" and op.path.endswith("Season 01") for op in result.operations)
        moves = [op for op in result.operations if op.type == "move"]
        assert len(moves) == 2
        assert all("S01E0" in op.path for op in moves)
        assert result.spec_applied == "standard"
        assert result.warnings == []

    def test_specials_season0(self, tmp_path):
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        f1 = show_dir / "特别篇 S00E01.mkv"
        f1.write_bytes(b"x")

        result = build_plan_tv(
            files=[str(f1)],
            show=_show_summary(),
            dest_root=str(tmp_path / "dest"),
            language="zh-CN",
        )
        assert any(op.type == "mkdir" and op.path.endswith("Season 00") for op in result.operations)
        moves = [op for op in result.operations if op.type == "move"]
        assert len(moves) == 1
        assert "S00E01" in moves[0].path

    def test_unparseable_file_warning(self, tmp_path):
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        f1 = show_dir / "random video.mkv"  # 无 S/E
        f1.write_bytes(b"x")

        result = build_plan_tv(
            files=[str(f1)],
            show=_show_summary(),
            dest_root=str(tmp_path / "dest"),
            language="zh-CN",
        )
        assert any("无法解析" in w for w in result.warnings)
        # 不可解析文件不产生 move
        assert all(op.type != "move" for op in result.operations)

    def test_invalid_char_sanitized(self, tmp_path):
        """标题含非法字符需清理"""
        show = ShowSummary(
            tmdb_id=1, title="剧:名", original_title="x", year=2020,
            total_seasons=1, total_episodes=1, seasons=[
                SeasonSummary(season_number=1, name="S1", episode_count=1)
            ],
        )
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        f1 = show_dir / "剧:名 S01E01.mkv"
        f1.write_bytes(b"x")
        result = build_plan_tv(
            files=[str(f1)], show=show, dest_root=str(tmp_path / "dest"), language="zh-CN"
        )
        mkdirs = [op.path for op in result.operations if op.type == "mkdir"]
        # 检查文件夹名本身（basename）不含非法字符；完整路径在 Windows 上含盘符冒号 C:
        assert all(":" not in p.replace("\\", "/").split("/")[-1] for p in mkdirs)

    def test_part_in_generated_filename(self, tmp_path):
        """part 段应生成 S01E01-part-1 文件名（part 与编号间有连字符）"""
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        f1 = show_dir / "Series A S01E01-part-1.mkv"
        f1.write_bytes(b"x")
        result = build_plan_tv(
            files=[str(f1)], show=_show_summary(),
            dest_root=str(tmp_path / "dest"), language="zh-CN",
        )
        moves = [op for op in result.operations if op.type == "move"]
        assert len(moves) == 1
        assert "S01E01-part-1" in moves[0].path


from melodyi_filebot.models import CandidateSummary
from melodyi_filebot.planner import build_plan_movie


class TestBuildPlanMovie:
    """build_plan_movie 测试"""

    def test_standard_movie(self, tmp_path):
        src = tmp_path / "源"
        src.mkdir()
        f = src / "某电影.2020.1080p.mkv"
        f.write_bytes(b"x")
        cand = CandidateSummary(
            tmdb_id=123, title="某电影", original_title="Mov", year=2020,
            overview_length=50, media_type="movie",
        )
        result = build_plan_movie(
            files=[str(f)], movie=cand, dest_root=str(tmp_path / "dest")
        )
        mkdirs = [op.path for op in result.operations if op.type == "mkdir"]
        assert any("某电影 (2020) [tmdbid-123]" in p for p in mkdirs)
        moves = [op for op in result.operations if op.type == "move"]
        assert len(moves) == 1
        assert "某电影 (2020).mkv" in moves[0].path

    def test_empty_files_warning(self, tmp_path):
        """空文件列表不应崩溃，且不应产生 move 操作"""
        cand = CandidateSummary(
            tmdb_id=123, title="某电影", original_title="Mov", year=2020,
            overview_length=50, media_type="movie",
        )
        result = build_plan_movie(files=[], movie=cand, dest_root=str(tmp_path / "dest"))
        assert all(op.type != "move" for op in result.operations)
        # 仍创建 movie 目录
        assert any(op.type == "mkdir" for op in result.operations)
        assert any("未找到视频文件" in w for w in result.warnings)


class TestCompanions:
    """伴生文件（字幕等 sidecar）自动改名测试

    规则：视频改名时，同目录下「视频 stem.」前缀的非视频文件随之改名，
    目标名 = 改名后视频 stem + 原后缀（语言 token 等原样保留）。
    """

    def _show(self):
        return ShowSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス", year=2022,
            total_seasons=1, total_episodes=13,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=13)],
        )

    def test_tv_subtitle_renamed_with_video(self, tmp_path):
        """视频改名时同名字幕随之改名，落到同季目录"""
        src = tmp_path / "src"
        src.mkdir()
        v = src / "Show S01E01.mkv"
        sub = src / "Show S01E01.ass"
        v.write_bytes(b"x")
        sub.write_text("x")
        result = build_plan_tv(
            files=[str(v)], show=self._show(), dest_root=str(tmp_path / "dest")
        )
        moves = {op.source: op.path for op in result.operations if op.type == "move"}
        # 视频与字幕都产生 move
        assert str(sub) in moves
        # 字幕落到 Season 01，目标名=视频新 stem + 原后缀
        assert "Season 01" in moves[str(sub)]
        assert moves[str(sub)].replace("\\", "/").endswith("/莉可丽丝 (2022) S01E01.ass")

    def test_tv_language_tag_suffix_preserved(self, tmp_path):
        """.TC.ass 的语言 token 后缀原样保留"""
        src = tmp_path / "src"
        src.mkdir()
        v = src / "Show S01E01.mkv"
        tc = src / "Show S01E01.TC.ass"
        v.write_bytes(b"x")
        tc.write_text("x")
        result = build_plan_tv(
            files=[str(v)], show=self._show(), dest_root=str(tmp_path / "dest")
        )
        moves = {op.source: op.path for op in result.operations if op.type == "move"}
        assert moves[str(tc)].replace("\\", "/").endswith("/莉可丽丝 (2022) S01E01.TC.ass")

    def test_tv_partial_prefix_companion_excluded(self, tmp_path):
        """部分前缀（stem 后非 '.'）的文件不当伴生"""
        src = tmp_path / "src"
        src.mkdir()
        v = src / "Show S01E01.mkv"
        other = src / "Show S01E01-extra.ass"  # stem 后是 '-'，非伴生
        v.write_bytes(b"x")
        other.write_text("x")
        result = build_plan_tv(
            files=[str(v)], show=self._show(), dest_root=str(tmp_path / "dest")
        )
        moves = [op for op in result.operations if op.type == "move"]
        # 只有视频一个 move
        assert len(moves) == 1
        assert moves[0].source == str(v)

    def test_tv_from_map_companions_follow(self, tmp_path):
        """override 模式：伴生跟随 map 里的视频条目"""
        from melodyi_filebot.planner import build_plan_tv_from_map
        from melodyi_filebot.models import PlanMap, FileMapping
        src = tmp_path / "src"
        src.mkdir()
        v = src / "随便.mkv"
        sub = src / "随便.ass"
        v.write_bytes(b"x")
        sub.write_text("x")
        plan_map = PlanMap(
            media_type="tv", tmdb_id=46260,
            mappings=[FileMapping(file=str(v), season=1, episode=1)],
        )
        result = build_plan_tv_from_map(plan_map, self._show(), dest_root=str(tmp_path / "dest"))
        moves = {op.source: op.path for op in result.operations if op.type == "move"}
        assert str(sub) in moves
        assert moves[str(sub)].replace("\\", "/").endswith("/莉可丽丝 (2022) S01E01.ass")

    def test_movie_companions_follow(self, tmp_path):
        """电影正片改名时伴生随之改名"""
        src = tmp_path / "src"
        src.mkdir()
        v = src / "某电影.2020.mkv"
        sub = src / "某电影.2020.ass"
        v.write_bytes(b"x")
        sub.write_text("x")
        movie = CandidateSummary(
            tmdb_id=123, title="某电影", original_title="Mov", year=2020,
            overview_length=50, media_type="movie",
        )
        result = build_plan_movie(files=[str(v)], movie=movie, dest_root=str(tmp_path / "dest"))
        moves = {op.source: op.path for op in result.operations if op.type == "move"}
        assert str(sub) in moves
        assert moves[str(sub)].replace("\\", "/").endswith("/某电影 (2020).ass")

    def test_movie_from_map_companions_follow(self, tmp_path):
        """电影 override：正片伴生随之改名"""
        from melodyi_filebot.planner import build_plan_movie_from_map
        from melodyi_filebot.models import PlanMap, FileMapping
        src = tmp_path / "src"
        src.mkdir()
        v = src / "main.mkv"
        sub = src / "main.ass"
        v.write_bytes(b"x")
        sub.write_text("x")
        movie = CandidateSummary(
            tmdb_id=123, title="某电影", original_title="Mov", year=2020,
            overview_length=50, media_type="movie",
        )
        plan_map = PlanMap(
            media_type="movie", tmdb_id=123,
            mappings=[FileMapping(file=str(v))],
        )
        result = build_plan_movie_from_map(plan_map, movie, dest_root=str(tmp_path / "dest"))
        moves = {op.source: op.path for op in result.operations if op.type == "move"}
        assert str(sub) in moves
        assert moves[str(sub)].replace("\\", "/").endswith("/某电影 (2020).ass")


class TestPathNormalization:
    """输入路径归一化测试

    覆盖：末尾斜杠、混合分隔符、源/目标路径一致性。
    断言用「路径已归一化」(normpath 幂等) 判断，平台无关。
    """

    def test_tv_dest_root_trailing_slash_normalized(self, tmp_path):
        """dest_root 带尾斜杠不应产生双分隔符"""
        show = ShowSummary(
            tmdb_id=1, title="t", original_title="t", year=2020,
            total_seasons=1, total_episodes=1,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=1)],
        )
        src = tmp_path / "src"
        src.mkdir()
        f = src / "t S01E01.mkv"
        f.write_bytes(b"x")
        # 带平台分隔符尾斜杠
        dest = str(tmp_path / "dest") + os.sep
        result = build_plan_tv(files=[str(f)], show=show, dest_root=dest)
        for op in result.operations:
            assert op.path == os.path.normpath(op.path), f"路径未归一化: {op.path!r}"

    def test_tv_dest_root_forward_slash_trailing_normalized(self, tmp_path):
        """dest_root 以正斜杠结尾（跨平台输入）也应归一化"""
        show = ShowSummary(
            tmdb_id=1, title="t", original_title="t", year=2020,
            total_seasons=1, total_episodes=1,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=1)],
        )
        src = tmp_path / "src"
        src.mkdir()
        f = src / "t S01E01.mkv"
        f.write_bytes(b"x")
        dest = str(tmp_path / "dest") + "/"
        result = build_plan_tv(files=[str(f)], show=show, dest_root=dest)
        for op in result.operations:
            assert op.path == os.path.normpath(op.path), f"路径未归一化: {op.path!r}"

    def test_tv_move_source_normalized(self, tmp_path):
        """move 的 source 路径应归一化"""
        show = ShowSummary(
            tmdb_id=1, title="t", original_title="t", year=2020,
            total_seasons=1, total_episodes=1,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=1)],
        )
        src = tmp_path / "src"
        src.mkdir()
        f = src / "t S01E01.mkv"
        f.write_bytes(b"x")
        result = build_plan_tv(files=[str(f)], show=show, dest_root=str(tmp_path / "dest"))
        moves = [op for op in result.operations if op.type == "move"]
        assert moves
        assert moves[0].source == os.path.normpath(moves[0].source)

    def test_movie_dest_root_trailing_slash_normalized(self, tmp_path):
        """电影计划同样归一化 dest_root 尾斜杠"""
        src = tmp_path / "src"
        src.mkdir()
        f = src / "某电影.2020.mkv"
        f.write_bytes(b"x")
        movie = CandidateSummary(
            tmdb_id=123, title="某电影", original_title="Mov", year=2020,
            overview_length=50, media_type="movie",
        )
        dest = str(tmp_path / "dest") + os.sep
        result = build_plan_movie(files=[str(f)], movie=movie, dest_root=dest)
        for op in result.operations:
            assert op.path == os.path.normpath(op.path), f"路径未归一化: {op.path!r}"

    def test_paths_use_platform_separator(self, tmp_path):
        """归一化后路径使用平台原生分隔符（无混合 / 与 \）"""
        show = ShowSummary(
            tmdb_id=1, title="t", original_title="t", year=2020,
            total_seasons=1, total_episodes=1,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=1)],
        )
        src = tmp_path / "src"
        src.mkdir()
        f = src / "t S01E01.mkv"
        f.write_bytes(b"x")
        result = build_plan_tv(files=[str(f)], show=show, dest_root=str(tmp_path / "dest") + "/")
        for op in result.operations:
            # 归一化后不应再含另一种分隔符
            if os.altsep:
                assert os.altsep not in op.path, f"路径含非原生分隔符: {op.path!r}"


class TestSeasonHint:
    """--season 季提示测试：文件名无季标记时用提示季号"""

    def _show(self):
        return ShowSummary(
            tmdb_id=1, title="剧", original_title="x", year=2020,
            total_seasons=2, total_episodes=24,
            seasons=[
                SeasonSummary(season_number=1, name="S1", episode_count=12),
                SeasonSummary(season_number=2, name="S2", episode_count=12),
            ],
        )

    def test_season_hint_applied_to_seasonless_files(self, tmp_path):
        """文件名无季标记（方括号集号），--season 让它们落到指定季"""
        src = tmp_path / "src"
        src.mkdir()
        f1 = src / "Amagami [01].mkv"
        f2 = src / "Amagami [02].mkv"
        f1.write_bytes(b"x")
        f2.write_bytes(b"x")
        result = build_plan_tv(
            files=[str(f1), str(f2)], show=self._show(),
            dest_root=str(tmp_path / "dest"), season_hint=2,
        )
        moves = [op for op in result.operations if op.type == "move"]
        assert len(moves) == 2
        assert all("Season 02" in op.path for op in moves)
        assert all("S02E0" in op.path for op in moves)

    def test_explicit_season_in_filename_wins_over_hint(self, tmp_path):
        """文件名有显式季标记（如 S00 特别篇），--season 不覆盖"""
        src = tmp_path / "src"
        src.mkdir()
        special = src / "剧 S00E01.mkv"
        normal = src / "剧 [02].mkv"
        special.write_bytes(b"x")
        normal.write_bytes(b"x")
        result = build_plan_tv(
            files=[str(special), str(normal)], show=self._show(),
            dest_root=str(tmp_path / "dest"), season_hint=2,
        )
        moves = {op.source: op.path for op in result.operations if op.type == "move"}
        assert "Season 00" in moves[str(special)]
        assert "S00E01" in moves[str(special)]
        assert "Season 02" in moves[str(normal)]
        assert "S02E02" in moves[str(normal)]

    def test_no_hint_defaults_to_season1(self, tmp_path):
        """无 --season 且文件名无季标记 → 默认 Season 01"""
        src = tmp_path / "src"
        src.mkdir()
        f = src / "剧 [01].mkv"
        f.write_bytes(b"x")
        result = build_plan_tv(
            files=[str(f)], show=self._show(),
            dest_root=str(tmp_path / "dest"),
        )
        moves = [op for op in result.operations if op.type == "move"]
        assert "Season 01" in moves[0].path
        assert "S01E01" in moves[0].path


class TestDraftAndOverrideMap:
    """draft-map 生成与 build-plan --map override 测试"""

    def _show(self):
        return ShowSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス", year=2022,
            total_seasons=2, total_episodes=19,
            seasons=[
                SeasonSummary(season_number=0, name="Specials", episode_count=6),
                SeasonSummary(season_number=1, name="S1", episode_count=13),
            ],
        )

    def test_draft_map_tv_emits_parsed_guesses(self, tmp_path):
        """draft-map 输出每个文件的解析猜测，含无法解析项"""
        from melodyi_filebot.planner import draft_map_tv
        src = tmp_path / "src"
        src.mkdir()
        f1 = src / "Show S02E01.mkv"
        f2 = src / "Show [03].mkv"
        f3 = src / "unknown.mkv"
        for f in (f1, f2, f3):
            f.write_bytes(b"x")
        m = draft_map_tv([str(f1), str(f2), str(f3)], tmdb_id=46260, season_hint=2)
        assert m.media_type == "tv"
        assert m.tmdb_id == 46260
        assert len(m.mappings) == 3
        by_file = {x.file: x for x in m.mappings}
        # 显式季标记保留
        assert by_file[str(f1)].season == 2 and by_file[str(f1)].episode == 1
        # 无季标记用 season_hint
        assert by_file[str(f2)].season == 2 and by_file[str(f2)].episode == 3
        # 无法解析：episode 为 None
        assert by_file[str(f3)].episode is None

    def test_build_plan_tv_from_map_uses_explicit_mapping(self, tmp_path):
        """build-plan --map 按显式映射构建，不解析文件名"""
        from melodyi_filebot.planner import build_plan_tv_from_map
        from melodyi_filebot.models import PlanMap, FileMapping
        src = tmp_path / "src"
        src.mkdir()
        f1 = src / "随便起的名.mkv"
        f2 = src / "another.mkv"
        f1.write_bytes(b"x")
        f2.write_bytes(b"x")
        plan_map = PlanMap(
            media_type="tv", tmdb_id=46260, language="zh-CN",
            mappings=[
                FileMapping(file=str(f1), season=2, episode=1),
                FileMapping(file=str(f2), season=0, episode=3),
            ],
        )
        result = build_plan_tv_from_map(plan_map, self._show(), dest_root=str(tmp_path / "dest"))
        moves = {op.source: op.path for op in result.operations if op.type == "move"}
        assert "Season 02" in moves[str(f1)] and "S02E01" in moves[str(f1)]
        assert "Season 00" in moves[str(f2)] and "S00E03" in moves[str(f2)]
        assert result.spec_applied == "override"

    def test_build_plan_tv_from_map_skips_missing_episode(self, tmp_path):
        """映射中 episode 为 None 的项跳过并告警"""
        from melodyi_filebot.planner import build_plan_tv_from_map
        from melodyi_filebot.models import PlanMap, FileMapping
        src = tmp_path / "src"
        src.mkdir()
        f1 = src / "a.mkv"
        f2 = src / "b.mkv"
        f1.write_bytes(b"x")
        f2.write_bytes(b"x")
        plan_map = PlanMap(
            media_type="tv", tmdb_id=46260,
            mappings=[
                FileMapping(file=str(f1), season=1, episode=1),
                FileMapping(file=str(f2), season=None, episode=None),
            ],
        )
        result = build_plan_tv_from_map(plan_map, self._show(), dest_root=str(tmp_path / "dest"))
        moves = [op for op in result.operations if op.type == "move"]
        assert len(moves) == 1
        assert any("缺少集号" in w or "跳过" in w for w in result.warnings)

    def test_build_plan_movie_from_map(self, tmp_path):
        """电影 override：第一个映射为正片"""
        from melodyi_filebot.planner import build_plan_movie_from_map
        from melodyi_filebot.models import PlanMap, FileMapping, CandidateSummary
        src = tmp_path / "src"
        src.mkdir()
        f1 = src / "main.mkv"
        f2 = src / "extra.mkv"
        f1.write_bytes(b"x")
        f2.write_bytes(b"x")
        movie = CandidateSummary(
            tmdb_id=123, title="某电影", original_title="Mov", year=2020,
            overview_length=50, media_type="movie",
        )
        plan_map = PlanMap(
            media_type="movie", tmdb_id=123,
            mappings=[FileMapping(file=str(f1)), FileMapping(file=str(f2))],
        )
        result = build_plan_movie_from_map(plan_map, movie, dest_root=str(tmp_path / "dest"))
        moves = [op for op in result.operations if op.type == "move"]
        assert len(moves) == 1
        assert moves[0].source == str(f1)
        assert "某电影 (2020).mkv" in moves[0].path
        assert result.spec_applied == "override"


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
