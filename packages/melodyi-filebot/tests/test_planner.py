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
