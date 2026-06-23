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

    def test_fetch_summary_episodes_flag(self, tmdb_show_detail):
        from melodyi_filebot.models import ShowSummary, SeasonSummary, EpisodeBrief
        s = ShowSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス",
            year=2022, total_seasons=1, total_episodes=2,
            overview_available=True, overview_length=100,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=2)],
            episode_groups=[],
        )
        eps = [EpisodeBrief(episode_number=1, name="第一集", overview_length=50)]
        with patch("melodyi_filebot.cli.tmdb.get_show_summary", return_value=s), \
             patch("melodyi_filebot.cli.tmdb.get_season_episodes", return_value=eps):
            runner = CliRunner()
            result = runner.invoke(cli, ["fetch-summary", "46260", "--episodes", "1"])
        assert result.exit_code == 0
        assert "第一集" in result.output


from pathlib import Path


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
