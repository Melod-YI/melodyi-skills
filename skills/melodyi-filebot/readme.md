---
name: melodyi-filebot
description: 用于电影、剧集、动画番剧的批量重命名与目录整理，输出符合 Jellyfin 规范的结构。当用户需要整理影视文件、重命名剧集、为 Jellyfin 准备媒体库时使用。
---

# melodyi-filebot

基于 TMDB 数据，对电影/剧集/番剧做批量重命名与目录整理，输出 Jellyfin 可直接识别的结构。**当前阶段（P0）仅做重命名与目录整理，不做刮削**（NFO 生成、Bangumi 双源、非标场景自动处理在后续阶段）。

## 能力边界（P0）

**已支持：**
- 按关键字搜索 TMDB（tv / movie / multi，multi 结果区分每条的真实类型）
- 获取剧的结构摘要（季/集结构、overview 是否可用、是否存在剧集组），**不含完整 overview**，节省上下文
- 基于解析出的季/集编号，生成符合 Jellyfin 规范的重命名 + 目录整理计划
- dry-run 校验（源存在、目标无冲突）后执行；执行必留事务日志，可回滚

**暂不支持（后续阶段）：**
- NFO 刮削文件生成
- Bangumi 交叉校验与数据补全
- 非标场景的自动覆盖（episode group 重置版、季拆分/重排、集合并拆分）——P0 遇到需向用户说明并降级为手动逐文件处理

## 何时使用

- 用户有一个剧集/番剧完结（或部分季完结）后，需要批量重命名并整理目录
- 需要把 release 命名（含发布组、画质噪声）整理成 Jellyfin 标准结构
- 需要基于 TMDB 数据确认剧集身份与季/集结构

## 前置

代码位于 monorepo 的 `packages/melodyi-filebot/`，需先安装为 CLI：

```bash
pip install -e packages/melodyi-filebot
```

配置 TMDB API Key（二选一）：
- 环境变量 `TMDB_API_KEY`
- 配置文件 `~/.melodyi-skills/melodyi-filebot/config.yaml`：
  ```yaml
  tmdb_api_key: 你的key
  ```

`~/.melodyi-skills/melodyi-filebot/` 是本工具的统一数据目录，存放配置文件与事务日志快照（`snapshots/` 子目录）。

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
- 文件无法解析集号 → 出现在 `warnings`，需向用户确认如何处理
- 非标场景 → `warnings` 提示，P0 不自动覆盖，降级为手动处理

### 5. 执行（默认 dry-run，必留事务日志）

```bash
# 先 dry-run 校验（不改动文件）
melodyi-filebot execute-plan --plan plan.json

# 确认无误后真正执行
melodyi-filebot execute-plan --plan plan.json --execute
# 也可显式指定日志路径
melodyi-filebot execute-plan --plan plan.json --execute --snapshot /path/to/snap.json
```

- dry-run：校验源文件存在、目标无冲突，不执行不写日志
- `--execute`：真正执行，**一定会写事务日志**：
  - 未指定 `--snapshot` → 默认写到 `~/.melodyi-skills/melodyi-filebot/snapshots/<plan文件名>.snapshot.json`
  - 指定 `--snapshot` → 写到指定路径
  - 执行后回显日志路径与 undo 用法

### 6. 回滚（如需）

```bash
melodyi-filebot undo <snapshot路径>
```

按逆序恢复原始目录结构（仅对 rename/move 可逆，不恢复已删除内容）。

## 输出目录结构（Jellyfin 规范）

```
Shows/剧名 (年) [tmdbid-xxx]/Season 01/剧名 (年) S01E01.mkv
Movies/电影名 (年) [tmdbid-xxx]/电影名 (年).mkv
```

- Season 文件夹写 `Season 01`（不写 `S01`）
- 多集合并：`S01E01-E02.mkv`；分段：`S01E01-part-1.mkv`
- 特别篇：`Season 00`
- 目标路径会做归一化：去尾斜杠、转平台原生分隔符，输入带不带斜杠均一致

## 上下文占用

进上下文的只有搜索候选与结构摘要。完整 overview 不进上下文（由 CLI 内部处理，供后续 NFO 生成使用）。剧集元数据较大且大部分对流程判断无意义，仅摘要（title + 结构）进入上下文。
