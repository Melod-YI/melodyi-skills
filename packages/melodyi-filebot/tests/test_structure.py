"""structure（路径分析）测试"""

import pytest

from melodyi_filebot import structure
from melodyi_filebot.planner import VIDEO_EXTS


def fake_probe(seconds_by_name):
    """构造一个按文件名返回固定时长的 probe 函数（避免真实 ffprobe）"""

    def _probe(path):
        name = str(path).rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return seconds_by_name.get(name)

    return _probe


class TestFormatDuration:
    """format_duration 测试"""

    def test_hms(self):
        assert structure.format_duration(24 * 60 + 13) == "00:24:13"

    def test_with_hours(self):
        assert structure.format_duration(2 * 3600 + 5 * 60 + 1) == "02:05:01"

    def test_rounds_seconds(self):
        assert structure.format_duration(23.7) == "00:00:24"

    def test_none(self):
        assert structure.format_duration(None) is None


class TestAnalyzeNormalTree:
    """正常目录：返回完整树，视频带时长，目录累计视频数"""

    def test_tree_structure_and_video_count(self, tmp_path):
        # root(深度1)
        #   ├ a.mkv            视频
        #   ├ note.txt
        #   └ Season 1/        深度2
        #       ├ ep01.mkv     视频
        #       └ ep02.mkv     视频
        (tmp_path / "a.mkv").write_bytes(b"x")
        (tmp_path / "note.txt").write_text("nope")
        s1 = tmp_path / "Season 1"
        s1.mkdir()
        (s1 / "ep01.mkv").write_bytes(b"x")
        (s1 / "ep02.mkv").write_bytes(b"x")

        result = structure.analyze_path(
            str(tmp_path),
            probe=fake_probe({"a.mkv": 100.0, "ep01.mkv": 24 * 60 + 13, "ep02.mkv": None}),
        )

        assert result.truncated is False
        assert result.total_files == 4
        assert result.total_videos == 3
        assert result.max_depth == 2
        assert result.warnings == []

        tree = result.tree
        assert tree.type == "dir"
        assert tree.video_count == 3  # root 累计
        children = {c.name: c for c in tree.children}
        assert children["a.mkv"].is_video is True
        assert children["a.mkv"].duration_seconds == 100.0
        assert children["note.txt"].is_video is False
        assert children["note.txt"].duration_seconds is None
        season = children["Season 1"]
        assert season.type == "dir"
        assert season.video_count == 2  # 子目录累计
        ep_children = {c.name: c for c in season.children}
        assert ep_children["ep01.mkv"].duration_seconds == 24 * 60 + 13
        assert ep_children["ep02.mkv"].duration_seconds is None  # probe 返回 None

    def test_single_file_video(self, tmp_path):
        f = tmp_path / "movie.mp4"
        f.write_bytes(b"x")
        result = structure.analyze_path(str(f), probe=fake_probe({"movie.mp4": 90 * 60}))
        assert result.truncated is False
        assert result.total_files == 1
        assert result.total_videos == 1
        assert result.max_depth == 1
        assert result.tree.type == "file"
        assert result.tree.is_video is True
        assert result.tree.duration_seconds == 90 * 60

    def test_single_file_non_video(self, tmp_path):
        f = tmp_path / "readme.txt"
        f.write_text("x")
        result = structure.analyze_path(str(f), probe=fake_probe({}))
        assert result.total_videos == 0
        assert result.tree.is_video is False


class TestAnalyzeWarnings:
    """命中告警条件：只返回概要并停止，不构建详细树"""

    def test_depth_warning(self, tmp_path):
        # 构造深度 5 的目录链：root/a/b/c/d（root=1）
        d = tmp_path
        for name in ["a", "b", "c", "d"]:
            d = d / name
            d.mkdir()
        (d / "deep.mkv").write_bytes(b"x")

        result = structure.analyze_path(str(tmp_path), probe=fake_probe({}))
        assert result.truncated is True
        assert result.tree is None
        assert result.max_depth == 5
        assert any("深度" in w for w in result.warnings)
        assert result.total_files == 1

    def test_file_count_warning(self, tmp_path):
        # 6001 个文件超过 5000 阈值
        for i in range(6001):
            (tmp_path / f"f{i:05d}.mkv").write_bytes(b"x")

        result = structure.analyze_path(str(tmp_path), probe=fake_probe({}))
        assert result.truncated is True
        assert result.tree is None
        assert result.total_files == 6001
        assert any("超过" in w for w in result.warnings)
        # 概要应包含按扩展名统计
        assert result.by_ext.get(".mkv") == 6001

    def test_summary_by_depth_dirs(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b").mkdir()
        (tmp_path / "f.mkv").write_bytes(b"x")
        (tmp_path / "a" / "g.mkv").write_bytes(b"x")
        result = structure.analyze_path(str(tmp_path), probe=fake_probe({}))
        # 深度 3，未触发；这里用来验证 by_depth 字段在截断时存在即可——改用深链
        # 直接验证字段在非截断时为 None
        assert result.truncated is False
        assert result.by_depth is None


class TestAnalyzeErrors:
    def test_missing_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            structure.analyze_path(str(tmp_path / "nope"), probe=fake_probe({}))


class TestRenderText:
    """render_text 文本树渲染测试"""

    def _make(self, tmp_path):
        (tmp_path / "a.mkv").write_bytes(b"x")
        (tmp_path / "note.txt").write_text("nope")
        s1 = tmp_path / "Season 1"
        s1.mkdir()
        (s1 / "ep01.mkv").write_bytes(b"x")
        return structure.analyze_path(
            str(tmp_path),
            probe=fake_probe({"a.mkv": 100.0, "ep01.mkv": 24 * 60 + 13}),
        )

    def test_root_shows_abs_path_children_show_name_only(self, tmp_path):
        result = self._make(tmp_path)
        text = structure.render_text(result)
        # 首层是绝对路径
        assert str(tmp_path) in text
        # 子节点不重复显示完整绝对路径：ep01 出现但其所在行不应含 tmp_path 的父前缀
        ep_line = [ln for ln in text.splitlines() if "ep01.mkv" in ln][0]
        assert str(tmp_path) not in ep_line

    def test_video_duration_hms_and_dir_video_count(self, tmp_path):
        result = self._make(tmp_path)
        text = structure.render_text(result)
        assert "(00:24:13)" in text  # ep01 时长
        assert "[视频 2]" in text  # root 累计 2 个视频（a.mkv + ep01.mkv）

    def test_truncated_summary_no_tree(self, tmp_path):
        d = tmp_path
        for name in ["a", "b", "c", "d"]:
            d = d / name
            d.mkdir()
        (d / "deep.mkv").write_bytes(b"x")
        result = structure.analyze_path(str(tmp_path), probe=fake_probe({}))
        text = structure.render_text(result)
        assert "[告警]" in text
        assert "按扩展名" in text
        assert "deep.mkv" not in text  # 未展开完整树

    def test_single_file(self, tmp_path):
        f = tmp_path / "movie.mp4"
        f.write_bytes(b"x")
        result = structure.analyze_path(str(f), probe=fake_probe({"movie.mp4": 90 * 60}))
        text = structure.render_text(result)
        assert str(f) in text
        assert "(01:30:00)" in text


# VIDEO_EXTS 仅用于断言一致性
assert {".mkv", ".mp4"} <= VIDEO_EXTS


class TestProbeStreamDetails:
    """ffprobe 流信息探测（NFO streamdetails 用）"""

    def test_probe_returns_video_audio(self, monkeypatch):
        import json as _json
        from pathlib import Path

        fake_json = {
            "streams": [
                {"codec_name": "h264", "codec_type": "video", "width": 1920, "height": 1080,
                 "avg_frame_rate": "24000/1001", "duration": "1420.5",
                 "display_aspect_ratio": "16:9"},
                {"codec_name": "aac", "codec_type": "audio", "channels": 2, "sample_rate": "48000"},
            ]
        }

        class FakeProc:
            stdout = _json.dumps(fake_json)
            returncode = 0

        monkeypatch.setattr(structure.subprocess, "run", lambda *a, **k: FakeProc())
        sd = structure.probe_stream_details(Path("x.mkv"))
        assert sd is not None
        assert sd["video"]["codec"] == "h264"
        assert sd["video"]["width"] == 1920
        assert sd["video"]["duration_seconds"] == 1420  # float → int
        assert sd["video"]["framerate"] == "23.976"
        assert sd["audio"]["codec"] == "aac"
        assert sd["audio"]["channels"] == 2
        assert sd["audio"]["samplingrate"] == 48000

    def test_probe_returns_none_on_failure(self, monkeypatch):
        from pathlib import Path

        def _raise(*a, **k):
            raise FileNotFoundError("no ffprobe")

        monkeypatch.setattr(structure.subprocess, "run", _raise)
        assert structure.probe_stream_details(Path("x.mkv")) is None

    def test_probe_video_only(self, monkeypatch):
        import json as _json
        from pathlib import Path

        fake_json = {"streams": [
            {"codec_name": "h265", "codec_type": "video", "width": 1280, "height": 720,
             "avg_frame_rate": "24/1", "duration": "600"}]}

        class FakeProc:
            stdout = _json.dumps(fake_json)
            returncode = 0

        monkeypatch.setattr(structure.subprocess, "run", lambda *a, **k: FakeProc())
        sd = structure.probe_stream_details(Path("x.mkv"))
        assert "video" in sd and "audio" not in sd
        assert sd["video"]["framerate"] == "24"
