---
name: melodyi-filebot
description: 用于电影、剧集、动画番剧的批量重命名与目录整理，输出符合 Jellyfin 规范的结构。当用户需要整理影视文件、重命名剧集、为 Jellyfin 准备媒体库时使用。
---

# melodyi-filebot

基于 TMDB 数据，对电影/剧集/番剧做批量重命名与目录整理，输出 Jellyfin 可直接识别的结构。P0 阶段仅做重命名与整理，不做刮削（NFO 生成在后续阶段）。

## 何时使用

- 用户有一个剧集/番剧完结（或部分季完结）后，需要批量重命名并整理目录
- 需要把 release 命名（含发布组、画质噪声）整理成 Jellyfin 标准结构
- 需要基于 TMDB 数据确认剧集身份与季/集结构

## 前置

代码位于 monorepo 的 `packages/melodyi-filebot/`，需先安装为 CLI：

```bash
pip install -e packages/melodyi-filebot
```

配置 TMDB API Key：环境变量 `TMDB_API_KEY`，或 `~/.melodyi-filebot/config.yaml` 中 `tmdb_api_key`。

## 工作流程

### 1. 提取关键字

从用户提供的文件夹/文件名提取搜索关键字。参考 `docs/search-heuristics.md` 的去噪规则。中文与罗马字并存时两者都保留。

### 2. 搜索与确认

```bash
melodyi-filebot search "关键字" --type tv --language zh-CN
```

- **0 结果**：按启发式回退（短标题、罗马字），仍无结果则询问用户
- **复数结果**：列出候选，请用户确认 tmdb_id
- **单一明确结果**：可直接进入下一步，但仍建议向用户展示命中

### 3. 获取摘要

```bash
melodyi-filebot fetch-summary <tmdb_id> --language zh-CN [--episodes <季号>]
```

返回剧/季/集的**结构摘要**（不含完整 overview）。注意：
- `overview_available=False` 或 `overview_length<10` 标记该处数据可能缺失（P1+ 用 Bangumi 补全）
- `episode_groups` 非空提示存在剧集组（重置版等非标场景，见启发式文档）

### 4. 构建计划

```bash
melodyi-filebot build-plan --show-id <tmdb_id> --source <源目录> --dest <目标根目录> --language zh-CN --out plan.json
```

默认走标准流程：文件按解析出的 S/E 放入 `Shows/剧名 (年) [tmdbid-xxx]/Season NN/剧名 (年) SxxEyy.ext`。电影用 `--movie-id`。

- 文件无法解析集号 → 出现在 `warnings`，需向用户确认如何处理
- 非标场景（episode group、季重排、集合并拆分）：P0 暂不支持自动覆盖，需向用户说明并降级为手动逐文件处理

### 5. 执行（默认 dry-run）

```bash
# 先 dry-run 校验
melodyi-filebot execute-plan --plan plan.json

# 确认无误后真正执行
melodyi-filebot execute-plan --plan plan.json --execute --snapshot snap.json
```

dry-run 会校验源文件存在、目标无冲突。执行时写事务日志 `snap.json`。

### 6. 回滚（如需）

```bash
melodyi-filebot undo snap.json
```

按逆序恢复原始目录结构（仅对 rename/move 可逆，不恢复已删除内容）。

## 输出目录结构（Jellyfin 规范）

```
Shows/剧名 (年) [tmdbid-xxx]/Season 01/剧名 (年) S01E01.mkv
Movies/电影名 (年) [tmdbid-xxx]/电影名 (年).mkv
```

- Season 文件夹必须写 `Season 01`（不写 `S01`）
- 多集合并：`S01E01-E02.mkv`；分段：`S01E01-part-1.mkv`
- 特别篇：`Season 00`

## 上下文占用

进上下文的只有搜索候选与结构摘要。完整 overview 不进上下文（由 CLI 内部处理，供后续 NFO 生成使用）。
