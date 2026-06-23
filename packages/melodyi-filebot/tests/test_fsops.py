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
