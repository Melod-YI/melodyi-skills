"""摘要压缩测试"""

import pytest
from melodyi_filebot import summarize
from melodyi_filebot.models import ShowSummary


class TestSummarize:
    """summarize 模块测试"""

    def test_show_summary_from_detail(self, tmdb_show_detail):
        s = summarize.show_summary_from_detail(tmdb_show_detail)
        assert s.tmdb_id == 46260
        assert s.title == "莉可丽丝"
        assert s.original_title == "リコリス・リコイル"
        assert s.year == 2022
        assert s.overview_available is True
        assert len(s.seasons) == 2
        assert s.seasons[0].season_number == 0
        assert s.seasons[0].episode_count == 6
        assert s.total_episodes == 19  # 6 + 13

    def test_overview_unavailable_when_short(self):
        detail = {
            "id": 1,
            "name": "t",
            "original_name": "t",
            "first_air_date": "2020-01-01",
            "overview": "短",  # 长度 1
            "seasons": [],
            "episode_groups": {"results": []},
        }
        s = summarize.show_summary_from_detail(detail)
        assert s.overview_available is False
        assert s.overview_length == 1

    def test_overview_unavailable_when_empty(self):
        detail = {
            "id": 1,
            "name": "t",
            "original_name": "t",
            "first_air_date": None,
            "overview": "",
            "seasons": [],
            "episode_groups": {"results": []},
        }
        s = summarize.show_summary_from_detail(detail)
        assert s.overview_available is False

    def test_episode_groups_extracted(self):
        detail = {
            "id": 1,
            "name": "t",
            "original_name": "t",
            "first_air_date": "2020-01-01",
            "overview": "x" * 50,
            "seasons": [],
            "episode_groups": {
                "results": [
                    {"id": "abc", "name": "HD Remaster", "type": 1, "episode_count": 19}
                ]
            },
        }
        s = summarize.show_summary_from_detail(detail)
        assert len(s.episode_groups) == 1
        assert s.episode_groups[0].id == "abc"
        assert s.episode_groups[0].episode_count == 19

    def test_episode_group_from_detail(self):
        """剧集组详情解析：嵌套子组 + 集列表（集带季号）"""
        raw = {
            "id": "g1", "name": "All Episodes + OVAs", "type": 6,
            "episode_count": 19, "group_count": 2,
            "groups": [
                {"id": "s1", "name": "Lycoris Recoil", "order": 0, "episodes": [
                    {"season_number": 1, "episode_number": 1, "name": "慢慢来",
                     "air_date": "2022-07-02", "runtime": 24, "overview": "x" * 50}
                ]},
                {"id": "s2", "name": "OVAs", "order": 1, "episodes": []},
            ],
        }
        d = summarize.episode_group_from_detail(raw)
        assert d.id == "g1"
        assert d.type == 6
        assert d.episode_count == 19
        assert d.group_count == 2
        assert len(d.sub_groups) == 2
        assert d.sub_groups[0].name == "Lycoris Recoil"
        e = d.sub_groups[0].episodes[0]
        assert e.season_number == 1
        assert e.episode_number == 1
        assert e.runtime == 24
        assert e.overview_length == 50
        # 空子组也保留
        assert d.sub_groups[1].episodes == []

    def test_episode_group_from_detail_empty(self):
        """无 groups 的剧集组安全兜底"""
        d = summarize.episode_group_from_detail({"id": "g", "name": "n", "type": 1})
        assert d.id == "g"
        assert d.sub_groups == []
        assert d.episode_count == 0

    def test_candidates_from_search(self):
        search_resp = {
            "results": [
                {
                    "id": 46260,
                    "name": "莉可丽丝",
                    "original_name": "リコリス・リコイル",
                    "first_air_date": "2022-07-02",
                    "overview": "x" * 50,
                    "media_type": "tv",
                }
            ]
        }
        cands = summarize.candidates_from_search(search_resp, media_type="tv")
        assert len(cands) == 1
        assert cands[0].tmdb_id == 46260
        assert cands[0].year == 2022

    def test_candidates_empty(self):
        assert summarize.candidates_from_search({"results": []}, "tv") == []

    def test_candidates_multi_uses_per_result_media_type(self):
        """multi 搜索时，每条结果按自带 media_type 选字段并写入模型

        回归用例：bug 表现为 tv 条目走 movie 字段分支，title/year 为空，
        且 CandidateSummary.media_type 错误地存为 "multi"。
        """
        search_resp = {
            "results": [
                {
                    "id": 45782,
                    "name": "刀剑神域",
                    "original_name": "ソードアート・オンライン",
                    "first_air_date": "2012-07-08",
                    "overview": "x" * 50,
                    "media_type": "tv",
                },
                {
                    "id": 413594,
                    "title": "刀剑神域：序列之争",
                    "original_title": "劇場版 ソードアート・オンライン",
                    "release_date": "2017-02-18",
                    "overview": "y" * 50,
                    "media_type": "movie",
                },
            ]
        }
        cands = summarize.candidates_from_search(search_resp, media_type="multi")
        assert len(cands) == 2
        # tv 条目用 name/first_air_date，类型保留为 tv
        assert cands[0].title == "刀剑神域"
        assert cands[0].original_title == "ソードアート・オンライン"
        assert cands[0].year == 2012
        assert cands[0].media_type == "tv"
        # movie 条目用 title/release_date，类型保留为 movie
        assert cands[1].title == "刀剑神域：序列之争"
        assert cands[1].original_title == "劇場版 ソードアート・オンライン"
        assert cands[1].year == 2017
        assert cands[1].media_type == "movie"

    def test_year_from_release_date(self):
        assert summarize._year_from_date("2022-07-02") == 2022
        assert summarize._year_from_date(None) is None
        assert summarize._year_from_date("") is None
