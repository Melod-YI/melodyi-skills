# CLAUDE.md

本文件为 Claude Code 在 `packages/gitcode` 下工作时提供指导。

## 项目概述

`gitcode` 是 GitCode PR 代码检视的 CLI 包，封装 GitCode v5 API 调用与 token 管理。
配套轻量 skill `skills/gitcode-pr-review` 通过调用已安装的 `gitcode` CLI 完成检视/验收。
未来可拆分 `gitcode-submit`、`gitcode-merge` 等 skill，共享本包与同一份账号级 token 配置。

## 常用命令

```bash
# 安装（开发模式）
pip install -e packages/gitcode

# 运行测试
pytest packages/gitcode/tests -v

# 验证配置
gitcode user
```

## 配置

token 优先级：环境变量 `GITCODE_TOKEN` > `~/.melodyi-skills/gitcode/config.json` 的 `gitcode_token`。
CLI 提供 `--config PATH` 指定配置文件路径（不提供 `--token`，避免秘钥落入命令行）。

## 架构

- `url.py`：`parse_pr_url()` 从 PR URL 解析 owner/repo/number
- `config.py`：`load_token()` 读取 token（env > config）
- `api.py`：`GitCodeClient(httpx)` 封装端点，token 经 `Authorization: Bearer` 头发送；
  `APIError` 承载 4xx/5xx 与网络错误
- `cli.py`：click 命令组，6 个子命令；stdout 输出 JSON，stderr 日志；
  退出码 0/1/2；`--mine` 在 cli 层过滤（取 user.login 后筛 comments）

## 设计决策

- httpx（非 stdlib urllib）：JSON 自动 UTF-8 编码、MockTransport 便于测试、符合项目约定；
  包形态下安装成本不再是缺点
- 评论 body 支持 `--body` 与 `--body-file`，长内容/中文推荐 `--body-file`
- API 返回原始 JSON 透传，过滤/分析交给调用方（cli 或 agent）
