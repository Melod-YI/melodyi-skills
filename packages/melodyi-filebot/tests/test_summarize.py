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
                    {"id": "abc", "name": "HD Remaster", "type": 1}
                ]
            },
        }
        s = summarize.show_summary_from_detail(detail)
        assert len(s.episode_groups) == 1
        assert s.episode_groups[0].id == "abc"

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

    def test_year_from_release_date(self):
        assert summarize._year_from_date("2022-07-02") == 2022
        assert summarize._year_from_date(None) is None
        assert summarize._year_from_date("") is None
