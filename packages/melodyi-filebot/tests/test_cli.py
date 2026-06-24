"""CLI 测试"""

import json
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from melodyi_filebot.cli import cli


class TestCliSearch:
    """search 子命令测试"""

    def test_search_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "query" in result.output

    def test_search_tv(self):
        from melodyi_filebot.models import CandidateSummary
        cands = [CandidateSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス",
            year=2022, overview_length=50, media_type="tv",
        )]
        with patch("melodyi_filebot.cli.tmdb.search", return_value=cands):
            runner = CliRunner()
            result = runner.invoke(cli, ["search", "莉可丽丝", "--type", "tv"])
        assert result.exit_code == 0
        assert "莉可丽丝" in result.output

    def test_search_no_results(self):
        with patch("melodyi_filebot.cli.tmdb.search", return_value=[]):
            runner = CliRunner()
            result = runner.invoke(cli, ["search", "不存在的剧"])
        assert result.exit_code == 0
        assert "未找到" in result.output or "0" in result.output


class TestCliFetchSummary:
    """fetch-summary 子命令测试"""

    def test_fetch_summary(self, tmdb_show_detail):
        from melodyi_filebot.models import ShowSummary, SeasonSummary
        s = ShowSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス",
            year=2022, total_seasons=2, total_episodes=19,
            overview_available=True, overview_length=100,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=13)],
            episode_groups=[],
        )
        with patch("melodyi_filebot.cli.tmdb.get_show_summary", return_value=s):
            runner = CliRunner()
            result = runner.invoke(cli, ["fetch-summary", "46260"])
        assert result.exit_code == 0
        assert "莉可丽丝" in result.output
        # 不应输出完整 overview 原文（摘要只含 length）
        assert "overview_length" in result.output or "19" in result.output

    def test_fetch_summary_season_only_skips_show(self):
        """指定 --season 时只拉取该季集列表，不搜索整剧"""
        from melodyi_filebot.models import EpisodeBrief
        eps = [
            EpisodeBrief(episode_number=1, name="第一集", overview_length=50, runtime=24),
            EpisodeBrief(episode_number=2, name="第二集", overview_length=0, runtime=None),
        ]
        runner = CliRunner()
        with patch("melodyi_filebot.cli.tmdb.get_season_episodes", return_value=eps) as mock_eps, \
             patch("melodyi_filebot.cli.tmdb.get_show_summary") as mock_show:
            result = runner.invoke(cli, ["fetch-summary", "46260", "--season", "1"])
        assert result.exit_code == 0
        # 只拉季集，不搜整剧
        mock_eps.assert_called_once_with(46260, 1, language="zh-CN")
        mock_show.assert_not_called()
        # 输出含表头解释
        assert "时长" in result.output
        assert "简介长度" in result.output
        # 有 runtime 的集显示分钟数，无 runtime 显示缺失说明（不是 'runtime=未知'）
        assert "24" in result.output
        assert "无数据" in result.output
        assert "runtime=未知" not in result.output
        # overview_len 单元格只显示数字，不含 'overview_len=' 这种英文标签
        assert "overview_len=" not in result.output

    def test_fetch_summary_show_only_when_no_season(self):
        """不带 --season 时输出整剧摘要（不变更原行为）"""
        from melodyi_filebot.models import ShowSummary, SeasonSummary
        s = ShowSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス",
            year=2022, total_seasons=1, total_episodes=2,
            overview_available=True, overview_length=100,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=2)],
            episode_groups=[],
        )
        with patch("melodyi_filebot.cli.tmdb.get_show_summary", return_value=s):
            runner = CliRunner()
            result = runner.invoke(cli, ["fetch-summary", "46260"])
        assert result.exit_code == 0
        assert "莉可丽丝" in result.output


from pathlib import Path


class TestCliAnalyze:
    """analyze 子命令测试"""

    def test_analyze_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "path" in result.output

    def test_analyze_prints_tree(self, tmp_path):
        (tmp_path / "a.mkv").write_bytes(b"x")
        (tmp_path / "Season 1").mkdir()
        (tmp_path / "Season 1" / "ep01.mkv").write_bytes(b"x")
        with patch("melodyi_filebot.cli.analyze_path") as mock_analyze:
            from melodyi_filebot.models import PathAnalysis, TreeNode
            mock_analyze.return_value = PathAnalysis(
                root=str(tmp_path), truncated=False,
                total_files=2, total_videos=2, total_dirs=1, max_depth=2,
                tree=TreeNode(name=tmp_path.name, type="dir", path=str(tmp_path),
                              video_count=2, children=[]),
            )
            runner = CliRunner()
            result = runner.invoke(cli, ["analyze", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["truncated"] is False
        assert data["total_videos"] == 2

    def test_analyze_default_text_output(self, tmp_path):
        """默认（不加 --json）输出树状文本，首层显示绝对路径"""
        with patch("melodyi_filebot.cli.analyze_path") as mock_analyze:
            from melodyi_filebot.models import PathAnalysis, TreeNode
            mock_analyze.return_value = PathAnalysis(
                root=str(tmp_path), truncated=False,
                total_files=1, total_videos=1, total_dirs=0, max_depth=1,
                tree=TreeNode(name="movie.mp4", type="file", path=str(tmp_path / "movie.mp4"),
                              is_video=True, duration_seconds=5400.0),
            )
            runner = CliRunner()
            result = runner.invoke(cli, ["analyze", str(tmp_path)])
        assert result.exit_code == 0
        # 首层绝对路径
        assert str(tmp_path / "movie.mp4") in result.output
        # 时长为时分秒
        assert "(01:30:00)" in result.output
        # 不应是 JSON
        assert result.output.lstrip()[0] != "{"

    def test_analyze_truncated_summary(self, tmp_path):
        with patch("melodyi_filebot.cli.analyze_path") as mock_analyze:
            from melodyi_filebot.models import PathAnalysis
            mock_analyze.return_value = PathAnalysis(
                root=str(tmp_path), truncated=True,
                total_files=6000, total_videos=6000, max_depth=6,
                warnings=["文件总数 6000 超过 5000，数量过多"],
                by_ext={".mkv": 6000},
            )
            runner = CliRunner()
            result = runner.invoke(cli, ["analyze", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["truncated"] is True
        assert data["tree"] is None
        assert data["by_ext"][".mkv"] == 6000


class TestCliBuildPlan:
    """build-plan 子命令测试"""

    def test_build_plan_tv(self, tmp_path, tmdb_show_detail):
        from melodyi_filebot.models import ShowSummary, SeasonSummary
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        (show_dir / "莉可丽丝 S01E01.mkv").write_bytes(b"x")
        s = ShowSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス",
            year=2022, total_seasons=1, total_episodes=13,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=13)],
        )
        with patch("melodyi_filebot.cli.tmdb.get_show_summary", return_value=s):
            runner = CliRunner()
            plan_path = str(tmp_path / "plan.json")
            result = runner.invoke(cli, [
                "build-plan", "--show-id", "46260",
                "--source", str(show_dir), "--dest", str(tmp_path / "dest"),
                "--out", plan_path,
            ])
        assert result.exit_code == 0, result.output
        plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
        assert any(op["type"] == "move" for op in plan["operations"])


class TestCliExecuteAndUndo:
    """execute-plan 与 undo 测试"""

    def test_execute_and_undo(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        plan_path = str(tmp_path / "plan.json")
        snap_path = str(tmp_path / "snap.json")
        plan = {
            "operations": [
                {"type": "mkdir", "path": str(tmp_path / "dest" / "Show")},
                {"type": "move", "source": str(f), "path": str(tmp_path / "dest" / "Show" / "a.mkv")},
            ],
            "spec_applied": "standard",
            "warnings": [],
        }
        Path(plan_path).write_text(json.dumps(plan), encoding="utf-8")

        runner = CliRunner()
        # dry-run
        r1 = runner.invoke(cli, ["execute-plan", "--plan", plan_path])
        assert r1.exit_code == 0
        assert "dry-run" in r1.output
        assert f.exists()
        # execute
        r2 = runner.invoke(cli, ["execute-plan", "--plan", plan_path, "--execute", "--snapshot", snap_path])
        assert r2.exit_code == 0
        assert not f.exists()
        assert (tmp_path / "dest" / "Show" / "a.mkv").exists()
        # undo
        r3 = runner.invoke(cli, ["undo", snap_path])
        assert r3.exit_code == 0
        assert f.exists()


class TestExecuteDefaultSnapshot:
    """--execute 不指定 --snapshot 时的默认日志行为"""

    def _write_plan(self, tmp_path, src_file, target):
        plan = {
            "operations": [
                {"type": "mkdir", "path": str(target.parent)},
                {"type": "move", "source": str(src_file), "path": str(target)},
            ],
            "spec_applied": "standard",
            "warnings": [],
        }
        plan_path = tmp_path / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        return plan_path

    def test_execute_writes_default_snapshot(self, tmp_path, monkeypatch):
        """--execute 无 --snapshot 时，默认写到 SNAPSHOTS_DIR/<stem>.snapshot.json"""
        import melodyi_filebot.config as fbconfig
        snaps_dir = tmp_path / "snapshots"
        monkeypatch.setattr(fbconfig, "SNAPSHOTS_DIR", snaps_dir)

        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        target = tmp_path / "dest" / "Show" / "a.mkv"
        plan_path = self._write_plan(tmp_path, f, target)

        runner = CliRunner()
        result = runner.invoke(cli, ["execute-plan", "--plan", str(plan_path), "--execute"])
        assert result.exit_code == 0, result.output
        # 默认 snapshot 已写入
        default_snap = snaps_dir / "plan.snapshot.json"
        assert default_snap.exists()
        # 执行确实发生
        assert not f.exists()
        assert target.exists()
        # 输出提示路径与 undo 用法
        assert str(default_snap) in result.output
        assert "undo" in result.output

    def test_default_snapshot_is_undoable(self, tmp_path, monkeypatch):
        """默认 snapshot 可用于 undo 回滚"""
        import melodyi_filebot.config as fbconfig
        snaps_dir = tmp_path / "snapshots"
        monkeypatch.setattr(fbconfig, "SNAPSHOTS_DIR", snaps_dir)

        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        target = tmp_path / "dest" / "Show" / "a.mkv"
        plan_path = self._write_plan(tmp_path, f, target)

        runner = CliRunner()
        runner.invoke(cli, ["execute-plan", "--plan", str(plan_path), "--execute"])
        default_snap = str(snaps_dir / "plan.snapshot.json")
        assert Path(default_snap).exists()
        # undo
        r = runner.invoke(cli, ["undo", default_snap])
        assert r.exit_code == 0
        assert f.exists()

    def test_dry_run_writes_no_snapshot(self, tmp_path, monkeypatch):
        """dry-run 不写 snapshot"""
        import melodyi_filebot.config as fbconfig
        snaps_dir = tmp_path / "snapshots"
        monkeypatch.setattr(fbconfig, "SNAPSHOTS_DIR", snaps_dir)

        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        target = tmp_path / "dest" / "Show" / "a.mkv"
        plan_path = self._write_plan(tmp_path, f, target)

        runner = CliRunner()
        result = runner.invoke(cli, ["execute-plan", "--plan", str(plan_path)])
        assert result.exit_code == 0
        assert not snaps_dir.exists() or not any(snaps_dir.iterdir())
        # dry-run 不应改动文件系统
        assert f.exists()


class TestBuildPlanSeason:
    """build-plan --season 季提示测试"""

    def test_season_flag_routes_files_to_hint_season(self, tmp_path):
        from melodyi_filebot.models import ShowSummary, SeasonSummary
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        (show_dir / "Amagami [01].mkv").write_bytes(b"x")
        s = ShowSummary(
            tmdb_id=1, title="剧", original_title="x", year=2020,
            total_seasons=2, total_episodes=24,
            seasons=[
                SeasonSummary(season_number=1, name="S1", episode_count=12),
                SeasonSummary(season_number=2, name="S2", episode_count=12),
            ],
        )
        with patch("melodyi_filebot.cli.tmdb.get_show_summary", return_value=s):
            runner = CliRunner()
            plan_path = str(tmp_path / "plan.json")
            result = runner.invoke(cli, [
                "build-plan", "--show-id", "1", "--season", "2",
                "--source", str(show_dir), "--dest", str(tmp_path / "dest"),
                "--out", plan_path,
            ])
        assert result.exit_code == 0, result.output
        plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
        moves = [op for op in plan["operations"] if op["type"] == "move"]
        assert moves
        assert all("Season 02" in op["path"] for op in moves)
        assert all("S02E01" in op["path"] for op in moves)

    def test_season_flag_rejected_for_movie(self, tmp_path):
        """--season 仅适用于剧集，电影用应报错"""
        src = tmp_path / "src"
        src.mkdir()
        (src / "m.mkv").write_bytes(b"x")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "build-plan", "--movie-id", "1", "--season", "2",
            "--source", str(src), "--dest", str(tmp_path / "dest"),
        ])
        assert result.exit_code != 0
        assert "剧集" in result.output or "show" in result.output.lower()


class TestDraftMapAndOverride:
    """draft-map + build-plan --map 工作流测试"""

    def test_draft_map_tv_writes_mapping(self, tmp_path):
        from melodyi_filebot.models import ShowSummary, SeasonSummary
        src = tmp_path / "src"
        src.mkdir()
        (src / "Show S02E01.mkv").write_bytes(b"x")
        (src / "unknown.mkv").write_bytes(b"x")
        runner = CliRunner()
        out_path = str(tmp_path / "map.json")
        result = runner.invoke(cli, [
            "draft-map", "--show-id", "46260", "--source", str(src),
            "--season", "2", "--out", out_path,
        ])
        assert result.exit_code == 0, result.output
        data = json.loads(Path(out_path).read_text(encoding="utf-8"))
        assert data["media_type"] == "tv"
        assert data["tmdb_id"] == 46260
        assert len(data["mappings"]) == 2
        # 显式季标记保留，未知项 episode 为 None
        eps = {m["file"]: m for m in data["mappings"]}
        s02 = next(v for k, v in eps.items() if "S02E01" in k)
        assert s02["season"] == 2 and s02["episode"] == 1
        unk = next(v for k, v in eps.items() if "unknown" in k)
        assert unk["episode"] is None

    def test_build_plan_map_override(self, tmp_path):
        """draft-map 生成 → 编辑 → build-plan --map 构建"""
        from melodyi_filebot.models import ShowSummary, SeasonSummary
        src = tmp_path / "src"
        src.mkdir()
        # 文件名无意义，靠映射指定季/集
        (src / "随便.mkv").write_bytes(b"x")
        show = ShowSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス", year=2022,
            total_seasons=2, total_episodes=19,
            seasons=[SeasonSummary(season_number=2, name="S2", episode_count=12)],
        )
        # 写一份已编辑的映射：随便.mkv → S02E05
        map_path = tmp_path / "map.json"
        map_path.write_text(json.dumps({
            "media_type": "tv", "tmdb_id": 46260, "language": "zh-CN",
            "mappings": [
                {"file": str(src / "随便.mkv"), "season": 2, "episode": 5,
                 "episode_end": None, "part": None},
            ],
        }), encoding="utf-8")

        with patch("melodyi_filebot.cli.tmdb.get_show_summary", return_value=show):
            runner = CliRunner()
            plan_path = str(tmp_path / "plan.json")
            result = runner.invoke(cli, [
                "build-plan", "--map", str(map_path),
                "--dest", str(tmp_path / "dest"), "--out", plan_path,
            ])
        assert result.exit_code == 0, result.output
        plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
        assert plan["spec_applied"] == "override"
        moves = [op for op in plan["operations"] if op["type"] == "move"]
        assert len(moves) == 1
        assert "Season 02" in moves[0]["path"]
        assert "S02E05" in moves[0]["path"]

    def test_build_plan_map_conflicts_with_source(self, tmp_path):
        """--map 与 --source 互斥"""
        map_path = tmp_path / "map.json"
        map_path.write_text("{}", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "build-plan", "--map", str(map_path), "--source", str(tmp_path),
            "--dest", str(tmp_path / "dest"),
        ])
        assert result.exit_code != 0

    def test_build_plan_auto_requires_source(self, tmp_path):
        """自动模式缺 --source 应报错"""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "build-plan", "--show-id", "1", "--dest", str(tmp_path / "dest"),
        ])
        assert result.exit_code != 0
        assert "source" in result.output.lower() or "map" in result.output.lower()
