"""TMDB 封装测试（mock 网络调用）"""

from unittest.mock import patch, MagicMock

import pytest

from melodyi_filebot import tmdb


@pytest.fixture(autouse=True)
def _set_key(monkeypatch):
    """所有测试注入 API key"""
    monkeypatch.setattr(tmdb, "_api_key", "test_key")


class TestSearch:
    """search 测试"""

    def test_search_tv_returns_candidates(self):
        mock_search = MagicMock()
        mock_search.tv.return_value = {
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
        with patch("melodyi_filebot.tmdb.tmdbsimple.Search", return_value=mock_search):
            cands = tmdb.search("莉可丽丝", media_type="tv", language="zh-CN")
        assert len(cands) == 1
        assert cands[0].tmdb_id == 46260
        mock_search.tv.assert_called_once_with(query="莉可丽丝", language="zh-CN")

    def test_search_movie(self):
        mock_search = MagicMock()
        mock_search.movie.return_value = {"results": []}
        with patch("melodyi_filebot.tmdb.tmdbsimple.Search", return_value=mock_search):
            cands = tmdb.search("某电影", media_type="movie", language="zh-CN")
        assert cands == []
        mock_search.movie.assert_called_once_with(query="某电影", language="zh-CN")

    def test_search_multi(self):
        mock_search = MagicMock()
        mock_search.multi.return_value = {
            "results": [
                {"id": 1, "name": "A", "original_name": "A", "media_type": "tv",
                 "first_air_date": "2020-01-01", "overview": "x" * 50},
                {"id": 2, "title": "B", "original_title": "B", "media_type": "movie",
                 "release_date": "2021-01-01", "overview": "x" * 50},
            ]
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.Search", return_value=mock_search):
            cands = tmdb.search("x", media_type="multi", language="zh-CN")
        assert len(cands) == 2

    def test_search_raises_without_key(self, monkeypatch):
        """未配置 key 时应抛 RuntimeError

        注意：必须同时 mock load_tmdb_api_key 返回 None，
        否则 _ensure_key 会重新读取真实配置文件（环境里可能已配 key）。
        """
        monkeypatch.setattr(tmdb, "_api_key", None)
        monkeypatch.setattr(tmdb.config, "load_tmdb_api_key", lambda: None)
        with pytest.raises(RuntimeError, match="TMDB_API_KEY"):
            tmdb.search("x", media_type="tv")


class TestShowSummary:
    """get_show_summary 测试"""

    def test_get_show_summary(self, tmdb_show_detail):
        mock_tv = MagicMock()
        mock_tv.info.return_value = tmdb_show_detail
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV", return_value=mock_tv):
            s = tmdb.get_show_summary(46260, language="zh-CN")
        assert s.tmdb_id == 46260
        assert s.total_seasons == 2
        assert s.total_episodes == 19
        mock_tv.info.assert_called_once()
        _, kwargs = mock_tv.info.call_args
        assert kwargs.get("append_to_response") == "episode_groups"

    def test_get_show_summary_uses_language(self, tmdb_show_detail):
        mock_tv = MagicMock()
        mock_tv.info.return_value = tmdb_show_detail
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV", return_value=mock_tv):
            tmdb.get_show_summary(46260, language="ja-JP")
        _, kwargs = mock_tv.info.call_args
        assert kwargs.get("language") == "ja-JP"


class TestSeasonEpisodes:
    """get_season_episodes 测试"""

    def test_get_season_episodes(self):
        mock_seasons = MagicMock()
        mock_seasons.info.return_value = {
            "episodes": [
                {"episode_number": 1, "name": "第一集", "air_date": "2022-07-02", "overview": "x" * 50},
                {"episode_number": 2, "name": "第二集", "air_date": "2022-07-09", "overview": "x" * 50},
            ]
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV_Seasons", return_value=mock_seasons):
            eps = tmdb.get_season_episodes(46260, 1, language="zh-CN")
        assert len(eps) == 2
        assert eps[0].episode_number == 1
        assert eps[0].overview_available is True

    def test_get_season_episodes_includes_runtime(self):
        """集摘要应包含 runtime（分钟）"""
        mock_seasons = MagicMock()
        mock_seasons.info.return_value = {
            "episodes": [
                {"episode_number": 1, "name": "第一集", "air_date": "2022-07-02", "overview": "x" * 50, "runtime": 24},
                {"episode_number": 2, "name": "第二集", "air_date": "2022-07-09", "overview": "x" * 50, "runtime": 23},
            ]
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV_Seasons", return_value=mock_seasons):
            eps = tmdb.get_season_episodes(46260, 1, language="zh-CN")
        assert len(eps) == 2
        assert eps[0].episode_number == 1
        assert eps[0].overview_available is True
        assert eps[0].runtime == 24
        assert eps[1].runtime == 23

    def test_get_season_episodes_runtime_none_when_missing(self):
        """TMDB 无 runtime 字段时为 None"""
        mock_seasons = MagicMock()
        mock_seasons.info.return_value = {
            "episodes": [
                {"episode_number": 1, "name": "第一集", "overview": "x" * 50},
            ]
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV_Seasons", return_value=mock_seasons):
            eps = tmdb.get_season_episodes(46260, 1)
        assert eps[0].runtime is None
        mock_seasons = MagicMock()
        mock_seasons.info.return_value = {"episodes": []}
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV_Seasons", return_value=mock_seasons):
            eps = tmdb.get_season_episodes(46260, 1)
        assert eps == []


from melodyi_filebot.models import CandidateSummary


class TestMovieSummary:
    """get_movie_summary 测试"""

    def test_get_movie_summary(self):
        mock_movie = MagicMock()
        mock_movie.info.return_value = {
            "id": 550,
            "title": "搏击俱乐部",
            "original_title": "Fight Club",
            "release_date": "1999-10-15",
            "overview": "x" * 50,
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.Movies", return_value=mock_movie):
            movie = tmdb.get_movie_summary(550, language="zh-CN")
        assert movie.tmdb_id == 550
        assert movie.title == "搏击俱乐部"
        assert movie.year == 1999
        assert movie.media_type == "movie"


class TestEpisodeGroup:
    """get_episode_group 测试"""

    def test_get_episode_group(self):
        mock_eg = MagicMock()
        mock_eg.info.return_value = {
            "id": "g1", "name": "All Episodes + OVAs", "type": 6,
            "episode_count": 19, "group_count": 2,
            "groups": [
                {"name": "Lycoris Recoil", "episodes": [
                    {"season_number": 1, "episode_number": 1, "name": "慢慢来",
                     "air_date": "2022-07-02", "runtime": 24, "overview": "x" * 50}
                ]},
            ],
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV_Episode_Groups", return_value=mock_eg):
            d = tmdb.get_episode_group("g1", language="zh-CN")
        assert d.id == "g1"
        assert d.type == 6
        assert d.sub_groups[0].name == "Lycoris Recoil"
        assert d.sub_groups[0].episodes[0].season_number == 1
        mock_eg.info.assert_called_once_with(language="zh-CN")

    def test_get_episode_group_passes_language(self):
        mock_eg = MagicMock()
        mock_eg.info.return_value = {"id": "g", "name": "n", "type": 1, "groups": []}
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV_Episode_Groups", return_value=mock_eg):
            tmdb.get_episode_group("g", language="ja-JP")
        _, kwargs = mock_eg.info.call_args
        assert kwargs.get("language") == "ja-JP"


class TestShowDetailFull:
    """get_show_detail_full：append 全量字段"""

    def test_uses_append_to_response(self):
        mock_tv = MagicMock()
        mock_tv.info.return_value = {"id": 154494, "name": "莉可丽丝"}
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV", return_value=mock_tv):
            tmdb.get_show_detail_full(154494, language="zh-CN")
        _, kwargs = mock_tv.info.call_args
        append = kwargs.get("append_to_response", "")
        for part in ["external_ids", "aggregate_credits", "keywords", "content_ratings"]:
            assert part in append, f"应 append {part}"

    def test_returns_raw_dict(self):
        mock_tv = MagicMock()
        mock_tv.info.return_value = {"id": 154494, "name": "莉可丽丝", "overview": "x" * 50}
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV", return_value=mock_tv):
            d = tmdb.get_show_detail_full(154494, language="zh-CN")
        assert d["id"] == 154494
        assert d["name"] == "莉可丽丝"


class TestSeasonDetail:
    """get_season_detail：含每集 crew/guest_stars"""

    def test_returns_raw_dict(self):
        mock_s = MagicMock()
        mock_s.info.return_value = {
            "id": 154494, "season_number": 1, "name": "S1",
            "episodes": [{"episode_number": 1, "name": "e1", "crew": [], "guest_stars": []}],
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV_Seasons", return_value=mock_s):
            d = tmdb.get_season_detail(154494, 1, language="zh-CN")
        assert d["season_number"] == 1
        assert d["episodes"][0]["name"] == "e1"
        mock_s.info.assert_called_once()
