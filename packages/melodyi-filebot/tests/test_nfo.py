"""NFO XML 生成测试（纯数据→XML 层，mock 来源数据）"""

from melodyi_filebot import nfo


def _show_data():
    return {
        "id": 154494, "name": "莉可丽丝", "original_name": "リコリス・リコイル",
        "overview": "x" * 50, "first_air_date": "2022-07-02", "last_air_date": "2022-09-24",
        "in_production": False, "episode_run_time": [24],
        "genres": [{"id": 16, "name": "动画"}],
        "networks": [{"name": "BS11"}],
        "vote_average": 8.5,
        "poster_path": "/abc.jpg", "backdrop_path": "/def.jpg",
        "external_ids": {"imdb_id": "tt13293588", "tvdb_id": 371310},
        "aggregate_credits": {"cast": [{"name": "内山夕实", "roles": [{"character": "鲁迪"}], "order": 0, "profile_path": "/p.jpg"}]},
        "keywords": {"results": [{"name": "isekai"}, {"name": "anime"}]},
        "content_ratings": {"results": [{"rating": "TV-MA", "iso_3166_1": "US"}]},
        "created_by": [{"name": "理不尽な孫の手"}],
    }


class TestTvshowXml:
    def test_tvshow_xml_has_required_fields(self):
        xml = nfo.build_tvshow_xml(_show_data(), bangumi_data=None, language="zh-CN")
        assert "<?xml" in xml and "<tvshow>" in xml and "</tvshow>" in xml
        assert "<title>莉可丽丝</title>" in xml
        assert "<originaltitle>リコリス・リコイル</originaltitle>" in xml
        assert "<plot>" in xml and "x" * 50 in xml  # TMDB overview 原文
        assert "<tmdbid>154494</tmdbid>" in xml
        assert "<imdb_id>tt13293588</imdb_id>" in xml
        assert "<tvdbid>371310</tvdbid>" in xml
        assert "<genre>动画</genre>" in xml
        assert "<tag>isekai</tag>" in xml
        assert "<studio>BS11</studio>" in xml
        assert "<rating>8.5</rating>" in xml
        assert "<lockdata>true</lockdata>" in xml
        assert "<status>Ended</status>" in xml  # in_production=False
        assert "image.tmdb.org/t/p/original/abc.jpg" in xml  # poster URL
        assert "<actor>" in xml and "内山夕实" in xml
        assert "<role>鲁迪</role>" in xml  # 从 aggregate_credits.roles[0] 读取角色

    def test_tvshow_xml_bangumi_fill_when_overview_short(self):
        """TMDB overview <10 字时用 bangumi summary 填 plot"""
        data = dict(_show_data(), overview="短")  # 长度 1
        bg = {"summary": "这是 bangumi 的简介。" * 10, "name_cn": "莉可丽丝", "name": "リコリス"}
        xml = nfo.build_tvshow_xml(data, bangumi_data=bg, language="zh-CN")
        assert "这是 bangumi 的简介" in xml
        assert "短" not in xml.split("<plot>")[1].split("</plot>")[0]

    def test_tvshow_xml_uniqueid(self):
        """uniqueid：TMDB 默认 + bangumi id 附加"""
        bg = {"id": 364450, "summary": "", "name_cn": ""}
        xml = nfo.build_tvshow_xml(_show_data(), bangumi_data=bg, language="zh-CN")
        assert '<uniqueid type="tmdbid" default="true">154494</uniqueid>' in xml
        assert '<uniqueid type="bgm">364450</uniqueid>' in xml

    def test_tvshow_xml_uniqueid_no_bangumi(self):
        """无 bangumi 时只输出 tmdbid uniqueid"""
        xml = nfo.build_tvshow_xml(_show_data(), bangumi_data=None, language="zh-CN")
        assert '<uniqueid type="tmdbid" default="true">154494</uniqueid>' in xml
        assert "bgm" not in xml

    def test_tvshow_xml_dateadded(self):
        """dateadded 传入时输出"""
        xml = nfo.build_tvshow_xml(_show_data(), bangumi_data=None, language="zh-CN",
                                   dateadded="2026-07-01 12:00:00")
        assert "<dateadded>2026-07-01 12:00:00</dateadded>" in xml

    def test_tvshow_xml_escapes_special_chars(self):
        """文本中的 & < > 应被 XML 转义"""
        data = dict(_show_data(), name="A & B <C>", overview="x" * 50)
        xml = nfo.build_tvshow_xml(data, bangumi_data=None, language="zh-CN")
        assert "<title>A &amp; B &lt;C&gt;</title>" in xml


def _season_data():
    return {
        "id": 154494, "season_number": 1, "name": "第 1 季",
        "overview": "x" * 50, "air_date": "2022-07-02",
        "poster_path": "/season.jpg",
    }


class TestSeasonXml:
    def test_season_xml(self):
        xml = nfo.build_season_xml(_season_data(), bangumi_data=None,
                                   show_actors=None, season_number=1,
                                   tmdb_id=154494, dateadded="2026-07-01 12:00:00")
        assert "<season>" in xml and "</season>" in xml
        assert "<title>第 1 季</title>" in xml
        assert "<seasonnumber>1</seasonnumber>" in xml
        assert "<premiered>2022-07-02</premiered>" in xml
        assert "<lockdata>true</lockdata>" in xml
        assert "<dateadded>2026-07-01 12:00:00</dateadded>" in xml
        assert "image.tmdb.org/t/p/original/season.jpg" in xml
        assert '<uniqueid type="tmdbid" default="true">154494-1</uniqueid>' in xml

    def test_season_xml_bangumi_when_no_tmdb_overview(self):
        """TMDB 季 overview 空 + 有 bangumi subject → 用 bangumi summary（物语）"""
        data = dict(_season_data(), overview="")
        bg = {"id": 999, "summary": "物语这一季的简介。" * 10, "name_cn": "化物语", "date": "2009-07-05"}
        xml = nfo.build_season_xml(data, bangumi_data=bg, show_actors=None,
                                   season_number=1, bangumi_subject_id=999)
        assert "物语这一季的简介" in xml
        assert '<uniqueid type="bgm">999</uniqueid>' in xml

    def test_season_xml_inherits_show_actors(self):
        """季 nfo 继承剧级演员"""
        actors = [{"name": "内山夕实", "character": "鲁迪", "order": 0, "profile_path": "/p.jpg",
                   "roles": [{"character": "鲁迪"}]}]
        xml = nfo.build_season_xml(_season_data(), bangumi_data=None,
                                   show_actors=actors, season_number=1, tmdb_id=1)
        assert "<actor>" in xml and "内山夕实" in xml
        assert "<role>鲁迪</role>" in xml  # 从 roles[0].character 读


def _episode_data():
    return {
        "name": "慢慢来", "overview": "x" * 50, "air_date": "2022-07-02",
        "runtime": 24, "episode_number": 1, "season_number": 1,
        "still_path": "/still.jpg", "vote_average": 8.4,
        "guest_stars": [{"name": "竹田海渡", "character": "急救员", "order": 504, "profile_path": "/g.jpg"}],
        "crew": [{"name": "平野宏树", "job": "Director"}, {"name": "岡本学", "job": "Writer"}],
    }


def _stream_details():
    return {
        "video": {"codec": "h264", "width": 1920, "height": 1080, "aspect": "16:9",
                  "framerate": "23.976", "duration": 23, "duration_seconds": 1420},
        "audio": {"codec": "aac", "channels": 2, "samplingrate": 48000},
    }


class TestEpisodeXml:
    def test_episode_xml(self):
        xml = nfo.build_episode_xml(
            _episode_data(), bangumi_data=None, show_title="莉可丽丝",
            target_season=1, target_episode=1, stream_details=_stream_details(),
            tmdb_id=154494, dateadded="2026-07-01 12:00:00",
        )
        assert "<episodedetails>" in xml and "</episodedetails>" in xml
        assert "<title>慢慢来</title>" in xml
        assert "<showtitle>莉可丽丝</showtitle>" in xml
        assert "<season>1</season>" in xml and "<episode>1</episode>" in xml
        assert "<aired>2022-07-02</aired>" in xml
        assert "<runtime>24</runtime>" in xml
        assert "<director>平野宏树</director>" in xml
        assert "<writer>岡本学</writer>" in xml
        assert "<lockdata>true</lockdata>" in xml
        assert "<dateadded>2026-07-01 12:00:00</dateadded>" in xml
        assert "竹田海渡" in xml
        assert "<role>急救员</role>" in xml  # guest_stars character 顶层
        assert "<type>GuestStar</type>" in xml
        assert "<codec>h264</codec>" in xml
        assert "<width>1920</width>" in xml
        assert "<durationinseconds>1420</durationinseconds>" in xml
        assert "image.tmdb.org/t/p/original/still.jpg" in xml
        assert '<uniqueid type="tmdbid" default="true">154494-1-1</uniqueid>' in xml

    def test_episode_xml_displayseason_when_target_ne_source(self):
        """target(S01E05) ≠ source(S00E12) 时写 displayseason/displayepisode"""
        ep = dict(_episode_data(), season_number=0, episode_number=12)
        xml = nfo.build_episode_xml(
            ep, bangumi_data=None, show_title="物语",
            target_season=1, target_episode=5, stream_details=None,
        )
        assert "<displayseason>0</displayseason>" in xml
        assert "<displayepisode>12</displayepisode>" in xml
        assert "<season>1</season>" in xml  # 展示用 target
        assert "<episode>5</episode>" in xml

    def test_episode_xml_bangumi_desc_fill(self):
        ep = dict(_episode_data(), overview="")
        bg = {"id": 1111258, "desc": "bangumi 集简介。" * 10, "name_cn": "慢慢来", "airdate": "2022-07-02"}
        xml = nfo.build_episode_xml(
            ep, bangumi_data=bg, show_title="莉可丽丝",
            target_season=1, target_episode=1, stream_details=None,
        )
        assert "bangumi 集简介" in xml
        assert '<uniqueid type="bgm">1111258</uniqueid>' in xml  # bangumi episode id

    def test_episode_xml_runtime_bangumi_fallback(self):
        """TMDB runtime 缺失时用 bangumi duration 转分钟补"""
        ep = dict(_episode_data(), runtime=None)
        bg = {"id": 111, "desc": "x" * 20, "duration": "00:24:30"}
        xml = nfo.build_episode_xml(
            ep, bangumi_data=bg, show_title="x",
            target_season=1, target_episode=1, stream_details=None,
        )
        assert "<runtime>25</runtime>" in xml  # 24 分 30 秒 → 25（秒数四舍五入）

    def test_episode_xml_no_streamdetails_when_none(self):
        xml = nfo.build_episode_xml(
            _episode_data(), bangumi_data=None, show_title="x",
            target_season=1, target_episode=1, stream_details=None,
        )
        assert "<fileinfo>" not in xml


import os
from melodyi_filebot.models import NfoOperation, NfoSource


class TestGenerateNfo:
    def test_generate_tvshow_writes_xml(self, tmp_path):
        op = NfoOperation(type="tvshow", path=str(tmp_path / "tvshow.nfo"),
                          source=NfoSource(provider="tmdb", tmdb_id=154494, bangumi_subject_id=364450))

        def fake_show(tid, language="zh-CN"):
            return {"id": 154494, "name": "莉可丽丝", "overview": "x" * 50,
                    "episode_run_time": [24], "genres": [], "networks": [],
                    "external_ids": {}, "aggregate_credits": {"cast": []},
                    "keywords": {"results": []}, "content_ratings": {"results": []},
                    "created_by": [], "poster_path": None, "backdrop_path": None,
                    "first_air_date": "2022-07-02", "last_air_date": None,
                    "in_production": False, "vote_average": 8.5}

        def fake_bg_subject(sid):
            return {"id": 364450, "summary": "", "name_cn": ""}

        path = nfo.generate_nfo(op, language="zh-CN", dry_run=False,
                                dateadded="2026-07-01 12:00:00",
                                fetch_show_detail=fake_show,
                                fetch_bangumi_subject=fake_bg_subject)
        assert path.endswith("tvshow.nfo")
        content = open(path, encoding="utf-8").read()
        assert "<tvshow>" in content and "莉可丽丝" in content
        assert "<dateadded>2026-07-01 12:00:00</dateadded>" in content
        assert '<uniqueid type="bgm">364450</uniqueid>' in content

    def test_generate_episode_with_streamdetails(self, tmp_path):
        video = tmp_path / "e.mkv"
        video.write_bytes(b"x")
        op = NfoOperation(type="episode", path=str(tmp_path / "e.nfo"), season=1, episode=1,
                          source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1))
        show_detail = {"id": 154494, "name": "莉可丽丝", "overview": "x" * 50,
                       "episode_run_time": [24], "aggregate_credits": {"cast": []},
                       "external_ids": {}, "keywords": {"results": []},
                       "content_ratings": {"results": []}, "created_by": [],
                       "genres": [], "networks": [], "poster_path": None,
                       "backdrop_path": None, "first_air_date": "2022-07-02",
                       "last_air_date": None, "in_production": False, "vote_average": 0}

        def fake_season(tid, sn, language="zh-CN"):
            return {"season_number": 1, "name": "S1", "episodes": [
                {"episode_number": 1, "name": "e1", "overview": "x" * 50, "season_number": 1,
                 "runtime": 24, "air_date": "2022-07-02", "still_path": None,
                 "vote_average": 8.0, "guest_stars": [], "crew": []}]}

        def fake_probe(path):
            return {"video": {"codec": "h264", "width": 1920, "height": 1080},
                    "audio": {"codec": "aac", "channels": 2}}

        nfo.generate_nfo(op, language="zh-CN", dry_run=False,
                         dateadded="2026-07-01 12:00:00",
                         show_detail=show_detail, fetch_season_detail=fake_season,
                         probe_stream=fake_probe, video_path=str(video))
        content = open(str(tmp_path / "e.nfo"), encoding="utf-8").read()
        assert "<episodedetails>" in content
        assert "<showtitle>莉可丽丝</showtitle>" in content
        assert "<codec>h264</codec>" in content

    def test_generate_episode_bangumi_fill(self, tmp_path):
        """episode TMDB overview 空 + bangumi desc 补"""
        op = NfoOperation(type="episode", path=str(tmp_path / "e.nfo"), season=1, episode=1,
                          source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1,
                                           bangumi_subject_id=364450, bangumi_episode_id=111))
        show_detail = {"id": 154494, "name": "莉可丽丝", "overview": "x" * 50,
                       "episode_run_time": [24], "aggregate_credits": {"cast": []},
                       "external_ids": {}, "keywords": {"results": []},
                       "content_ratings": {"results": []}, "created_by": [],
                       "genres": [], "networks": [], "poster_path": None,
                       "backdrop_path": None, "first_air_date": "2022-07-02",
                       "last_air_date": None, "in_production": False, "vote_average": 0}

        def fake_season(tid, sn, language="zh-CN"):
            return {"season_number": 1, "episodes": [
                {"episode_number": 1, "name": "e1", "overview": "", "season_number": 1,
                 "runtime": None, "air_date": None, "still_path": None,
                 "vote_average": 0, "guest_stars": [], "crew": []}]}

        def fake_bg_eps(sid, ep_type=0):
            from melodyi_filebot.models import BangumiEpisodeBrief
            return [BangumiEpisodeBrief(episode_id=111, name="e1", name_cn="慢慢来",
                                        sort=1, ep=1, desc="bangumi 集简介。" * 10,
                                        airdate="2022-07-02", duration="00:24:00")]

        nfo.generate_nfo(op, language="zh-CN", dry_run=False,
                         show_detail=show_detail, fetch_season_detail=fake_season,
                         fetch_bangumi_episodes=fake_bg_eps)
        content = open(str(tmp_path / "e.nfo"), encoding="utf-8").read()
        assert "bangumi 集简介" in content
        assert "<runtime>24</runtime>" in content  # TMDB runtime None → bangumi duration 转分钟

    def test_dry_run_does_not_write(self, tmp_path):
        op = NfoOperation(type="tvshow", path=str(tmp_path / "tvshow.nfo"),
                          source=NfoSource(provider="tmdb", tmdb_id=1))
        nfo.generate_nfo(op, language="zh-CN", dry_run=True,
                         fetch_show_detail=lambda tid, language="zh-CN": {
                             "id": 1, "name": "x", "overview": "x" * 50,
                             "episode_run_time": [24], "genres": [], "networks": [],
                             "external_ids": {}, "aggregate_credits": {"cast": []},
                             "keywords": {"results": []}, "content_ratings": {"results": []},
                             "created_by": [], "poster_path": None, "backdrop_path": None,
                             "first_air_date": "2020-01-01", "last_air_date": None,
                             "in_production": False, "vote_average": 0})
        assert not (tmp_path / "tvshow.nfo").exists()
