# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 约束

1. 我们使用中文交流，使用中文输出文档。
2. 我们修改的每一个"问题"，在条件允许的情况下都应该添加测试用例，避免未来再次改错。

## 项目概述

**melodyi-skills** 是一个 Claude Code Agent Skills 的 monorepo——每个 skill 是一个自包含的工具，用于扩展 Claude Code 的能力。大部分 skill 是标准化的，仅含 `SKILL.md`（skill 定义/Claude 运行时读取的指令）以及可选的 `CLAUDE.md`（开发指南）；少数 skill 携带大量代码、需安装为 CLI 后执行，这类代码作为独立包放在 `packages/` 下，对应的 `SKILL.md` 则作为轻量 skill 放在 `skills/` 下，通过命令名调用已安装的 CLI。

Skills 通过 `sync-skills.sh` 同步到 **仓库同级目录** `../skill-workspace/`，将每个 skill 复制到 `../skill-workspace/<name>-workspace/.claude/skills/<name>/`。主要目的是在受控的、隔离于源码仓库的环境下验证对应 skill 的功能。`packages/` 下的 CLI 包不在 `sync-skills.sh` 同步范围内，需单独安装（见下文「常用命令」）。

> 注：仓库内的 `workspace/` 目录是历史遗留的本地运行时目录，已被 `.gitignore` 忽略；当前同步脚本的实际目标是 `../skill-workspace/`，不要往仓库内 `workspace/` 写新内容。

我们所有的开发、测试都在当前工程下，不要放在 user 目录的 `.claude` 文件夹下。

## 目录结构

```
melodyi-skills/
|-- skills/              # 所有 skill 的定义（SKILL.md + 可选 CLAUDE.md/scripts/tests）
|-- packages/           # 需安装为 CLI 的较重代码包（含 pyproject.toml、源码、tests/）
|-- docs/               # 文档资料
|-- sync-skills.sh      # 同步脚本：skills/ -> ../skill-workspace/<name>-workspace/.claude/skills/<name>/
|-- SKILL.md.source     # 部分 skill 的原始需求/草稿来源
+-- CLAUDE.md           # 本文件
```

- **`skills/`** — 每个子目录是一个独立的 skill。包含 `SKILL.md`、可选的 `CLAUDE.md`、以及少量直接放在 `scripts/` 下执行的脚本（如 `arxiv-analyze`、`hackernews`、`melodyi-vision`）。携带大量代码、需安装为 CLI 的 skill，其 `SKILL.md` 仍在此处，但实际代码放在 `packages/` 下对应的包中。
- **`packages/`** — 需安装为 CLI 后执行的较重代码包，flat 布局（源码在 `packages/<pkg>/<pkg>/`，测试在 `packages/<pkg>/tests/`）。每个包有自己的 `CLAUDE.md`，作为该包内部开发的权威指引——在包内工作时以其为准。
- **skill 与 package 的对应关系**（实际代码为准）：
  - `skills/melodyi-web-fetch` + `skills/melodyi-web-search` → `packages/melodyi-web`（CLI：`melodyi-web`，DDD 架构：`application/domain/infrastructure/providers`）
  - `skills/gitcode-pr-review` + `skills/gitcode-contribution` → `packages/gitcode`（CLI：`gitcode`）
  - `skills/melodyi-filebot` → `packages/melodyi-filebot`（CLI：`melodyi-filebot`）
  - `skills/blogwatcher-cli` → 引用外部 `blogwatcher` CLI，本仓库内**无**对应 package
- **skill 名 vs 目录名**：`SKILL.md` frontmatter 里的 `name` 不一定等于目录名（如 `skills/agent-compare` 的 `name: cross-repo-analyzer`，`skills/melodyi-vision` 的 `name: image-understanding`）。路由以 frontmatter `name` 为准，文件系统以目录名为准。

> 以上仅列出部分示例，实际子目录会随开发迭代增减，请以文件系统为准。

## 常用命令

```bash
# 同步所有 skill 到隔离 workspace（仓库同级 ../skill-workspace/）
bash sync-skills.sh

# 安装某个 CLI 包（开发模式，需在各包目录或仓库根执行）
pip install -e packages/gitcode
pip install -e packages/melodyi-web
pip install -e packages/melodyi-filebot
# 含开发依赖：
pip install -e "packages/<pkg>[dev]"

# 运行某包的全部测试
pytest packages/gitcode/tests -v
pytest packages/melodyi-web/tests -v
pytest packages/melodyi-filebot/tests -v

# 运行单个测试用例
pytest packages/<pkg>/tests/test_xxx.py::test_name -v
pytest packages/<pkg>/tests/test_xxx.py -k "test_name"

# 运行 skill 内置脚本测试（部分 skill 自带 tests/ 与 pytest.ini，如 melodyi-vision、get-user-location）
pytest skills/melodyi-vision/tests -v
```

> 各 package 的具体命令、CLI 子命令与配置细节见 `packages/<pkg>/CLAUDE.md`。

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

## 用户配置与数据目录约定

各 skill 的用户配置、运行时数据（数据库、日志、快照等）统一放在用户主目录下，遵循同一约定：

- **目录根**：`~/.melodyi-skills/<skill-name>/`（所有 skill 共用 `~/.melodyi-skills/` 根目录，各自一个子目录）。代码中以 `Path.home() / ".melodyi-skills" / "<skill-name>"` 定义，如 `USER_CONFIG_DIR` / `CONFIG_DIR`。
- **优先级**：CLI 参数 > 环境变量 > 用户配置文件 > 内置默认值。
- **默认值必须用绝对路径**：Pydantic 配置模型（schema）里所有路径字段的默认值必须基于 `Path.home()` 拼出绝对路径，**禁止用相对路径**（如 `./data/compare.db`、`./logs`）。相对默认会在"配置文件缺该字段"时把数据/日志写到当前工作目录（CWD），污染仓库或运行目录。内置默认加载器（`_get_builtin_default_config` 等）同样指向用户目录绝对路径。
- **`config init` 模板**：生成的 `config.yaml` 模板里路径用 `${HOME}/.melodyi-skills/<skill-name>/...` 形式，与默认值一致。
- **运行时产物不入库**：数据库、日志等运行时生成的文件不提交进仓库，对应目录写入 `.gitignore`（如 `packages/<pkg>/data/`）。

> 反例（已修复）：melodyi-web 曾在 `config_schema.py` 用相对默认 `./data/compare.db`、`./logs`，导致比对模式 db 和日志落到包目录下；同时用户 `config.yaml` 里曾误写 `${HOME}/.melodyi-web/...`（少了 `melodyi-skills/` 段）。新增/修改路径字段时务必对照本约定。

## 语言与文档规范

- **文档语言：** 中文 — SKILL.md 文件、CLAUDE.md 文件、文档字符串、错误指导文本、CLI 帮助文本和提交信息均使用中文
- **代码语言：** 英文标识符，中文文档字符串和注释
- **提交信息格式：** 约定式提交（`feat:`、`fix:`、`refactor:`、`docs:`、`chore:`）+ 中文描述
- **Python 版本：** 全部 >=3.10
- **代码风格：** PEP 8；Pydantic V2 模型；Click 用于 CLI；httpx 用于 HTTP；argparse 用于简单脚本
