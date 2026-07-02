#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""melodyi-skills 同步脚本。

将仓库 skills/ 下每个 skill 同步到隔离 workspace，供在受控环境下验证 skill 功能。

目标 workspace 根目录按以下优先级解析（符合项目约定 CLI > env > 配置 > 默认）：
    1. CLI 参数 --workspace-root
    2. 环境变量 MELODYI_SYNC_WORKSPACE_ROOT
    3. scripts/sync-skills.local.yaml（本地覆盖，gitignore）
    4. scripts/sync-skills.yaml（仓库默认配置）
    5. 内置默认值 ~/.melodyi-skills/workspace

用法：
    python scripts/sync_skills.py [--workspace-root PATH]
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

import yaml

# ---------- 常量 ----------

#: 内置默认 workspace 根目录。
DEFAULT_WORKSPACE_ROOT = "~/.melodyi-skills/workspace"
#: 仓库内提交的默认配置文件名（与本脚本同目录）。
CONFIG_FILENAME = "sync-skills.yaml"
#: 本地覆盖配置文件名（gitignore，不提交）。
LOCAL_CONFIG_FILENAME = "sync-skills.local.yaml"
#: 控制 workspace_root 的环境变量名。
ENV_VAR = "MELODYI_SYNC_WORKSPACE_ROOT"

logger = logging.getLogger("sync_skills")


# ---------- 路径工具 ----------


def expand_path(value: str) -> Path:
    """展开路径中的 ~ 与 ${HOME} 等变量，返回绝对 Path。"""
    expanded = os.path.expandvars(os.path.expanduser(value))
    return Path(expanded).resolve()


# ---------- 配置解析 ----------


def _load_yaml(path: Path) -> dict:
    """读取 YAML 配置；文件不存在或为空时返回空 dict。"""
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        logger.warning("配置文件 %s 解析失败，已忽略: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        logger.warning("配置文件 %s 顶层不是映射，已忽略", path)
        return {}
    return data


def resolve_workspace_root(
    cli_value: str | None,
    env_value: str | None,
    scripts_dir: Path,
) -> Path:
    """按优先级解析 workspace 根目录。

    优先级：CLI > env > 本地配置 > 默认配置 > 内置默认。
    """
    if cli_value:
        logger.info("workspace_root 来源: CLI 参数 -> %s", cli_value)
        return expand_path(cli_value)

    if env_value:
        logger.info("workspace_root 来源: 环境变量 %s -> %s", ENV_VAR, env_value)
        return expand_path(env_value)

    local_cfg = _load_yaml(scripts_dir / LOCAL_CONFIG_FILENAME)
    if "workspace_root" in local_cfg:
        value = str(local_cfg["workspace_root"])
        logger.info("workspace_root 来源: 本地配置 %s -> %s", LOCAL_CONFIG_FILENAME, value)
        return expand_path(value)

    committed_cfg = _load_yaml(scripts_dir / CONFIG_FILENAME)
    if "workspace_root" in committed_cfg:
        value = str(committed_cfg["workspace_root"])
        logger.info("workspace_root 来源: 默认配置 %s -> %s", CONFIG_FILENAME, value)
        return expand_path(value)

    logger.info("workspace_root 来源: 内置默认 -> %s", DEFAULT_WORKSPACE_ROOT)
    return expand_path(DEFAULT_WORKSPACE_ROOT)


# ---------- 同步逻辑 ----------


def sync_skill(skill_path: Path, workspace_root: Path) -> None:
    """将单个 skill 目录同步到 <workspace_root>/<skill>-workspace/.claude/skills/<skill>。

    目标已存在时先清空再复制，避免残留旧文件。
    """
    skill_name = skill_path.name
    workspace_path = workspace_root / f"{skill_name}-workspace"
    target_skill_dir = workspace_path / ".claude" / "skills" / skill_name

    logger.info("处理 skill: %s", skill_name)
    logger.info("  源路径: %s", skill_path)
    logger.info("  目标 workspace: %s", workspace_path)
    logger.info("  目标 skill 目录: %s", target_skill_dir)

    workspace_path.mkdir(parents=True, exist_ok=True)
    (workspace_path / ".claude" / "skills").mkdir(parents=True, exist_ok=True)

    if target_skill_dir.exists():
        logger.info("  -> 清空已存在的目标目录: %s", target_skill_dir)
        shutil.rmtree(target_skill_dir)

    logger.info("  -> 复制 %s 到目标目录", skill_name)
    shutil.copytree(skill_path, target_skill_dir)
    logger.info("  -> 完成: %s", skill_name)


def sync_all(skills_dir: Path, workspace_root: Path) -> int:
    """遍历 skills/ 下每个子目录并同步。返回同步的 skill 数量。"""
    logger.info("=== Skills 同步脚本 ===")
    logger.info("Skills 目录: %s", skills_dir)
    logger.info("Workspace 根目录: %s", workspace_root)

    if not skills_dir.is_dir():
        logger.error("错误: skills 目录不存在: %s", skills_dir)
        raise SystemExit(1)

    count = 0
    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir():
            continue
        try:
            sync_skill(skill_path, workspace_root)
            count += 1
        except Exception as exc:  # noqa: BLE001 单 skill 失败不中断整体
            logger.error("同步 skill 失败，跳过: %s -> %s", skill_path.name, exc)

    logger.info("=== 同步完成，共 %d 个 skill ===", count)
    return count


# ---------- CLI ----------


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="同步 skills 到隔离 workspace")
    parser.add_argument(
        "--workspace-root",
        default=None,
        help="目标 workspace 根目录（覆盖配置文件与环境变量）",
    )
    args = parser.parse_args(argv)

    scripts_dir = Path(__file__).resolve().parent
    repo_root = scripts_dir.parent
    skills_dir = repo_root / "skills"

    workspace_root = resolve_workspace_root(
        cli_value=args.workspace_root,
        env_value=os.environ.get(ENV_VAR),
        scripts_dir=scripts_dir,
    )

    sync_all(skills_dir, workspace_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
