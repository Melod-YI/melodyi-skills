"""sync_skills.py 的单元测试。

覆盖：
- 配置解析优先级（CLI > env > 本地配置 > 默认配置 > 内置兜底）
- 路径展开（~ 与 ${HOME}）
- 同步行为端到端
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sync_skills import (
    DEFAULT_WORKSPACE_ROOT,
    ENV_VAR,
    resolve_workspace_root,
    sync_skill,
)


@pytest.fixture()
def scripts_dir(tmp_path: Path) -> Path:
    """模拟 scripts/ 目录，用于放置配置文件。"""
    d = tmp_path / "scripts"
    d.mkdir()
    return d


def write_yaml(path: Path, workspace_root: str) -> None:
    path.write_text(f"workspace_root: {workspace_root}\n", encoding="utf-8")


# ---------- 配置解析优先级 ----------


def test_default_when_no_config(scripts_dir: Path) -> None:
    """无任何配置/环境变量/CLI 参数时，使用内置默认值。"""
    got = resolve_workspace_root(
        cli_value=None, env_value=None, scripts_dir=scripts_dir
    )
    assert got == Path(os.path.expanduser(DEFAULT_WORKSPACE_ROOT)).resolve()


def test_committed_config_used(scripts_dir: Path) -> None:
    """提交的 sync-skills.yaml 提供默认值。"""
    write_yaml(scripts_dir / "sync-skills.yaml", "/abs/committed")
    got = resolve_workspace_root(None, None, scripts_dir)
    assert got == Path("/abs/committed").resolve()


def test_local_overrides_committed(scripts_dir: Path) -> None:
    """本地 sync-skills.local.yaml 覆盖提交配置。"""
    write_yaml(scripts_dir / "sync-skills.yaml", "/abs/committed")
    write_yaml(scripts_dir / "sync-skills.local.yaml", "/abs/local")
    got = resolve_workspace_root(None, None, scripts_dir)
    assert got == Path("/abs/local").resolve()


def test_env_overrides_configs(scripts_dir: Path) -> None:
    """环境变量优先于配置文件。"""
    write_yaml(scripts_dir / "sync-skills.yaml", "/abs/committed")
    write_yaml(scripts_dir / "sync-skills.local.yaml", "/abs/local")
    got = resolve_workspace_root(None, "/abs/env", scripts_dir)
    assert got == Path("/abs/env").resolve()


def test_cli_overrides_all(scripts_dir: Path) -> None:
    """CLI 参数优先级最高。"""
    write_yaml(scripts_dir / "sync-skills.yaml", "/abs/committed")
    write_yaml(scripts_dir / "sync-skills.local.yaml", "/abs/local")
    got = resolve_workspace_root("/abs/cli", "/abs/env", scripts_dir)
    assert got == Path("/abs/cli").resolve()


def test_env_var_name_constant() -> None:
    """环境变量名符合约定。"""
    assert ENV_VAR == "MELODYI_SYNC_WORKSPACE_ROOT"


# ---------- 路径展开 ----------


def test_tilde_expansion(scripts_dir: Path) -> None:
    """配置中的 ~ 被展开为家目录。"""
    write_yaml(scripts_dir / "sync-skills.yaml", "~/foo/bar")
    got = resolve_workspace_root(None, None, scripts_dir)
    assert got == Path(os.path.expanduser("~/foo/bar"))


def test_home_var_expansion(scripts_dir: Path) -> None:
    """配置中的 ${HOME} 被展开。"""
    write_yaml(scripts_dir / "sync-skills.yaml", "${HOME}/foo/bar")
    got = resolve_workspace_root(None, None, scripts_dir)
    expected = Path(os.path.expandvars("${HOME}/foo/bar"))
    assert got == expected


def test_default_uses_melodyi_skills_workspace(scripts_dir: Path) -> None:
    """默认值即用户要求的 ~/.melodyi-skills/workspace。"""
    got = resolve_workspace_root(None, None, scripts_dir)
    assert got == Path(os.path.expanduser("~/.melodyi-skills/workspace"))


# ---------- 同步行为端到端 ----------


def test_sync_skill_copies_into_workspace(tmp_path: Path) -> None:
    """单个 skill 被复制到 <workspace_root>/<skill>-workspace/.claude/skills/<skill>。"""
    skills_dir = tmp_path / "skills"
    skill_src = skills_dir / "demo-skill"
    (skill_src / "nested").mkdir(parents=True)
    (skill_src / "SKILL.md").write_text("hello", encoding="utf-8")
    (skill_src / "nested" / "data.txt").write_text("data", encoding="utf-8")

    workspace_root = tmp_path / "ws"
    target = workspace_root / "demo-skill-workspace" / ".claude" / "skills" / "demo-skill"

    sync_skill(skill_src, workspace_root)
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "hello"
    assert (target / "nested" / "data.txt").read_text(encoding="utf-8") == "data"


def test_sync_skill_replaces_existing_target(tmp_path: Path) -> None:
    """目标已存在时先清空再复制，避免残留旧文件。"""
    skills_dir = tmp_path / "skills"
    skill_src = skills_dir / "demo-skill"
    skill_src.mkdir(parents=True)
    (skill_src / "SKILL.md").write_text("new", encoding="utf-8")

    workspace_root = tmp_path / "ws"
    target = workspace_root / "demo-skill-workspace" / ".claude" / "skills" / "demo-skill"
    target.mkdir(parents=True)
    (target / "stale.txt").write_text("stale", encoding="utf-8")  # 旧残留

    sync_skill(skill_src, workspace_root)
    assert not (target / "stale.txt").exists()
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "new"
