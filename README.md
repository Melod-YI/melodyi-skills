# melodyi-skills

> 一套面向 Claude Code 的 Agent Skills 合集 —— 把"让 Claude 帮你做事"的能力沉淀成一个个可复用的 skill。

这个仓库里收录了作者日常使用 Claude Code 时沉淀下来的各类 skill：从抓网页、搜网络、读 arXiv 论文，到 GitCode PR 检视、影视文件整理、发邮件、看 Hacker News……每个 skill 都是自包含的工具，Claude 在运行时按需读取并执行。

## 这是什么

**Claude Code Agent Skills** 是扩展 Claude Code 能力的机制：一个 skill 就是一份给 Claude 看的"使用手册"（`SKILL.md`），告诉它在什么场景下触发、调用哪些工具、如何处理错误、如何格式化输出。Claude 会根据用户的话自动路由到合适的 skill。

本仓库里的 skill 分两类：

- **轻量 skill**：仅含 `SKILL.md`（外加少量脚本/测试），直接由 Claude 读取并执行。
- **CLI skill**：携带大量代码、需先安装为命令行工具，对应的 `SKILL.md` 只负责调用已安装的 CLI，真正的代码放在 `packages/` 下。

## Skill 清单

> 路由以 `SKILL.md` frontmatter 里的 `name` 为准，下表「skill 名」即该 name；「目录」是仓库里的实际目录名。

| Skill 名 | 目录 | 一句话说明 |
| --- | --- | --- |
| `melodyi-web-search` | `skills/melodyi-web-search` | 多提供商网络搜索，查实时信息、新闻、文档 |
| `melodyi-web-fetch` | `skills/melodyi-web-fetch` | 抓取网页并转为 markdown，读文章、提取文档内容 |
| `arxiv-analyze` | `skills/arxiv-analyze` | 给定 arXiv 链接或编号，阅读并分析论文 |
| `hackernews` | `skills/hackernews` | 按 URL 搜索 Hacker News 讨论、抓取/精简评论线程 |
| `image-understanding` | `skills/melodyi-vision` | 当前模型不支持多模态时，借外部能力理解/分析图片 |
| `get-user-location` | `skills/get-user-location` | 获取用户实时地理位置（"我在哪""定位"等场景） |
| `cross-repo-analyzer` | `skills/agent-compare` | 在当前 workspace 下添加 git 项目，对比多个仓库的差异 |
| `gitcode-pr-review` | `skills/gitcode-pr-review` | 检视 GitCode PR 代码、提交评论、验收检视意见 |
| `gitcode-contribution` | `skills/gitcode-contribution` | 统计某用户在某 GitCode 仓库的总贡献（MR、增减行等） |
| `blogwatcher-cli` | `skills/blogwatcher-cli` | 用 blogwatcher CLI 管理博客文章（扫描更新、已读/未读、备注） |
| `gws-gmail-send` | `skills/gws-gmail-send` | 通过 Gmail 发送邮件（可带附件打包压缩） |
| `melodyi-filebot` | `skills/melodyi-filebot` | 剧集/番剧/电影批量重命名、目录整理、生成 Jellyfin NFO |

按用途粗略分组：

- **信息获取**：`melodyi-web-search`、`melodyi-web-fetch`、`arxiv-analyze`、`hackernews`、`image-understanding`、`get-user-location`
- **开发协作**：`cross-repo-analyzer`、`gitcode-pr-review`、`gitcode-contribution`
- **内容与邮件**：`blogwatcher-cli`、`gws-gmail-send`
- **媒体整理**：`melodyi-filebot`

## 仓库结构

```
melodyi-skills/
├── skills/        # 所有 skill 的定义（SKILL.md + 可选 CLAUDE.md/scripts/tests）
├── packages/      # 需安装为 CLI 的较重代码包（gitcode / melodyi-web / melodyi-filebot）
├── scripts/       # 仓库级脚本：sync_skills.py 同步脚本 + 配置
├── docs/          # 文档资料
├── CLAUDE.md      # 给 Claude Code 看的项目指引
└── README.md      # 本文件
```

`skills/` 与 `packages/` 的对应关系：

| Skill（在 `skills/` 下） | 对应 Package（在 `packages/` 下） | CLI 命令 |
| --- | --- | --- |
| `melodyi-web-fetch` + `melodyi-web-search` | `packages/melodyi-web` | `melodyi-web` |
| `gitcode-pr-review` + `gitcode-contribution` | `packages/gitcode` | `gitcode` |
| `melodyi-filebot` | `packages/melodyi-filebot` | `melodyi-filebot` |
| `blogwatcher-cli` | （引用外部 `blogwatcher` CLI，本仓库内无 package） | `blogwatcher` |

## 快速开始

### 1. 同步 skill 到隔离 workspace

skill 通过 `scripts/sync_skills.py` 同步到一个隔离于源码仓库的 workspace，便于在受控环境下验证功能：

```bash
# 同步所有 skill（默认目标 ~/.melodyi-skills/workspace，可配置）
python scripts/sync_skills.py

# 指定目标目录（覆盖配置与环境变量）
python scripts/sync_skills.py --workspace-root /path/to/workspace
```

`<workspace_root>` 优先级：CLI `--workspace-root` > 环境变量 `MELODYI_SYNC_WORKSPACE_ROOT` > `scripts/sync-skills.local.yaml`（本地覆盖，gitignore）> `scripts/sync-skills.yaml`（仓库默认）> 内置默认。

### 2. 安装 CLI 包（仅 CLI skill 需要）

涉及 `packages/` 下代码的 skill（melodyi-web / gitcode / melodyi-filebot）需先安装为 CLI：

```bash
# 开发模式安装
pip install -e packages/gitcode
pip install -e packages/melodyi-web
pip install -e packages/melodyi-filebot

# 含开发依赖
pip install -e "packages/<pkg>[dev]"
```

> 各包的子命令、配置细节见 `packages/<pkg>/CLAUDE.md`。

## 配置与数据目录约定

各 skill 的用户配置、运行时数据（数据库、日志、快照等）统一放在用户主目录下：

- **目录根**：`~/.melodyi-skills/<skill-name>/`，所有 skill 共用 `~/.melodyi-skills/` 根目录，各自一个子目录。
- **优先级**：CLI 参数 > 环境变量 > 用户配置文件 > 内置默认值。
- **默认值一律用绝对路径**（基于 `~/.melodyi-skills/<skill>/`），避免把数据/日志写到当前工作目录污染仓库。
- **运行时产物不入库**：数据库、日志等不提交进仓库，对应目录写入 `.gitignore`。

## 开发与测试

```bash
# 运行某 package 的全部测试
pytest packages/gitcode/tests -v
pytest packages/melodyi-web/tests -v
pytest packages/melodyi-filebot/tests -v

# 单个用例
pytest packages/<pkg>/tests/test_xxx.py::test_name -v
pytest packages/<pkg>/tests/test_xxx.py -k "test_name"

# 部分轻量 skill 自带 tests/ 与 pytest.ini
pytest skills/melodyi-vision/tests -v

# 同步脚本自身的测试
pytest scripts/test_sync_skills.py -v
```

新增/修改 skill 时，建议加载 `skill-creator` skill 了解 skill 开发规范；与本项目约定冲突时以项目约定为准。

## Windows 环境说明

本项目在 Windows 上运行，使用 Scoop 管理工具。Git Bash 路径为 `C:\Applications\Scoop\apps\git\current\bin\bash.exe`。

需要从 skill 中启动 Claude Code 子进程时，使用如下模式：

```bash
CLAUDE_CODE_GIT_BASH_PATH="C:\Applications\Scoop\apps\git\current\bin\bash.exe" \
powershell -Command "cd 'project_path'; claude -p --output-format json 'question'"
```

会话恢复使用 `-r <session-id>`（不用 `-c`，多个 Claude 实例在同一目录运行时 `-c` 可能恢复错误的会话）。

## 语言与文档规范

- **文档语言**：中文 —— `SKILL.md`、`CLAUDE.md`、文档字符串、错误提示、CLI 帮助文本、提交信息均用中文。
- **代码语言**：英文标识符 + 中文文档字符串/注释。
- **提交信息**：约定式提交（`feat:` / `fix:` / `refactor:` / `docs:` / `chore:`）+ 中文描述。
- **Python**：>= 3.10；PEP 8；Pydantic V2；Click（CLI）；httpx（HTTP）；argparse（简单脚本）。

## 相关文档

- `CLAUDE.md` —— 给 Claude Code 看的项目整体指引（开发约束、目录结构、命令、约定）。
- `packages/<pkg>/CLAUDE.md` —— 各 CLI 包内部的权威开发指引。
- `scripts/sync-skills.yaml` —— 同步脚本配置（含注释说明）。
- `docs/` —— 其他文档资料。
