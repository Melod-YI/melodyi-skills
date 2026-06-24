---
name: melodyi-filebot
description: 用于电影、剧集、动画番剧的批量重命名与目录整理，输出符合 Jellyfin 规范的结构。当用户需要整理影视文件、重命名剧集、为 Jellyfin 准备媒体库时使用。
---

# melodyi-filebot

基于 TMDB 数据，对电影/剧集/番剧做批量重命名与目录整理，输出 Jellyfin 可直接识别的结构。**当前阶段（P0）仅做重命名与目录整理，不做刮削**（NFO 生成、Bangumi 双源、非标场景自动处理在后续阶段）。

## 工作流程

### 1. 提取关键字

从用户提供的文件夹/文件名提取搜索关键字。参考 `docs/search-heuristics.md` 的去噪规则（去方括号发布组、画质噪声、季集标记；中文与罗马字并存时都保留作多关键字尝试）。

### 2. 搜索与确认

```bash
# 单类型搜索
melodyi-filebot search "刀剑神域" --type tv --language zh-CN
# 混合搜索（同时返回 tv 与 movie，输出用 [tv]/[movie] 区分）
melodyi-filebot search "刀剑神域" --type multi
```

输出示例：`[tv] tmdb_id=45782 | 刀剑神域 (2012) | original=ソードアート・オンライン | overview_len=299`

- **0 结果**：按启发式回退（短标题、罗马字），仍无结果则询问用户
- **复数结果**：列出候选，请用户确认 tmdb_id
- **单一明确结果**：可直接进入下一步，但仍建议向用户展示命中

> 已知案例：`莉可丽丝：友谊是时间的窃贼` 直接搜无结果——它是《莉可丽丝》(tmdb_id=46260) 的 S00 特别篇。回退搜 `莉可丽丝` 命中主剧，文件 `[01-06]` 映射到 `Season 00`。详见 `docs/search-heuristics.md`。

### 3. 获取摘要

```bash
melodyi-filebot fetch-summary <tmdb_id> --language zh-CN [--episodes <季号>]
```

返回剧/季/集的**结构摘要**（不含完整 overview）。注意：
- `overview_available=False` 或 `overview_length<10`：该处数据可能缺失（后续阶段用 Bangumi 补全）
- `episode_groups` 非空：存在剧集组（重置版等非标场景，P0 不自动处理，仅提示）
- `--episodes <季号>`：展开该季集列表（懒加载，避免一次性拉取全部集信息）

### 4. 构建计划

```bash
# 剧集
melodyi-filebot build-plan --show-id <tmdb_id> --source <源目录> --dest <目标根目录> --language zh-CN --out plan.json
# 电影
melodyi-filebot build-plan --movie-id <tmdb_id> --source <源目录> --dest <目标根目录> --out plan.json
```

`--show-id` 与 `--movie-id` 二选一。计划写入 `--out` 指定文件并打印到 stdout。

默认标准流程：文件按解析出的 S/E 放入目标结构。注意：
- 季号优先从**文件名**解析（`S01E01`、`[01]` 等）。源目录的文件夹结构（如 `Season 2/`）**不被读取**作季来源。
- **多季剧、源目录只是其中一季**：若文件名带季标记（`S02E01`）直接正确归类；若文件名**不带**季标记（番剧常见的 `[01]..[12]`），用 `--season N` 指定这一季的季号（文件名有显式季标记如 `S00` 特别篇仍以文件名为准，不被覆盖）。`--season` 仅适用于剧集。
- 文件无法解析集号，或其他非标场景 → 出现在 `warnings`，需向用户确认如何处理



### 5. 执行（默认 dry-run，必留事务日志）

```bash
# 先 dry-run 校验（不改动文件）
melodyi-filebot execute-plan --plan plan.json

# 确认无误后真正执行
melodyi-filebot execute-plan --plan plan.json --execute

# 也可显式指定日志路径（一般无需指定）
melodyi-filebot execute-plan --plan plan.json --execute --snapshot /path/to/snap.json
```

- dry-run：校验源文件存在、目标无冲突，不执行不写日志
- `--execute`：真正执行，**一定会写事务日志**：
  - 未指定 `--snapshot` → 默认写到 `~/.melodyi-filebot/snapshots/<plan文件名>.snapshot.json`
  - 指定 `--snapshot` → 写到指定路径
  - 执行后回显日志路径与 undo 用法

### 6. 回滚（如需）

```bash
melodyi-filebot undo <snapshot路径>
```

按逆序恢复原始目录结构（仅对 rename/move 可逆，不恢复已删除内容）。