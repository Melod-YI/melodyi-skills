"""Bangumi v0 调用封装测试（mock 网络调用）

与 test_tmdb.py 同模式：mock 网络层（这里直接注入 fake httpx client 到模块级
bangumi._client），断言三个原语的解析与请求构造。
"""

from unittest.mock import MagicMock

import pytest

from melodyi_filebot import bangumi


def _fake_response(data, status=200):
    """构造假的 httpx.Response：status_code / raise_for_status / json"""
    r = MagicMock()
    r.status_code = status
    r.raise_for_status.return_value = None
    r.json.return_value = data
    return r


def _set_client(resp_or_side_effect):
    """注入 fake client：单个响应 → return_value；列表 → side_effect"""
    client = MagicMock()
    if isinstance(resp_or_side_effect, list):
        client.request.side_effect = resp_or_side_effect
    else:
        client.request.return_value = resp_or_side_effect
    bangumi._client = client
    return client


@pytest.fixture(autouse=True)
def _reset_client():
    """每个测试前后重置模块级 client，避免真实 httpx.Client 被创建"""
    bangumi._client = None
    yield
    bangumi._client = None


# ---------- 搜索响应/条目响应 fixture ----------

_SEARCH_HIT = {
    "id": 364450,
    "type": 2,
    "name": "リコリス・リコイル",
    "name_cn": "莉可丽丝",
    "date": "2022-07-02",
    "eps": 13,
    "platform": "TV",
    "summary": "x" * 50,
}

_SUBJECT_DETAIL = {
    "id": 364450,
    "type": 2,
    "name": "リコリス・リコイル",
    "name_cn": "莉可丽丝",
    "date": "2022-07-02",
    "eps": 13,
    "platform": "TV",
    "summary": "x" * 50,
}

_EPISODE = {
    "id": 1111258,
    "type": 0,
    "name": "Easy does it",
    "name_cn": "慢慢来",
    "sort": 1,
    "ep": 1,
    "airdate": "2022-07-02",
    "duration": "00:24:00",
    "desc": "x" * 50,
}


class TestSearchAnime:
    """search_anime 测试"""

    def test_returns_subjects(self):
        data = {"data": [_SEARCH_HIT], "total": 1}
        client = _set_client(_fake_response(data))
        cands = bangumi.search_anime("莉可丽丝")
        assert len(cands) == 1
        c = cands[0]
        assert c.subject_id == 364450
        assert c.name_cn == "莉可丽丝"
        assert c.name == "リコリス・リコイル"
        assert c.eps == 13
        assert c.platform == "TV"
        assert c.summary_available is True
        # 请求体限定动画类型
        _, kwargs = client.request.call_args
        assert kwargs["json"]["filter"] == {"type": [2]}
        assert kwargs["json"]["keyword"] == "莉可丽丝"

    def test_empty_results(self):
        _set_client(_fake_response({"data": [], "total": 0}))
        assert bangumi.search_anime("不存在") == []

    def test_summary_unavailable_when_short(self):
        """summary 长度 <10 时 summary_available=False"""
        hit = dict(_SEARCH_HIT, summary="短")
        _set_client(_fake_response({"data": [hit], "total": 1}))
        cands = bangumi.search_anime("x")
        assert cands[0].summary_available is False
        assert cands[0].summary_length == 1


class TestGetSubject:
    """get_subject 测试"""

    def test_returns_subject(self):
        _set_client(_fake_response(_SUBJECT_DETAIL))
        s = bangumi.get_subject(364450)
        assert s.subject_id == 364450
        assert s.summary_length == 50
        assert s.summary_available is True
        assert s.date == "2022-07-02"

    def test_missing_fields_tolerated(self):
        """字段缺失时安全兜底"""
        _set_client(_fake_response({"id": 1, "type": 2, "name": "n", "name_cn": "c"}))
        s = bangumi.get_subject(1)
        assert s.subject_id == 1
        assert s.eps == 0
        assert s.platform == ""
        assert s.summary_length == 0
        assert s.summary_available is False
        assert s.date is None


class TestGetSubjectEpisodes:
    """get_subject_episodes 测试"""

    def test_single_page(self):
        data = {"data": [_EPISODE], "total": 1, "limit": 50, "offset": 0}
        _set_client(_fake_response(data))
        eps = bangumi.get_subject_episodes(364450, ep_type=0)
        assert len(eps) == 1
        e = eps[0]
        assert e.episode_id == 1111258
        assert e.name_cn == "慢慢来"
        assert e.duration == "00:24:00"
        assert e.desc_available is True
        assert e.ep == 1

    def test_pagination(self):
        """total=120 应翻页 3 次（offset 0/50/100）合并 120 条"""
        def page(n, start):
            return [
                {"id": start + i, "type": 0, "name": f"n{i}", "name_cn": f"c{i}",
                 "sort": start + i, "ep": start + i, "desc": "x" * 20}
                for i in range(n)
            ]

        responses = [
            _fake_response({"data": page(50, 1), "total": 120, "limit": 50, "offset": 0}),
            _fake_response({"data": page(50, 51), "total": 120, "limit": 50, "offset": 50}),
            _fake_response({"data": page(20, 101), "total": 120, "limit": 50, "offset": 100}),
        ]
        client = MagicMock()
        client.request.side_effect = responses
        bangumi._client = client

        eps = bangumi.get_subject_episodes(1, ep_type=0)
        assert len(eps) == 120
        assert client.request.call_count == 3

    def test_desc_unavailable_when_missing(self):
        """desc 缺失/为空时 desc_available=False"""
        ep = dict(_EPISODE, desc="")
        _set_client(_fake_response({"data": [ep], "total": 1}))
        eps = bangumi.get_subject_episodes(364450)
        assert eps[0].desc_available is False
        assert eps[0].desc_length == 0

    def test_empty_episodes(self):
        _set_client(_fake_response({"data": [], "total": 0}))
        assert bangumi.get_subject_episodes(364450) == []


class TestErrors:
    """错误处理测试"""

    def test_404_raises_runtime_error(self):
        r = MagicMock()
        r.status_code = 404
        _set_client(r)
        with pytest.raises(RuntimeError, match="Bangumi 未找到资源"):
            bangumi.get_subject(999999)

    def test_non_2xx_raises(self):
        r = MagicMock()
        r.status_code = 500
        r.raise_for_status.side_effect = RuntimeError("server error")
        _set_client(r)
        with pytest.raises(RuntimeError):
            bangumi.get_subject(1)
