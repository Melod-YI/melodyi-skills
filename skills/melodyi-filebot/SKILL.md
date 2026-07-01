---
name: melodyi-filebot
description: 用于电影、剧集、动画番剧的批量重命名与目录整理，输出符合 Jellyfin 规范的结构。当用户需要整理影视文件、重命名剧集、为 Jellyfin 准备媒体库时使用。
---

# melodyi-filebot

基于 TMDB 数据，对电影/剧集/番剧做批量重命名与目录整理，输出 Jellyfin 可直接识别的结构。**当前阶段：重命名与目录整理（P0）已完成；Bangumi 数据查询（P1）与 NFO 生成（P2，仅 TV）已就绪**（电影 NFO 与电影重命名留后）。

## 工作流程

### 0. 分析路径结构（建议第一步）

拿到用户给的路径后，先用 `analyze` 展开成层级树，了解结构与规模，再决定后续策略：

```bash
melodyi-filebot analyze <文件夹或文件路径> [--out structure.json] [--json]
```

默认输出**树状文本**：首层显示绝对路径、深层只显示文件/目录名，视频带 `HH:MM:SS` 时长，目录标注子树累计视频数。加 `--json` 改为 JSON 输出（视频时长为秒数，含每个节点的完整路径），便于程序解析。

**告警即停**：目录深度达到 5 层及以上，或文件总数超过 5000 时，只返回概要并停止——此时不要硬处理，先向用户说明结构过大/过深，确认如何缩小范围（按季拆分、分批等）。

### 1. 提取关键字

从用户提供的文件夹/文件名提取搜索关键字。参考 `reference/search-heuristics.md` 的去噪规则（去方括号发布组、画质噪声、季集标记；中文与罗马字并存时都保留作多关键字尝试）。

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
# 整剧摘要（季列表）
melodyi-filebot fetch-summary <tmdb_id> --language zh-CN
# 下钻某季：只拉取并展示该季集列表（不再搜索整剧）
melodyi-filebot fetch-summary <tmdb_id> --season <季号> --language zh-CN
# 列出剧集组（默认不输出；重置版等非标场景才需要）
melodyi-filebot fetch-summary <tmdb_id> --episode-groups
```

返回剧/季/集的**结构摘要**（不含完整 overview）。**逐层下钻**用法：先不带 `--season` 看整剧命中，确认后再加 `--season N` 只看某季的具体集信息。

不带 `--season` 时：
- `简介可用=否`：该处 overview 可能缺失（后续阶段用 Bangumi 补全）
- **剧集组默认不输出**：重置版等非标场景归在剧集组而非独立季，用 `--episode-groups` 列出（组ID | 名称 | 类型 | 集数，类型映射为可读名如「制作顺序」），再用 `episode-group <组ID>` 查看组的子组与集列表

带 `--season N` 时，只拉该季集列表（懒加载，不搜整剧），输出表头 + 内容表格：

```
TMDB id=46260 第 1 季 集列表
集号 | 名称 | 时长(分钟) | 简介长度
E01 | 第一集 | 24 | 50
E02 | 第二集 | 无数据 | 0
```

时长列 `无数据` 表示 TMDB 无该集时长数据（后续阶段用 Bangumi 补全）。

### 3.x 剧集组详情（非标场景1）

```bash
# 取某剧集组的子组结构 + 集列表（集带季号，因组可跨季）
melodyi-filebot episode-group <group_id> [--language zh-CN] [--json]
```

用于重置版等归在剧集组的情况。组 ID 由 `fetch-summary <tmdb_id> --episode-groups` 获取。输出按子组（如正片 + OVA）分段打印集列表。

### 3.5 Bangumi 数据查询（辅助数据源，P1）

当 TMDB 数据可疑或缺失（番剧小众、overview 为空/<10 字）时，可查 Bangumi 交叉核对。三个原语已就绪，匿名调用无需 token：

```bash
# 搜索动画条目（限定 type=2，返回 ≤10 条）
melodyi-filebot bangumi-search "莉可丽丝"
# 取某条目详情
melodyi-filebot bangumi-subject <bangumi_id>
# 取条目集列表（type：0=本篇 1=特别篇 2=OP 3=ED …，默认 0；自动翻页）
melodyi-filebot bangumi-episodes <bangumi_id> [--type 0]
```

均支持 `--json` 输出完整结构化数据。**默认文本输出统一为「列含义表头 + `|` 分隔行」表格，且只显示简介长度、不外泄完整简介内容**（agent 无需知道简介原文）；`--json` 才含完整 summary/desc。

> 注：这是独立查询工具，**尚未**接入 `fetch-summary --with-bangumi` 自动交叉校验（下一步）。Bangumi 条目 ID 与 TMDB ID 不同体系，需通过搜索匹配。

> 全局约定：所有命令默认静默（不输出日志），仅报错时输出错误；加 `-v/--verbose` 输出 INFO 级日志（请求/响应/命中数等）。所有列表型文本输出均为「列名表头 + `|` 分隔内容行」表格风格，不外泄完整简介（只显示简介长度，`--json` 才给完整）。

### 3.6 NFO 生成（P2）

由工具生成完整 NFO（Jellyfin 直接用、`lockdata=true` 全锁跳过刮削），4 步流程：

1. 确认信息源（TMDB id、bangumi subject、剧集组等，用 search/fetch-summary/bangumi-search/episode-group）。
2. `draft-plan` 生成纯映射 Plan（agent 编辑对象）。
3. agent 编辑 Plan（校正集号、补 bangumi、调整展示身份≠来源用于非标重排）。
4. `build-plan` 生成执行清单 → `execute-plan` 移动 + `generate-nfo` 写 NFO。

```bash
# step 2: folder→target 清单 → Plan（调 API 解析来源）
melodyi-filebot draft-plan --folder-spec folders.json --out plan.json

# step 4: Plan → 执行清单（move + nfo 操作）
melodyi-filebot build-plan --plan plan.json --dest <dest> --with-nfo --out exec.json

# step 4: 执行移动
melodyi-filebot execute-plan --plan exec.json --execute

# step 4: 写 NFO（默认 dry-run，--execute 真写）
melodyi-filebot generate-nfo --plan exec.json --execute
```

`folders.json` 结构：
```json
{"show":{"tmdb_id":154494,"bangumi_subject_id":364450},
 "folders":[{"path":"D:/src/S1","target":{"kind":"season","season":1}}]}
```

**Plan 集三块**：每个 episode 含 `file`（源）、`target`（展示身份：季/集，决定文件名/目录/NFO season-episode）、`source`（元数据来源：TMDB 坐标 + 可选 bangumi）。`target` 与 `source.tmdb` 可不同（物语 S00 重排：展示为 S01E05、元数据取自 S00E12，NFO 写 displayseason/displayepisode）。

**字段集**：参考真实 Jellyfin NFO 样例，含 plot/title/rating/genres/tags/studio/actor/uniqueid/fileinfo streamdetails/lockdata 等（详见 `specs/2026-07-01-nfo-generation-design.md` §3）。TMDB 为主源，overview 空/<10 字用 bangumi 补；TMDB 无该季（物语）整季取 bangumi。`lockdata=true` 全锁 + TMDB 图片 URL 写入 `<art>`。

> 注：P2 当前仅 TV（tvshow/season/episode NFO）。电影 NFO 与电影重命名留后。

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
- **伴生文件自动改名**：每个视频改名时，同目录下文件名以「视频 stem + `.`」开头的非视频文件（字幕 `.ass`/`.srt`、海报等 sidecar）会随之改名，目标名 = 改名后视频 stem + 原后缀（语言 token 如 `.TC` 原样保留，不猜测语言）。例如视频 `Show S01E01.mkv → 翼年代记 (2005) S01E01.mkv` 时，`Show S01E01.TC.ass` → `翼年代记 (2005) S01E01.TC.ass`。该逻辑对自动模式与 override（`--map`）模式同样生效；`draft-map` 仍只映射视频，伴生在 `build-plan` 阶段自动发现并跟随。stem 后非 `.` 的文件（如 `Show S01E01-extra.ass`）不被视为伴生。

**季/集归属不确定时用 override（draft-then-edit）**：季/集判断随机性大，不靠规则硬编码。当文件名无季标记且季归属不明、`[01-06]` 可能是 S00/S01、集号需重排、一文件多集/一集多文件、特别篇归季不明时，走 override：

```bash
# 1. 生成映射初版（不调 TMDB，含无法解析项 season/episode=null）
melodyi-filebot draft-map --show-id <tmdb_id> --source <源目录> [--season N] --out map.json

# 2. 对照 fetch-summary 编辑 map.json：修正每项的 season/episode/episode_end/part

# 3. 按显式映射构建计划（spec_applied=override，不解析文件名）
melodyi-filebot build-plan --map map.json --dest <目标根目录> --out plan.json
```

`--map` 与 `--source`/`--show-id`/`--movie-id`/`--season` 互斥。映射格式与自动/override 边界详见 `reference/search-heuristics.md`（或 `docs/search-heuristics.md`）。



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
- 伴生文件（字幕等）的 move 同样在 dry-run 校验范围内，并随 `--execute` 一起移动、写入事务日志
- `--execute`：真正执行，**一定会写事务日志**：
  - 未指定 `--snapshot` → 默认写到 `~/.melodyi-skills/melodyi-filebot/snapshots/<plan文件名>.snapshot.json`
  - 指定 `--snapshot` → 写到指定路径
  - 执行后回显日志路径与 undo 用法

### 6. 回滚（如需）

```bash
melodyi-filebot undo <snapshot路径>
```

按逆序恢复原始目录结构（仅对 rename/move 可逆，不恢复已删除内容）。