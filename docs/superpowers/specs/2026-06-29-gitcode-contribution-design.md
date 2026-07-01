# gitcode-contribution 设计文档

日期：2026-06-29
分支：git-code-skill

## 背景与目标

用户希望 agent 能根据「用户名 + 仓库地址」收集某用户在该仓库的**总贡献情况**，最终交付一份 Markdown 汇总报告供验收。

具体采集目标（仓库 `openJiuwen/jiuwenswarm`，用户 `Melod-YI`，含未合并/已关闭的 MR）：

- MR 清单（编号、标题、状态、链接）
- 每个 MR 的增/删行数量
- 其中**测试代码**增/删、**非测试代码**增/删
- 全局合计

## 关键决策

1. **测试/非测试分类由 agent 完成，不落在代码里**（用户明确要求）。CLI 只负责取数。
2. **CLI 保持薄封装**：仅新增"列出仓库 PR"的取数能力，分类与汇总在 skill/agent 层。与项目「API 透传、分析交给调用方」约定一致。
3. **交付物为 Markdown 汇总报告**。

## GitCode v5 API 事实（已确认，来源 docs.gitcode.com）

- 列出 PR：`GET /repos/{owner}/{repo}/pulls`
  - `state`：`all`/`open`/`closed`/`merged`/`locked`，默认 `all`
  - `author`：按创建者用户名过滤
  - 分页：`page`（默认 1）/`per_page`（默认 20，最大 100）
  - 列表项含 `number`/`title`/`state`/`user.login`/`added_lines`/`removed_lines`/`html_url`/`merged_at`/`closed_at`
- 文件列表：`GET /repos/{owner}/{repo}/pulls/{number}/files`
  - 每文件含 `filename`/`status`/`additions`(string)/`deletions`(string)
  - 同样 `page`/`per_page` 分页
- `state` 直接取值 `merged` 区分已合并（GitCode 与 GitHub 不同，不靠 `merged` 布尔）

## 改动范围

### 1. `packages/gitcode/gitcode/url.py`

新增 `parse_repo_url(url) -> RepoRef(owner, repo)`：从仓库首页 URL 解析 owner/repo。

- 支持形态：`https://gitcode.com/{owner}/{repo}`、`https://gitcode.net/{owner}/{repo}`，尾部可带 `/`、`/-/...`、`.git` 等
- 与现有 `parse_pr_url` 共用 `UrlParseError`、`_ALLOWED_HOSTS`、`_SEG`
- 新增 `RepoRef` dataclass（owner, repo）

### 2. `packages/gitcode/gitcode/api.py`

- 新增 `list_prs(owner, repo, *, state="all", author=None) -> list`
  - 内部分页：`per_page=100`，循环 `page` 直到返回条数 < 100
  - 透传原始 PR 对象数组
- `get_files` 改为内部分页（同策略），保证大 MR 不丢文件
  - 行为变化：原单次请求 → 多页聚合；返回值类型仍为 `list`
  - 需更新 `test_api.py::test_get_files_request_and_parse` 以适配分页 URL（带 `page`/`per_page` 查询参数）

### 3. `packages/gitcode/gitcode/cli.py`

新增 `prs` 子命令：

```
gitcode prs <仓库URL> [--author <login>] [--state all]
```

- `--author`：创建者用户名（透传 API `author` 参数）
- `--state`：`all`/`open`/`closed`/`merged`，默认 `all`
- 退出码沿用 0/1/2；stdout 输出 JSON 数组
- URL 解析失败 → 1；token 缺失 → 2

### 4. `skills/gitcode-contribution/SKILL.md`（新建）

编排手册，agent 执行：

1. `gitcode prs <repo-url> --author <login> --state all` → 全部该用户 MR（含已合并/已关闭/开放）
2. 对每个 MR：`gitcode files <mr-url>` → 变更文件列表（含 filename/additions/deletions）
3. 用启发式规则判定每个文件是否测试代码（见下）
4. 汇总：每 MR {增,删,测试增,测试删,非测试增,非测试删} + 全局合计；用 PR `added_lines`/`removed_lines` 交叉校验总增删
5. 输出 Markdown 报告

**测试/非测试分类启发式**（写进 SKILL.md，agent 执行，只看路径文件名不读内容）：

文件归为"测试"当且仅当满足任一：
- 路径任一段 ∈ {`test`, `tests`, `__tests__`, `spec`, `specs`, `__mocks__`}
- 文件名（去扩展名）以 `test_` 开头、或以 `_test`/`_spec` 结尾、或扩展名前一段为 `test`/`spec`（即 `*.test.*`/`*.spec.*`）

非测试 = 其余（含配置类 `.yml`/`.json`/`Makefile` 等）。

**单 MR 取文件失败**：报告里标注该 MR"取文件失败"并跳过其拆分，但保留 MR 清单与 PR 总增删，不中断整体收集。

### 5. Markdown 报告样例

```markdown
# Melod-YI 在 openJiuwen/jiuwenswarm 的贡献汇总

共 N 个 MR（已合并 X / 已关闭 Y / 开放 Z）。

| # | 标题 | 状态 | 增 | 删 | 测试增 | 测试删 | 非测试增 | 非测试删 |
|---|------|------|---|---|--------|--------|----------|----------|
| 12 | feat: ... | merged | 120 | 30 | 40 | 5 | 80 | 25 |

**合计**：增 1234 / 删 321；测试增 300 / 测试删 60；非测试增 934 / 非测试删 261。
```

## 错误处理

- 退出码：0 成功 / 1 业务或网络错误 / 2 token 缺失或参数错误
- `prs`：非仓库 URL → 1；token 缺失 → 2；4xx/5xx → 1
- 429 等限流：agent 等待后重试（沿用 gitcode-pr-review 错误处理表）

## 测试

- `test_url.py`：`parse_repo_url` 合法/非法用例
- `test_api.py`：`list_prs` 请求参数（state/author/page/per_page）、多页聚合、空结果；`get_files` 分页聚合
- `test_cli.py`：`prs` 退出码、stdout JSON、`--author`/`--state` 透传、非法 URL→1
- 分类与汇总在 agent 层，不写代码测试（按用户要求）

## 非目标（YAGNI）

- 不在 CLI 实现分类/汇总逻辑
- 不实现按评论者/评审人维度的贡献（仅按 MR 作者）
- 不缓存请求结果
