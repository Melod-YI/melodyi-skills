---
name: gitcode-pr-review
description: GitCode PR 代码检视工具。支持检视 PR 代码并提交评论，以及验收已提交的检视意见。当用户提供 GitCode PR 链接并请求代码检视或验收检视意见时调用。
---

# GitCode PR 代码检视工具

基于 `gitcode` CLI（需先 `pip install -e packages/gitcode`）封装 GitCode API。
所有 API 调用、token 读取由 CLI 内部处理——**不要**自行 curl 接口或读取配置中的秘钥。

## 前置

- 已安装 `gitcode` CLI（`pip install -e packages/gitcode`）
- token 已配置：环境变量 `GITCODE_TOKEN`，或 `~/.melodyi-skills/gitcode/config.json` 的 `gitcode_token`
- 验证配置：`gitcode user` 能返回当前用户即正常

## CLI 速查

| 命令 | 作用 | stdout |
|---|---|---|
| `gitcode user` | 当前 token 用户 | JSON |
| `gitcode pr <url>` | PR 详情（标题/描述/分支/状态） | JSON |
| `gitcode files <url>` | 变更文件列表 | JSON |
| `gitcode comments <url> [--mine]` | 评论列表；`--mine` 仅本人 | JSON |
| `gitcode comment <url> --path P --position N (--body T \| --body-file F) [--commit-id SHA]` | 提交行内评论 | JSON |
| `gitcode resolve <url> --discussion-id D [--unresolved]` | 更新评论解决状态 | JSON |

`<url>` 直接传用户给的 PR 链接，CLI 内部解析 owner/repo/number。

退出码：`0` 成功 / `1` 业务或网络错误 / `2` token 未配置或参数错误。

## 模式一：代码检视

示例请求：
- "请检视这个 PR: https://gitcode.com/owner/repo/-/merge_requests/123"

执行步骤：

1. **获取 PR 详情与变更文件**
   ```bash
   gitcode pr "<url>"            # 取标题、描述、源/目标分支
   gitcode files "<url>"         # 取变更文件列表
   ```

2. **进入/克隆代码目录**（git 操作，由 agent 执行）
   - 目录不存在则克隆：`git clone https://gitcode.com/{owner}/{repo}.git`
   - 已存在则拉取：`git fetch origin`
   - 切换到 PR 分支：`git checkout {source_branch} && git pull origin {source_branch}`
     或 `git fetch origin pull/{number}/head:pr-{number} && git checkout pr-{number}`
   - 非交互式 git 注意事项见末尾

3. **分析代码变更**
   - 用 Read 工具逐个读取变更文件，行号即 `comment --position` 所需的 PR 分支绝对行号（1-based）
   - 检视意见分两级：
     - **严重**：功能/性能/bug/安全等必须修复的问题 → 直接提交行内评论
     - **建议**：风格/命名/可维护性等改进 → 汇总后由用户选择提交

4. **提交检视意见**
   - 先查已有评论避免重复：`gitcode comments "<url>"`
   - **严重**级别直接提交（长内容/中文用 `--body-file`）：
     ```bash
     # 先把评论写入临时文件，再用 --body-file 提交
     gitcode comment "<url>" --path src/a.py --position 10 --body-file /tmp/c1.md
     ```
     评论内容以 `**[严重]** 问题描述及修改建议` 开头。
   - **建议**级别不直接提交，按严重度排序输出汇总：
     ```
     === 检视意见汇总 ===

     --- 严重级别（已自动提交）---
     1. [文件路径:行号] **[严重]** 问题描述

     --- 建议级别（待确认）---
     2. [文件路径:行号] **[建议]** 改进建议

     请输入需要提交的建议级别意见编号（如: 2），或输入 none 跳过：
     ```
     用户选择后，仅对选中项用 `gitcode comment ... --body-file` 提交。

## 模式二：验收检视意见

示例请求：
- "验收这个 PR 的检视意见: <url>"

执行步骤：

1. **获取本人提交的评论**
   ```bash
   gitcode comments "<url>" --mine
   ```

2. **逐条验证是否已修复**
   - 对每条评论，用 Read 检查对应 `path`:`position` 的当前代码
   - 判断问题是否已解决

3. **更新解决状态**
   - 已修复：`gitcode resolve "<url>" --discussion-id <id>`（默认 resolved）
   - 未修复：`gitcode resolve "<url>" --discussion-id <id> --unresolved`
   - `<id>` 取自 `comments` 输出中的 `id` 字段

## 评论格式

评论必须以级别标记开头：

```markdown
**[严重]** 问题描述及修改建议

**[建议]** 改进建议内容
```

## 检视要点

- 正确性：逻辑、边界、错误处理 → 严重
- 安全：输入验证、敏感信息、权限 → 严重
- 性能：算法效率、资源使用 → 严重
- 风格/命名/可维护性/可读性 → 建议

## 错误处理

| 退出码/状态 | 处理 |
|---|---|
| 退出码 2（token 缺失） | 提示用户配置 `GITCODE_TOKEN` 或 config.json |
| 401 | token 无效或过期 |
| 403 | token 权限不足 |
| 404 | 检查 owner/repo/number |
| 429 | 等待后重试 |

## 非交互式 git 注意事项

- 禁止 `git rebase -i`、无 `-m` 的 `git commit`、`git add -p` 等会弹编辑器的命令
- `git log`/`git diff` 必须禁用分页器：`git --no-pager log` 或设 `GIT_PAGER=cat`
- `git commit` 必须带 `-m`
- 私有仓克隆需带认证 URL（`https://token@gitcode.com/...`）或预配 credential helper，不要交互输入凭据
