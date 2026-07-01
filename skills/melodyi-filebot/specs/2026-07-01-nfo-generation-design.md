# melodyi-filebot P2 · NFO 生成设计

- 日期：2026-07-01
- 状态：已与用户对齐 4 步流程与三份结构；基于 P1 bangumi 三原语 + 真实 Jellyfin NFO 样例 + Jellyfin 刮削机制研究
- 上游设计：见 `2026-06-23-melodyi-filebot-design.md` §6/§8 P2；本文件细化 NFO 字段集、计划书结构、来源解析、执行流程
- 范围：仅 TV（tvshow.nfo / season.nfo / `<file>.nfo`），电影留后

## 1. 目标与流程

由工具生成完整 NFO（Jellyfin 直接用、不在线刮削），支撑标准场景与四个非标场景（高达SEED 重置版、Re:Zero 季拆分、物语 S00 重排、集合并拆分）。

**4 步流程**：

1. **确认信息源**：agent 用 search/fetch-summary/bangumi-search/episode-group 等工具 + 与用户沟通，确认 TMDB id、bangumi subject、剧集组等来源。
2. **生成 Plan**：agent 输入 folder→(季|剧集组, bangumi?) 清单，app 扫描+解析+调 API 解析来源，输出**纯映射 Plan**（agent 看到并编辑的对象）。
3. **agent 编辑 Plan**：校正集号、补 bangumi、调整展示身份≠来源（物语重排）。
4. **生成执行清单并执行**：app 从 Plan 生成执行清单（move/nfo 操作），验证/dry-run/执行/回滚。

**核心原则**：Plan 是纯映射（剧/季/集 + 显式三块），不含 NFO 内容字段（overview/cast 等不进 agent 上下文）；NFO 内容在执行时由 CLI 按来源现拉现填。

## 2. 三份结构

### 2.1 Step 2 输入（folder→target 清单，agent 给）

```json
{
  "show": {"tmdb_id": 154494, "bangumi_subject_id": 364450},
  "folders": [
    {"path": "D:/src/莉可丽丝 S1", "target": {"kind": "season", "season": 1}},
    {"path": "D:/src/SEED-HD", "target": {"kind": "episode_group", "group_id": "67ffe4f983c6e567c7d95184"}}
  ]
}
```

- `show.bangumi_subject_id` 可选，剧级补全用。
- 每个 folder 可选带 `bangumi_subject_id`（该季 TMDB 缺失时用，物语情形）。
- `target.kind` = `season` | `episode_group`。

### 2.2 Plan（Step 2 输出 / Step 3 编辑对象，纯映射）

```json
{
  "show": {"tmdb_id":154494, "bangumi_subject_id":364450,
           "title":"莉可丽丝","year":2022, "language":"zh-CN"},
  "seasons": [
    {"season":1, "source":{"tmdb":{"tmdb_id":154494,"season":1},
                           "bangumi":{"subject_id":364450}}}
  ],
  "episodes": [
    {
      "file": "D:/src/莉可丽丝 S1/ep01.mkv",
      "target": {"season":1, "episode":1, "episode_end":null, "part":null},
      "source": {
        "tmdb": {"tmdb_id":154494, "season":1, "episode":1},
        "bangumi": {"subject_id":364450, "episode_id":1111258}
      }
    }
  ],
  "warnings": ["D:/src/.../unknown.mkv: 无法解析集号"]
}
```

**集三块**：
- `file`：源文件路径（唯一标识）。
- `target`：展示身份（季/集/[episode_end]/[part]）——决定文件名、目录、NFO 的 `<season>/<episode>` 与 `displayseason/displayepisode`。
- `source`：元数据来源（`tmdb` 坐标 + 可选 `bangumi` subject+episode_id）——决定拉取方式。

**关键**：`target` 与 `source.tmdb` 可不同（物语 S00 重排：`target=S01E05`，`source.tmdb=S00E12`，NFO 写 `displayseason=0/displayepisode=12`）。

**来源缺失**：TMDB 无该季（物语）→ `source.tmdb=null`，`source.bangumi` 为主；匹配不到 bangumi episode → `source.bangumi.episode_id=null` + warning，agent 手填。

### 2.3 执行清单（Step 4，app 从 Plan 生成，与 Plan 分离）

```json
{
  "operations": [mkdir/move…],
  "nfo_operations": [tvshow/season/episode nfo + source spec…],
  "warnings": […]
}
```

- `execute-plan` 读 `operations` 移动（含伴生字幕）。
- `generate-nfo` 读 `nfo_operations` 按来源拉取写 XML。
- 验证/dry-run/执行/回滚（事务日志）都在执行清单层。

## 3. 字段集（按 NFO 类型 + 来源映射）

参考真实 Jellyfin NFO 样例（无职转生），「尽量丰富」。`lockdata=true` 全锁。

### 3.1 `tvshow.nfo`

| 字段 | TMDB 来源 | bangumi 补充 |
|---|---|---|
| `plot`/`outline` | `overview` | `summary`（空/<10 时） |
| `title`/`originaltitle` | `name`/`original_name` | `name_cn`/`name` |
| `rating` | `vote_average` | `rating.score` |
| `year`/`premiered`/`releasedate`/`enddate` | `first_air_date`/`last_air_date` | `date` |
| `runtime` | `episode_run_time` | — |
| `genre`（多） | `genres` | — |
| `tag`（多） | `keywords`（append） | — |
| `studio`（多） | `networks` | — |
| `status` | `in_production`→Continuing/Ended | — |
| `mpaa` | `content_ratings`（append，可选） | — |
| `writer`/`credits`（多） | `created_by` | — |
| `actor`（name/role/type/sortorder） | `aggregate_credits` | — |
| `tmdbid`/`imdb_id`/`tvdbid` | `external_ids`（append） | — |
| `uniqueid` | tmdbid（default） | bangumi id（type=bgm，附加） |
| `lockdata`/`dateadded` | true / 生成时间戳 | — |
| `season`/`episode`=-1 | Jellyfin 占位 | — |

### 3.2 `season.nfo`

| 字段 | TMDB 来源 | bangumi 补充 |
|---|---|---|
| `plot`/`outline` | 季 `overview` | subject `summary`（季 TMDB 缺失时，物语） |
| `title` | 季 `name` | `name_cn` |
| `year`/`premiered`/`releasedate` | 季 `air_date` | subject `date` |
| `seasonnumber` | `season_number` | — |
| `tvdbid` | 季 external id | — |
| `actor`/`writer`/`credits` | 继承剧级 | — |
| `lockdata`/`dateadded` | true / 时间戳 | — |

### 3.3 `<file>.nfo`（episodedetails）

| 字段 | TMDB 来源 | bangumi 补充 |
|---|---|---|
| `plot` | 集 `overview` | `desc`（空/<10 时） |
| `title` | 集 `name` | `name_cn` |
| `showtitle` | 剧名 | — |
| `season`/`episode` | `target`（展示身份） | — |
| `aired` | `air_date` | `airdate` |
| `runtime` | `runtime` | `duration`（转分钟） |
| `rating` | `vote_average` | — |
| `director`/`writer`/`credits` | 集 `crew`（job=Director/Writer） | — |
| `actor`（含 GuestStar） | `guest_stars` + cast | — |
| `year`/`imdbid`/`tvdbid` | 集 external_ids | — |
| `uniqueid` | tmdbid+season+episode | bangumi episode id（附加） |
| `displayseason`/`displayepisode` | `target`≠`source.tmdb` 时写（特别篇重排） | — |
| `fileinfo`/`streamdetails` | **ffprobe** | — |
| `lockdata`/`dateadded` | true / 时间戳 | — |

### 3.4 图像（写入 NFO，配合 lockdata=true 全锁）

- `tvshow`：`<art><poster>https://image.tmdb.org/t/p/original{poster_path}</poster><fanart>...{backdrop_path}</fanart></art>`
- `season`：season `poster_path`；`episode`：`still_path`；`actor <thumb>`：`profile_path`
- TMDB 缺图 → bangumi subject `images` 兜底；仍无 → 省略该 art 元素
- 每类只取第一个（Jellyfin 规则）

### 3.5 主动不写

`episodeguide`（Jellyfin 内部 URL）、`anidbid`（TMDB 无此 id；agent 可手填）。`dateadded` 用生成时间戳。

## 4. bangumi 补全与来源解析

### 4.1 bangumi 字段补全

- 触发：TMDB 某实体 overview 为空或 `length<10`。
- 补：用 bangumi 同义字段（剧 `summary` / 集 `desc`）。仅 overview 类字段；cast/genres/ratings 等结构不同不补。
- 物语季级：整季 TMDB 无 → `season.source` 只有 bangumi，plot/title/airdate 全取 bangumi subject。

### 4.2 episode group 解析（folder→episode_group）

- app 调 `tmdb.get_episode_group(group_id)` 取子组+集列表（扁平化按 order）。
- 文件名序号（`[01]`/`E01`）→ 第 N 集 → 取其 `(season_number, episode_number)` 作 `source.tmdb` 坐标 + 默认 `target`。
- 高达SEED 1:1：target=source；重排时 agent 改 target 保留 source。

### 4.3 `draft-plan` 来源解析流程（Step 2 内部，对每个 folder）

1. 扫视频，解析文件名得序号。
2. `target.kind=season` → `get_season_episodes(tmdb_id, season)`，序号→集→`source.tmdb=(tmdb_id, season, N)`；`target.kind=episode_group` → `get_episode_group`，序号→第 N 集→`source.tmdb=(tmdb_id, ep.season, ep.episode)`。
3. 有 `bangumi_subject_id` → `get_subject_episodes`，按集号匹配→`source.bangumi.episode_id`；匹配不到→warning。
4. `target` 默认 = `source.tmdb` 的 (season, episode)；物语重排 agent 改 target（保留 source）。
5. TMDB 无该季（物语）→ `source.tmdb=null` + warning，`source.bangumi` 为主。
6. 未解析文件→warning。

## 5. 模块结构

```
melodyi_filebot/
├── models.py        # 扩展：Plan / EpisodeEntry / SeasonEntry / NfoSource / NfoOperation / ExecutionList
├── planner.py       # 扩展：draft-plan 来源解析；build-plan（Plan→ExecutionList）
├── nfo.py           # 新增：按来源拉取 + 生成 XML（tvshow/season/episode），含 ffprobe streamdetails、图片 URL
├── tmdb.py          # 已有 get_show_summary/get_season_episodes/get_episode_group；新增带 append 的详情拉取（external_ids/aggregate_credits/keywords/content_ratings）
├── bangumi.py       # 已有 get_subject/get_subject_episodes
├── ffprobe          # 复用 structure.py 的 ffprobe 能力
└── cli.py           # draft-plan / build-plan / execute-plan / generate-nfo
```

`nfo.py` 职责：给定 `NfoOperation`（来源 spec + 目标路径 + 季集），拉取 TMDB/bangumi 字段 → 按 §3 字段集组装 → 写 XML。TMDB 详情用 `append_to_response=external_ids,aggregate_credits,keywords,content_ratings` 一次性取全。

## 6. CLI 命令

```bash
# step 2: folder 清单 → Plan（调 API 解析来源）
# show 信息（tmdb_id + 可选 bangumi_subject_id）与 folders 都在 folder-spec JSON 里
melodyi-filebot draft-plan --folder-spec folders.json --out plan.json

# step 3: agent 编辑 plan.json

# step 4: Plan → 执行清单（move + nfo 操作）
melodyi-filebot build-plan --plan plan.json --dest <dest> --with-nfo --out exec.json

# step 4: 执行移动
melodyi-filebot execute-plan --plan exec.json --execute

# step 4: 写 NFO（默认 dry-run 列来源，--execute 真写）
melodyi-filebot generate-nfo --plan exec.json --execute
```

`folders.json` 即 §2.1 的输入结构（`show` + `folders`）。也支持 `--show-id`/`--source`/`--season` 等便捷 flags 作为单 folder 的糖（等价生成 folder-spec），多 folder 场景用 JSON。

`generate-nfo` 默认 dry-run（列出将写哪些 nfo 文件、来源是什么），`--execute` 真正拉取写盘。NFO 写入失败不回滚已移动文件（move 与 nfo 解耦，nfo 可独立重跑）。

## 7. 错误处理

- `draft-plan`：解析失败/来源匹配不到 → 写 warning 进 Plan，不中断；agent 据此补全。
- `generate-nfo`：单条 nfo 拉取/写盘失败 → 记 error 日志 + 继续其余；`--execute` 不因部分失败回滚 move（已解耦）。
- ffprobe 不可用 → 省略 streamdetails + warning，不致命。
- TMDB/bangumi 网络错误 → 友好报错（沿用 `_report_error`）。

## 8. 测试策略

- `test_nfo.py`：XML 生成（tvshow/season/episode，mock TMDB/bangumi → 断言关键字段/`lockdata=true`/`uniqueid`/`displayseason`）；bangumi 补全（TMDB overview 空→bangumi 填）；图片 URL 构造；ffprobe streamdetails（mock）。
- `test_planner.py`：`draft-plan`（folder input→Plan，mock → 断言结构+warnings）；episode group 解析；物语季 bangumi 来源；target≠source 重排。
- `test_cli.py`：`draft-plan`/`build-plan`/`generate-nfo` 命令（dry-run/execute）。
- integration：真实 TMDB/bangumi 莉可丽丝（默认 skip，`--run-integration`）。

## 9. 与 P0 既有结构的关系（迁移）

- 新 `Plan` 结构取代 `PlanMap`（Plan 是 PlanMap 的超集：增加 `seasons[]`、每集显式 `source` 三块、`warnings`）。
- `draft-plan` 取代 `draft-map`（`draft-map` 的无 API 文件名解析被 `draft-plan` 涵盖，`draft-plan` 额外调 API 解析来源）。
- `build-plan` 改为消费新 `Plan`，产出 `ExecutionList`（原 `BuildPlanResult` 扩展 `nfo_operations`）。
- 旧 `draft-map`/`PlanMap`/`build-plan --map` 在实现时逐步迁移/废弃；P0 既有测试相应调整。

## 10. 范围外（YAGNI / 留后）

- 电影 NFO（`movie.nfo`）——TV 完成后再加，是 TV 的子集。
- `anidbid` 获取（TMDB 无此 id；agent 手填或后续接 AniDB 源）。
- `lockedfields` 字段级锁（当前用 `lockdata=true` 全锁；字段级锁留后）。
- 多图像/季封面自定义选择（当前每类取第一个）。
- NFO 内容字段进 Plan（违背「不进上下文」原则，不做）。
