"""把当前仓库 skills/ 下的 skill 增量链接到 cc-switch 与 Claude Code。

复刻 cc-switch 开发者模式的两层符号链接模式：
    ~/.cc-switch/skills/<name>   ->  仓库 skills/<name>
    ~/.claude/skills/<name>      ->  ~/.cc-switch/skills/<name>

增量处理：已正确链接的跳过；目标已存在（非指向本仓库源的符号链接、
或是 cc-switch 内置 skill 的真实目录如 docx/pdf）一律**不覆盖**，仅告警跳过。

Windows 上创建符号链接需要「开发者模式」开启（或管理员权限）。

用法：
    python scripts/link_to_cc_switch.py                 # 链接所有 skill（增量）
    python scripts/link_to_cc_switch.py --skill foo     # 只链接指定 skill（可多次）
    python scripts/link_to_cc_switch.py --dry-run       # 预览，不实际创建
    python scripts/link_to_cc_switch.py --unlink        # 移除本脚本创建的链接（幂等）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 仓库根：本脚本位于 <repo>/scripts/link_to_cc_switch.py
REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_SKILLS_DIR = REPO_ROOT / "skills"

# cc-switch 与 Claude Code 的 skills 目录默认值。
DEFAULT_CC_SWITCH_ROOT = Path.home() / ".cc-switch" / "skills"
DEFAULT_CLAUDE_ROOT = Path.home() / ".claude" / "skills"


def is_symlink_to(path: Path, target: Path) -> bool:
    """判断 path 是否是指向 target 的符号链接。"""
    if not path.is_symlink():
        return False
    try:
        return path.resolve(strict=False) == target.resolve(strict=False)
    except (OSError, RuntimeError):
        return False


def discover_skills(skills_dir: Path) -> list[str]:
    """扫描 skills/ 下含 SKILL.md 的子目录，返回 skill 名列表（有序）。"""
    if not skills_dir.is_dir():
        return []
    names = []
    for child in sorted(skills_dir.iterdir()):
        if child.is_dir() and (child / "SKILL.md").is_file():
            names.append(child.name)
    return names


def link_one(
    skill_name: str,
    src: Path,
    cc_switch_root: Path,
    claude_root: Path,
    *,
    unlink: bool,
    dry_run: bool,
) -> str:
    """处理单个 skill 的两层链接。返回状态描述。"""
    store_path = cc_switch_root / skill_name
    claude_path = claude_root / skill_name

    if unlink:
        # 仅移除本脚本创建的链接（指向本仓库源 / 指向 store），不动真实目录。
        removed = []
        for p in (claude_path, store_path):  # 先删 claude 层，再删 store 层
            if is_symlink_to(p, store_path if p == claude_path else src):
                if not dry_run:
                    try:
                        p.unlink()
                    except OSError as e:
                        return f"{skill_name}: 移除失败 {p}: {e}"
                removed.append(str(p))
        if removed:
            return f"{skill_name}: 已移除链接 {', '.join(removed)}"
        return f"{skill_name}: 无需移除（未找到本脚本创建的链接）"

    # ---- 增量链接 ----
    messages = []

    # 第一层：cc-switch store -> 仓库源
    if is_symlink_to(store_path, src):
        messages.append("store 已链接")
    elif store_path.exists() or store_path.is_symlink():
        # 目标已存在（真实目录 / 指向他处的链接）——不覆盖
        kind = "符号链接指向他处" if store_path.is_symlink() else "已存在（非符号链接，可能是 cc-switch 内置 skill）"
        messages.append(f"store {kind}，跳过不覆盖")
    else:
        if not dry_run:
            store_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                store_path.symlink_to(src, target_is_directory=True)
            except OSError as e:
                return f"{skill_name}: 创建 store 链接失败 {store_path}: {e}\n  提示：Windows 需开启「开发者模式」或以管理员运行"
        messages.append(f"store 已新建 -> {src}")

    # 第二层：claude skills -> cc-switch store
    if is_symlink_to(claude_path, store_path):
        messages.append("claude 已链接")
    elif claude_path.exists() or claude_path.is_symlink():
        kind = "符号链接指向他处" if claude_path.is_symlink() else "已存在（非符号链接）"
        messages.append(f"claude {kind}，跳过不覆盖")
    else:
        if not dry_run:
            claude_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                claude_path.symlink_to(store_path, target_is_directory=True)
            except OSError as e:
                return f"{skill_name}: 创建 claude 链接失败 {claude_path}: {e}"
        messages.append(f"claude 已新建 -> {store_path}")

    return f"{skill_name}: " + "; ".join(messages)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="把仓库 skills/ 增量链接到 cc-switch 与 Claude Code（不覆盖已存在项）",
    )
    parser.add_argument("--skill", action="append", default=None,
                        help="只处理指定 skill（可多次）；默认处理全部")
    parser.add_argument("--cc-switch-root", default=str(DEFAULT_CC_SWITCH_ROOT),
                        help=f"cc-switch skills 目录（默认 {DEFAULT_CC_SWITCH_ROOT}）")
    parser.add_argument("--claude-root", default=str(DEFAULT_CLAUDE_ROOT),
                        help=f"Claude Code skills 目录（默认 {DEFAULT_CLAUDE_ROOT}）")
    parser.add_argument("--dry-run", action="store_true", help="预览，不实际创建/移除")
    parser.add_argument("--unlink", action="store_true", help="移除本脚本创建的链接")
    args = parser.parse_args(argv)

    cc_switch_root = Path(args.cc_switch_root).expanduser()
    claude_root = Path(args.claude_root).expanduser()

    if args.skill:
        skill_names = args.skill
        # 校验存在
        for name in skill_names:
            if not (REPO_SKILLS_DIR / name / "SKILL.md").is_file():
                print(f"错误：仓库 skills/ 下未找到 skill：{name}", file=sys.stderr)
                return 2
    else:
        skill_names = discover_skills(REPO_SKILLS_DIR)
        if not skill_names:
            print(f"错误：未在 {REPO_SKILLS_DIR} 下发现任何含 SKILL.md 的 skill", file=sys.stderr)
            return 2

    print(f"仓库 skills 目录: {REPO_SKILLS_DIR}")
    print(f"cc-switch store:  {cc_switch_root}")
    print(f"claude skills:    {claude_root}")
    print(f"模式: {'移除链接' if args.unlink else '增量链接'}{' (dry-run)' if args.dry_run else ''}")
    print(f"待处理 skill 数: {len(skill_names)}")
    print("-" * 60)

    for name in skill_names:
        src = REPO_SKILLS_DIR / name
        print(link_one(name, src, cc_switch_root, claude_root,
                        unlink=args.unlink, dry_run=args.dry_run))

    print("-" * 60)
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
