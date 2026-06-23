# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。

## 约束

1. 我们使用中文交流，使用中文输出文档。
2. 我们修改的每一个"问题"，在条件允许的情况下都应该添加测试用例，避免未来再次改错。

## 项目概述

**melodyi-skills** 是一个 Claude Code Agent Skills 的 monorepo——每个 skill 是一个自包含的工具，用于扩展 Claude Code 的能力。每个 skill 位于 `skills/<name>/` 目录下，包含一个 `SKILL.md`（skill 定义/Claude 运行时读取的指令）以及可选的 `CLAUDE.md`（开发指南）。

Skills 通过 `sync-skills.sh` 同步到 workspace 目录，将每个 skill 复制到 `workspace/<name>-workspace/.claude/skills/<name>/`。主要目的是在受控的环境下验证对应 skill 的功能。

我们所有的开发、测试都在当前工程下，不要放在 user 目录的 `.claude` 文件夹下。

## 目录结构

```
melodyi-skills/
|-- skills/              # 所有 skill 的源码定义（如 melodyi-web/、hackernews/、melodyi-vision/ 等）
|-- workspace/           # 各 skill 的运行时 workspace（如 melodyi-web-workspace/、hackernews-workspace/ 等）
|-- sync-skills.sh       # 同步脚本：skills/ > workspace/<name>-workspace/.claude/skills/<name>/
+-- CLAUDE.md            # 本文件
```

- **`skills/`** — 每个子目录是一个独立的 skill 项目，包含 `SKILL.md`、可选的 `CLAUDE.md`、源码和测试等。
- **`workspace/`** — 每个子目录对应一个 skill 的运行时环境（命名 `<skill-name>-workspace/`），由 `sync-skills.sh` 自动创建和维护。用于在隔离环境中测试 skill。

> 以上仅列出部分示例子目录，实际子目录会随开发迭代增减，请以文件系统为准。

## SKILL.md 格式

Skill 使用 `SKILL.md` 定义，包含 YAML frontmatter：
```yaml
---
name: skill-name
description: 触发条件描述（用于 Claude skill 路由）
---
```
后跟 Markdown 格式的指令，Claude 在运行时读取。这些是 skill 的使用手册——告诉 Claude 如何调用工具、处理错误和格式化输出。

如需更多信息，加载 skill-creator 这个 skill。需要注意，该 skill 的内容你仅需了解 skill 开发相关的约束、流程、规范、知识。与当前项目用户要求的内容相悖的，以用户要求为准。

## Windows 环境说明

本项目在 Windows 上运行，使用 Scoop 管理的工具。Git Bash 路径为 `C:\Applications\Scoop\apps\git\current\bin\bash.exe`。

需要从 skill 中启动 Claude Code 子进程时，使用如下模式：
```bash
CLAUDE_CODE_GIT_BASH_PATH="C:\Applications\Scoop\apps\git\current\bin\bash.exe" powershell -Command "cd 'project_path'; claude -p --output-format json 'question'"
```

会话恢复使用 `-r <session-id>`（不用 `-c`，多个 Claude 实例在同一目录运行时 `-c` 可能恢复错误的会话）。

## 语言与文档规范

- **文档语言：** 中文 — SKILL.md 文件、CLAUDE.md 文件、文档字符串、错误指导文本、CLI 帮助文本和提交信息均使用中文
- **代码语言：** 英文标识符，中文文档字符串和注释
- **提交信息格式：** 约定式提交（`feat:`、`fix:`、`refactor:`、`docs:`、`chore:`）+ 中文描述
- **Python 版本：** 全部 >=3.10
- **代码风格：** PEP 8；Pydantic V2 模型；Click 用于 CLI；httpx 用于 HTTP；argparse 用于简单脚本
