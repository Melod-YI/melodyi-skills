"""NFO XML 生成测试（纯数据→XML 层，mock 来源数据）"""

from melodyi_filebot import nfo


def _show_data():
    return {
        "id": 154494, "name": "莉可丽丝", "original_name": "リコリス・リコイル",
        "overview": "x" * 50, "first_air_date": "2022-07-02", "last_air_date": "2022-09-24",
        "in_production": False, "episode_run_time": 24,
        "genres": [{"id": 16, "name": "动画"}],
        "networks": [{"name": "BS11"}],
        "vote_average": 8.5,
        "poster_path": "/abc.jpg", "backdrop_path": "/def.jpg",
        "external_ids": {"imdb_id": "tt13293588", "tvdb_id": 371310},
        "aggregate_credits": {"cast": [{"name": "内山夕实", "character": "鲁迪", "order": 0, "profile_path": "/p.jpg"}]},
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

    def test_tvshow_xml_bangumi_fill_when_overview_short(self):
        """TMDB overview <10 字时用 bangumi summary 填 plot"""
        data = dict(_show_data(), overview="短")  # 长度 1
        bg = {"summary": "这是 bangumi 的简介。" * 10, "name_cn": "莉可丽丝", "name": "リコリス"}
        xml = nfo.build_tvshow_xml(data, bangumi_data=bg, language="zh-CN")
        assert "这是 bangumi 的简介" in xml
        assert "短" not in xml.split("<plot>")[1].split("</plot>")[0]
