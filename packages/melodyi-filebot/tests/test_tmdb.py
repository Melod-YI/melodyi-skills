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
        monkeypatch.setattr(tmdb, "_api_key", None)
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

    def test_get_season_episodes_empty(self):
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
