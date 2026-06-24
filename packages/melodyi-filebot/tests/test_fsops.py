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

    def test_scan_sorted(self, tmp_path):
        """扫描结果应为升序，保证计划稳定"""
        (tmp_path / "b.mkv").write_bytes(b"x")
        (tmp_path / "a.mkv").write_bytes(b"x")
        (tmp_path / "c.mkv").write_bytes(b"x")
        files = fsops.scan_video_files(str(tmp_path))
        assert files == sorted(files)


class TestFindCompanions:
    """find_companions 测试：发现视频的伴生文件（字幕等 sidecar）

    规则：同目录下、文件名以「视频 stem.」开头的非视频文件。
    """

    def test_same_stem_subtitle(self, tmp_path):
        """与视频同 stem 的字幕视为伴生"""
        (tmp_path / "Show S01E01.mkv").write_bytes(b"x")
        sub = tmp_path / "Show S01E01.ass"
        sub.write_text("x")
        comps = fsops.find_companions(str(tmp_path / "Show S01E01.mkv"))
        assert comps == [str(sub)]

    def test_language_tag_subtitle(self, tmp_path):
        """stem 后带语言 token 的字幕（.TC.ass）也视为伴生"""
        (tmp_path / "[G][Title][01][720p].mp4").write_bytes(b"x")
        tc = tmp_path / "[G][Title][01][720p].TC.ass"
        tc.write_text("x")
        plain = tmp_path / "[G][Title][01][720p].ass"
        plain.write_text("x")
        comps = fsops.find_companions(str(tmp_path / "[G][Title][01][720p].mp4"))
        assert set(comps) == {str(plain), str(tc)}

    def test_excludes_video_itself(self, tmp_path):
        """视频自身不被当伴生"""
        v = tmp_path / "Show S01E01.mkv"
        v.write_bytes(b"x")
        assert fsops.find_companions(str(v)) == []

    def test_excludes_other_videos(self, tmp_path):
        """同前缀的其他视频不当伴生"""
        (tmp_path / "Show S01E01.mkv").write_bytes(b"x")
        (tmp_path / "Show S01E01.alt.mp4").write_bytes(b"x")  # 另一视频
        comps = fsops.find_companions(str(tmp_path / "Show S01E01.mkv"))
        assert comps == []

    def test_excludes_partial_prefix_match(self, tmp_path):
        """stem 后非 '.' 的部分前缀匹配不算伴生

        Show S01E01 的 stem 不应 claim Show S01E01-part-1.ass（其后是 '-'）。
        """
        (tmp_path / "Show S01E01.mkv").write_bytes(b"x")
        (tmp_path / "Show S01E01-part-1.ass").write_text("x")
        comps = fsops.find_companions(str(tmp_path / "Show S01E01.mkv"))
        assert comps == []

    def test_missing_dir_returns_empty(self, tmp_path):
        """视频目录不存在时返回空列表（不抛异常）"""
        assert fsops.find_companions(str(tmp_path / "ghost" / "v.mkv")) == []

    def test_sorted(self, tmp_path):
        """结果升序，保证计划稳定"""
        (tmp_path / "Show S01E01.mkv").write_bytes(b"x")
        (tmp_path / "Show S01E01.b.ass").write_text("x")
        (tmp_path / "Show S01E01.a.ass").write_text("x")
        comps = fsops.find_companions(str(tmp_path / "Show S01E01.mkv"))
        assert comps == sorted(comps)


class TestCompanionExecuteAndUndo:
    """伴生文件执行与回滚集成测试"""

    def _plan(self, tmp_path):
        from melodyi_filebot.planner import build_plan_tv
        from melodyi_filebot.models import ShowSummary, SeasonSummary
        src = tmp_path / "src"
        src.mkdir()
        v = src / "Show S01E01.mkv"
        sub = src / "Show S01E01.ass"
        tc = src / "Show S01E01.TC.ass"
        v.write_bytes(b"v")
        sub.write_text("s")
        tc.write_text("t")
        show = ShowSummary(
            tmdb_id=1, title="Show", original_title="x", year=2020,
            total_seasons=1, total_episodes=1,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=1)],
        )
        return build_plan_tv(files=[str(v)], show=show, dest_root=str(tmp_path / "dest")), sub, tc

    def test_execute_moves_companions(self, tmp_path):
        plan, sub, tc = self._plan(tmp_path)
        fsops.execute_plan(plan, dry_run=False, snapshot_path=str(tmp_path / "snap.json"))
        # 字幕随视频改名后落到目标季目录
        dest_season = tmp_path / "dest" / "Show (2020) [tmdbid-1]" / "Season 01"
        assert (dest_season / "Show (2020) S01E01.ass").exists()
        assert (dest_season / "Show (2020) S01E01.TC.ass").exists()
        assert not sub.exists()
        assert not tc.exists()

    def test_undo_restores_companions(self, tmp_path):
        plan, sub, tc = self._plan(tmp_path)
        snap = fsops.execute_plan(plan, dry_run=False, snapshot_path=str(tmp_path / "snap.json"))
        fsops.undo(snap)
        # 回滚后伴生回到原位
        assert sub.exists()
        assert tc.exists()


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


class TestUndo:
    """undo 测试"""

    def test_undo_restores_original(self, tmp_path):
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
        assert not f.exists()
        fsops.undo(snapshot)
        # 回滚后源文件恢复，目标目录被清理（move 逆操作）
        assert f.exists()
        assert not (dest / "a.mkv").exists()

    def test_undo_from_file(self, tmp_path):
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
        snap_path = str(tmp_path / "snap.json")
        fsops.execute_plan(plan, dry_run=False, snapshot_path=snap_path)
        fsops.undo_from_file(snap_path)
        assert f.exists()
