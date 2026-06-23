"""fsops 测试"""

import json
from pathlib import Path

import pytest

from melodyi_filebot import fsops
from melodyi_filebot.planner import VIDEO_EXTS


class TestScan:
    """scan_video_files 测试"""

    def test_scan_finds_videos(self, tmp_path):
        (tmp_path / "a.mkv").write_bytes(b"x")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.mp4").write_bytes(b"x")
        (tmp_path / "c.txt").write_text("nope")
        files = fsops.scan_video_files(str(tmp_path))
        assert len(files) == 2
        assert all(Path(f).suffix in VIDEO_EXTS for f in files)

    def test_scan_recursive(self, tmp_path):
        (tmp_path / "s1").mkdir()
        (tmp_path / "s1" / "s2").mkdir()
        (tmp_path / "s1" / "s2" / "deep.mkv").write_bytes(b"x")
        files = fsops.scan_video_files(str(tmp_path))
        assert len(files) == 1

    def test_scan_empty(self, tmp_path):
        assert fsops.scan_video_files(str(tmp_path)) == []

    def test_scan_missing_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            fsops.scan_video_files(str(tmp_path / "nope"))


from melodyi_filebot.models import BuildPlanResult, PlanOperation


class TestExecutePlan:
    """execute_plan 测试"""

    def test_dry_run_no_changes(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        dest = tmp_path / "dest"
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="mkdir", path=str(dest / "Show")),
                PlanOperation(type="move", source=str(f), path=str(dest / "Show" / "a.mkv")),
            ]
        )
        snapshot = fsops.execute_plan(plan, dry_run=True)
        # dry-run 不应改动文件系统
        assert f.exists()
        assert not (dest / "Show").exists()
        assert snapshot is None

    def test_execute_moves_file(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        dest = tmp_path / "dest" / "Show"
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="mkdir", path=str(dest)),
                PlanOperation(type="move", source=str(f), path=str(dest / "a.mkv")),
            ]
        )
        snapshot = fsops.execute_plan(plan, dry_run=False)
        assert not f.exists()
        assert (dest / "a.mkv").exists()
        assert snapshot is not None
        assert len(snapshot["operations"]) == 2

    def test_execute_writes_snapshot_file(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        dest = tmp_path / "dest" / "Show"
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="mkdir", path=str(dest)),
                PlanOperation(type="move", source=str(f), path=str(dest / "a.mkv")),
            ]
        )
        snapshot = fsops.execute_plan(plan, dry_run=False, snapshot_path=str(tmp_path / "snap.json"))
        assert (tmp_path / "snap.json").exists()
        data = json.loads((tmp_path / "snap.json").read_text(encoding="utf-8"))
        assert "operations" in data

    def test_dry_run_detects_conflict(self, tmp_path):
        """目标已存在文件时 dry-run 报冲突"""
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        dest = tmp_path / "dest" / "Show"
        dest.mkdir(parents=True)
        (dest / "a.mkv").write_bytes(b"existing")
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="move", source=str(f), path=str(dest / "a.mkv")),
            ]
        )
        with pytest.raises(FileExistsError):
            fsops.execute_plan(plan, dry_run=True)

    def test_dry_run_detects_missing_source(self, tmp_path):
        dest = tmp_path / "dest" / "Show"
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="move", source=str(tmp_path / "ghost.mkv"), path=str(dest / "a.mkv")),
            ]
        )
        with pytest.raises(FileNotFoundError):
            fsops.execute_plan(plan, dry_run=True)
