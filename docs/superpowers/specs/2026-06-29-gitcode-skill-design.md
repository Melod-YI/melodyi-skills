# gitcode skill 设计文档

日期：2026-06-29
分支：git-code-skill

## 背景与动机

源 skill（`SKILL.md.source`，名为 `gitcode-pr-reviewer`）让 agent 直接执行：

- `curl` 调用 GitCode API（PR 详情、文件列表、评论、提交评论、验收评论）
- `Read` 读取 `config.json` 获取 `gitcode_token`
- 用临时文件 `--data-binary @file` 规避命令行中文编码问题

这些操作的痛点是：秘钥暴露在 agent 上下文与命令行中、中文编码脆弱、API 调用样板重复。

本设计把这些操作封装进一个可安装的 Python CLI 包，agent 只调用脚本子命令，token 在包内部读取，不暴露给 agent。

## 目标

- 提供 `packages/gitcode` CLI 包（`pip install -e packages/gitcode`），封装 GitCode API 调用、URL 解析、token 加载
- 提供 `skills/gitcode-pr-review` 轻量 skill，覆盖源 skill 的「检视 + 验收」双模式，调用已安装的 CLI
- 结构上支持未来拆分出更多场景 skill（提交、合并等），共享同一 CLI 与同一份账号级 token 配置

## 非目标（YAGNI）

- 不实现「提交/建 PR」「合并」子命令——留待未来对应 skill 时再做
- 不封装 git 克隆/切换分支——交回 agent
- 不实现代码分析、严重度判定——agent 职责

## 目录结构

```
packages/gitcode/
  pyproject.toml              # 入点 gitcode=gitcode.cli:cli；依赖 click、httpx
  src/gitcode/
    __init__.py
    cli.py                    # Click 命令组
    config.py                 # token 解析
    api.py                    # GitCodeClient(httpx)
    url.py                    # parse_pr_url()
  tests/
    test_url.py
    test_config.py
    test_api.py
skills/gitcode-pr-review/
  SKILL.md                    # 检视+验收，调用 gitcode CLI
```

`packages/gitcode` 不参与 `sync-skills.sh`，使用前需 `pip install -e packages/gitcode`（同 melodyi-web）。

## CLI 子命令

| 子命令 | 作用 | stdout 输出 |
|---|---|---|
| `gitcode user` | 当前 token 对应用户 | JSON |
| `gitcode pr <url>` | PR 详情（标题/描述/源/目标分支/状态） | JSON |
| `gitcode files <url>` | 变更文件列表 | JSON |
| `gitcode comments <url> [--mine]` | 评论列表；`--mine` 仅当前用户 | JSON |
| `gitcode comment <url> --path P --position N (--body-file F \| --body T) [--commit-id SHA]` | 提交行内评论 | JSON |
| `gitcode resolve <url> --discussion-id D [--resolved true\|false]` | 更新评论解决状态 | JSON |

`<url>` 直接吃用户给的 PR 链接，`parse_pr_url()` 内部解析 owner/repo/number，兼容：

- `https://gitcode.net/{owner}/{repo}/-/merge_requests/{n}`
- `https://gitcode.com/{owner}/{repo}/pulls/{n}`
- `https://gitcode.com/{owner}/{repo}/-/merge_requests/{n}`

`comment` 提供 `--body`（内联）与 `--body-file`（文件）两种传参，长内容/多行中文建议用 `--body-file`。

## 配置与认证

- token 来源优先级：环境变量 `GITCODE_TOKEN` > `~/.melodyi-skills/gitcode/config.json` 的 `gitcode_token`
- CLI 提供 `--config PATH` 指定配置文件路径（覆盖默认位置，便于多账号/测试）；**不提供 `--token` 选项**，以免秘钥落入命令行/进程列表，违背"token 不暴露"目标
- 配置目录用 `gitcode`（账号级 token，未来 submit/review/merge 三个 skill 共用同一份）
- API base：`https://api.gitcode.com/api/v5`
- 认证：`Authorization: Bearer {token}` 请求头（token 不进 URL/命令行/日志）
- 中文编码：httpx `json=body` 自动 UTF-8 编码，无需临时文件

## 依赖

- Python >= 3.10
- `click`（CLI 框架，约定；命令组便于未来拆 skill）
- `httpx`（HTTP，约定；JSON 自动收发 + MockTransport 便于测试）

声明于 `pyproject.toml`。

## 输出与退出码

- stdout：结构化 JSON（供 agent 解析）
- stderr：日志（请求方法/URL、状态码、错误）
- 退出码：`0` 成功 / `1` 网络/业务错误（含 4xx/5xx）/ `2` token 未配置

## 测试策略（TDD，不打真实 API）

- `test_url.py`：三种 URL 格式解析 → owner/repo/number；非法 URL 报错
- `test_config.py`：token 优先级（env > config，用临时配置文件与 `monkeypatch`）；缺失时返回 None
- `test_api.py`：用 httpx `MockTransport` 注入假响应，验证各端点的请求 URL/headers/body 构造与响应解析；401/404 等状态码映射到退出码与错误信息

## SKILL.md 改写要点

保留源 skill 内容：

- 两种模式：代码检视 / 验收检视意见
- 严重度分级：严重（自动提交行内评论）、建议（汇总后由用户选择提交）
- 评论格式：`**[严重]** ...` / `**[建议]** ...`
- 检视要点、错误码表、非交互式 git 注意事项（禁 `git rebase -i`、`--no-pager`、`git commit -m` 等）

替换：

- 所有 `curl ...` → `gitcode <子命令>`
- 所有 `Read config.json 取 token` → 删除（CLI 内部处理；token 缺失时 CLI 退出码 2 并提示）
- 删除「临时文件 + --data-binary」相关说明

## 未来扩展（不在本次范围）

按场景拆分轻量 skill，各自由对应 CLI 子命令组支撑：

- `skills/gitcode-submit`：建 PR / 推送（对应未来 `gitcode submit ...` 子命令）
- `skills/gitcode-merge`：合并 PR（对应未来 `gitcode merge ...` 子命令）

三者共享 `packages/gitcode` 与 `~/.melodyi-skills/gitcode/config.json`。
