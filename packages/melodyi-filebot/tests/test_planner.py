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
