#!/bin/bash

# 脚本用于同步 skills 目录到对应的 workspace
# 对于每个 skill，会创建/更新对应的 workspace 目录

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/skills"
WORKSPACE_ROOT="$SCRIPT_DIR/../skill-workspace"

echo "=== Skills 同步脚本 ==="
echo "Skills 目录: $SKILLS_DIR"
echo "Workspace 根目录: $WORKSPACE_ROOT"
echo ""

# 检查 skills 目录是否存在
if [ ! -d "$SKILLS_DIR" ]; then
    echo "错误: skills 目录不存在: $SKILLS_DIR"
    exit 1
fi

# 遍历 skills 目录下的每个第一层子文件夹
for skill_path in "$SKILLS_DIR"/*/; do
    # 检查是否为目录
    if [ ! -d "$skill_path" ]; then
        continue
    fi

    # 获取文件夹名称（去掉路径和末尾斜杠）
    skill_name=$(basename "$skill_path")

    # 构建对应的 workspace 路径
    workspace_path="$WORKSPACE_ROOT/${skill_name}-workspace"
    target_skill_dir="$workspace_path/.claude/skills/$skill_name"

    echo "----------------------------------------"
    echo "处理 skill: $skill_name"
    echo "  源路径: $skill_path"
    echo "  目标 workspace: $workspace_path"
    echo "  目标 skill 目录: $target_skill_dir"

    # 检查并创建 workspace 目录
    if [ ! -d "$workspace_path" ]; then
        echo "  -> 创建 workspace 目录: $workspace_path"
        mkdir -p "$workspace_path"
    fi

    # 创建 .claude/skills 目录结构
    mkdir -p "$workspace_path/.claude/skills"

    # 清空目标 skill 目录（如果存在）
    if [ -d "$target_skill_dir" ]; then
        echo "  -> 清空已存在的目标目录"
        rm -rf "$target_skill_dir"
    fi

    # 复制 skill 目录
    echo "  -> 复制 $skill_name 到目标目录"
    cp -r "$skill_path" "$target_skill_dir"

    echo "  -> 完成!"
done

echo ""
echo "=== 同步完成 ==="