"""fixture 库可用性测试

验证 gen-fixtures.py 生成的极小用例：
- 结构与 manifest 一致（视频/伴生数量）
- 真实 ffprobe 能读出期望时长（端到端验证 analyze CLI 能拿到时间信息）

这些测试依赖入库的 fixture（packages/melodyi-filebot/tests/fixtures/），
调用真实 ffprobe（不 mock），但不调任何网络 API。
"""

import json
import shutil
from pathlib import Path

import pytest

from melodyi_filebot import structure

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def gundam_fixture() -> Path:
    """高达SEED 重制版 fixture 顶层目录（含 manifest.json + 源目录名一层）"""
    p = FIXTURES_DIR / "gundam-seed-hd"
    if not p.is_dir():
        pytest.skip(f"fixture 未生成: {p}（用 scripts/gen-fixtures.py 生成）")
    return p


def _case_root(fixture_dir: Path) -> Path:
    """fixture 下的用例根目录（源目录名那一层，manifest.json 之外的唯一子目录）"""
    return next(p for p in fixture_dir.iterdir() if p.is_dir())


def test_gundam_manifest_matches_filesystem(gundam_fixture):
    """manifest 记录的视频/伴生数与文件系统一致"""
    manifest = json.loads(
        (gundam_fixture / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["videos"]) == 98
    assert len(manifest["companions"]) == 98
    assert manifest["skipped"] == []
    case_root = _case_root(gundam_fixture)
    assert case_root.name == manifest["case_root"]  # 源目录名一层
    # 每个视频文件确实存在（rel 相对源目录根）
    for v in manifest["videos"]:
        assert (case_root / v["rel"]).is_file()
    # 抽样时长合理（~24 分钟）
    assert 1300 < manifest["videos"][0]["duration_seconds"] < 1500


def test_gundam_analyze_real_ffprobe(gundam_fixture, tmp_path):
    """端到端：copytree 到一次性 tmp_path，跑 analyze 真实 ffprobe 取时长

    演示测试工作流——fixture 入库为只读模板，测试时 copytree 到 tmp_path
    隔离使用，跑完即弃。
    """
    # copytree Season 1 到一次性目录（48 视频 + 48 字幕，~2.5MB）
    src_season = _case_root(gundam_fixture) / "Season 1"
    dst = tmp_path / "Season 1"
    shutil.copytree(src_season, dst)

    result = structure.analyze_path(str(dst))  # 默认真实 ffprobe
    assert result.truncated is False
    assert result.total_videos == 48

    # 找第一个视频节点，断言真实 ffprobe 读出 ~24 分钟
    def first_video(node):
        if node.is_video:
            return node
        for c in node.children or []:
            v = first_video(c)
            if v:
                return v
        return None

    vid = first_video(result.tree)
    assert vid is not None
    assert vid.duration_seconds is not None
    assert 1300 < vid.duration_seconds < 1500  # ~1433 秒
