"""pytest 公共 fixtures"""

import json
from pathlib import Path

import pytest


def pytest_addoption(parser):
    """添加 --run-integration 选项以启用真实 API 集成测试"""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="启用调用真实 TMDB API 的集成测试",
    )


def pytest_collection_modifyitems(config, items):
    """未指定 --run-integration 时，跳过标记为 integration 的测试"""
    if config.getoption("--run-integration"):
        return
    skip_integration = pytest.mark.skip(
        reason="集成测试默认跳过，加 --run-integration 启用（需真实 TMDB API key）"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


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
