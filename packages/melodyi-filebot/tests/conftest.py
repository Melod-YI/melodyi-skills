"""pytest 公共 fixtures"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def tmdb_show_detail() -> dict:
    """TV.info 响应快照（莉可丽丝，简化）"""
    return {
        "id": 46260,
        "name": "莉可丽丝",
        "original_name": "リコリス・リコイル",
        "first_air_date": "2022-07-02",
        "overview": "一名少女的故事。" * 20,
        "seasons": [
            {
                "season_number": 0,
                "name": "Specials",
                "episode_count": 6,
                "air_date": "2022-09-28",
                "overview": "特别篇",
            },
            {
                "season_number": 1,
                "name": "Season 1",
                "episode_count": 13,
                "air_date": "2022-07-02",
                "overview": "正篇",
            },
        ],
        "episode_groups": {"results": []},
    }


@pytest.fixture
def media_root(tmp_path: Path) -> Path:
    """临时媒体目录，含一个剧集文件夹与若干视频文件"""
    show_dir = tmp_path / "[组] 莉可丽丝 Lycoris Recoil S01"
    show_dir.mkdir()
    (show_dir / "莉可丽丝 S01E01.mkv").write_bytes(b"x")
    (show_dir / "莉可丽丝 S01E02.mkv").write_bytes(b"x")
    return tmp_path
