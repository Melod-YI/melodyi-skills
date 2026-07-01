---
name: gitcode-contribution
description: GitCode 用户贡献采集工具。当用户想统计某用户在某 GitCode 仓库的总贡献（MR 清单、增减行、测试/非测试拆分）时调用。需提供用户名与仓库地址。
---

# GitCode 用户贡献采集工具

基于 `gitcode` CLI（需先 `pip install -e packages/gitcode`）采集某用户在某 GitCode 仓库的全部 MR 贡献，
输出 Markdown 汇总报告。所有 API 调用、token 读取由 CLI 内部处理——**不要**自行 curl 或读秘钥。

## 前置

- 已安装 `gitcode` CLI（`pip install -e packages/gitcode`）
- token 已配置：环境变量 `GITCODE_TOKEN`，或 `~/.melodyi-skills/gitcode/config.json` 的 `gitcode_token`
- 验证：`gitcode user` 能返回当前用户即正常

## CLI 速查（本 skill 用到的）

| 命令 | 作用 | stdout |
|---|---|---|
| `gitcode prs <仓库URL> --author <用户> --state all` | 列出该用户在该仓库的全部 PR（含已合并/已关闭/开放，内部分页） | JSON 数组 |
| `gitcode files <pr-url>` | 某 PR 的变更文件列表（含 filename/additions/deletions，内部分页） | JSON 数组 |

`prs` 返回的每个 PR 对象关键字段：`number` / `title` / `state`(`open`/`closed`/`merged`) / `user.login` /
`added_lines` / `removed_lines` / `html_url` / `merged_at` / `closed_at`。
`files` 返回的每个文件对象关键字段：`filename` / `status` / `additions`(string) / `deletions`(string)。

退出码：`0` 成功 / `1` 业务或网络错误 / `2` token 未配置或参数错误。

## 采集流程

输入：用户名（如 `Melod-YI`）+ 仓库地址（如 `https://gitcode.com/openJiuwen/jiuwenswarm`）。

1. **列出全部 MR**
   ```bash
   gitcode prs "https://gitcode.com/openJiuwen/jiuwenswarm" --author "Melod-YI" --state all
   ```
   - `--state all` 必须带，才能覆盖已合并 + 已关闭 + 开放三种状态
   - 得到 MR 清单。若无 MR，直接报告"该用户在该仓库无 MR"并结束

2. **逐 MR 取变更文件**
   对每个 MR，构造其 PR URL（`https://gitcode.com/{owner}/{repo}/-/merge_requests/{number}`），执行：
   ```bash
   gitcode files "<pr-url>"
   ```
   - 单个 MR 取文件失败时：在报告里标注该 MR"取文件失败"，跳过其测试/非测试拆分，
     但仍保留在 MR 清单中、并计入 PR 自带的 `added_lines`/`removed_lines` 总增删，**不中断**整体采集

3. **分类每个文件为 测试 / 非测试**（只看路径文件名，不读内容）

   文件归为"测试"当且仅当满足任一：
   - 路径任一段 ∈ {`test`, `tests`, `__tests__`, `spec`, `specs`, `__mocks__`}
   - 文件名去扩展名后以 `test_` 开头，或以 `_test` / `_spec` 结尾
   - 文件名扩展名前一段为 `test` 或 `spec`（即 `*.test.*` / `*.spec.*` 形态）

   其余一律"非测试"（含配置类 `.yml`/`.json`/`Makefile`/`.md` 等）。

4. **汇总**

   - 每个 MR 计算：增 = Σ additions、删 = Σ deletions（按文件累加，`additions`/`deletions` 是字符串需转 int）
   - 测试增/删 = 仅测试文件累加；非测试增/删 = 仅非测试文件累加
   - 交叉校验：MR 的 `added_lines`/`removed_lines`（PR 自带总增删）应 ≈ 文件累加值；若不一致，以文件累加为准并在报告脚注说明偏差

5. **输出 Markdown 报告**（见下文格式）

## Markdown 报告格式

```markdown
# {用户} 在 {owner}/{repo} 的贡献汇总

共 {N} 个 MR（已合并 {X} / 已关闭 {Y} / 开放 {Z}）。

| # | 标题 | 状态 | 增 | 删 | 测试增 | 测试删 | 非测试增 | 非测试删 |
|---|------|------|---|---|--------|--------|----------|----------|
| 12 | feat: xxx | merged | 120 | 30 | 40 | 5 | 80 | 25 |
| 13 | fix: yyy | closed | 10 | 2 | 0 | 0 | 10 | 2 |

**合计**：增 {总增} / 删 {总删}；测试增 {测试增} / 测试删 {测试删}；非测试增 {非测试增} / 非测试删 {非测试删}。
```

- 标题过长可截断
- 状态列直接用 `merged`/`closed`/`open`
- 取文件失败的 MR：拆分四列填 `N/A`，但增/删两列用 PR 自带 `added_lines`/`removed_lines`
- 若有交叉校验偏差，末尾加一行脚注说明

## 错误处理

| 退出码/状态 | 处理 |
|---|---|
| 退出码 2（token 缺失） | 提示用户配置 `GITCODE_TOKEN` 或 config.json，终止 |
| 401 | token 无效或过期，终止 |
| 403 | token 权限不足，终止 |
| 404 | 检查 owner/repo 是否正确 |
| 429 | 等待后重试该次请求 |
| 单 MR 取文件失败 | 标注跳过，继续其余 MR |
