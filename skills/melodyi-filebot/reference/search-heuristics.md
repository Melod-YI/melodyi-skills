# 搜索启发式

本文件供 agent 在解析文件名、选择搜索关键字、判断 TMDB 数据是否符合用户理解时参考。随用例累积。

## 关键字提取

文件名常包含发布组、画质、编码等噪声。提取顺序：

1. 去除方括号 `[...]` 中的发布组/规格标记（如 `[VCB-Studio]`、`[Bilibili WEB-DL 1080p]`）
2. 去除尾部规格噪声（`1080p`、`2160p`、`WEB-DL`、`H265`、`AAC`、`Ma10p_1080p` 等）
3. 去除季/集标记（`S01`、`S01E01`、`[01-06]`）
4. 剩余部分作为候选标题；中文与罗马字/英文并存时，两者都保留作多关键字尝试

### 示例

| 原始文件名 | 提取关键字 |
|---|---|
| `Gundam.Build.Fighters.2013.S01E01.2160p.WEB-DL.H265.AAC-PTerWEB.mp4` | `Gundam Build Fighters` |
| `[VCB-Studio] Amagami SS+ Plus [10][Ma10p_1080p][x265_flac_aac].mkv` | `Amagami SS+ Plus` |
| `[Prejudice-Studio] 莉可丽丝：友谊是时间的窃贼 Lycoris Recoil_ Friends are thieves of time [01-06]...` | `莉可丽丝：友谊是时间的窃贼` → 回退到 `莉可丽丝` / `Lycoris Recoil` |

## 搜索回退策略

长标题 0 结果时：

1. 退到短主标题（冒号/空格前的部分）
2. 退到罗马字/英文标题
3. 仍无结果 → 询问用户

## 已知案例

### 莉可丽丝：友谊是时间的窃贼

- 现象：直接搜 `莉可丽丝：友谊是时间的窃贼` 无结果
- 原因：TMDB 把这部 OVA/特别篇归在《莉可丽丝》(tmdb_id=46260) 的 S00 特别篇下，而非独立条目
- 处理：回退搜 `莉可丽丝` → 命中主剧 → 文件 `[01-06]` 映射到 `Season 00/S00E01-E06`
- 规则沉淀：`xxx：副标题` 形式、资源方单列的剧场版/OVA/特别篇，常对应 TMDB 的 S00

<!-- ## 非标场景（P3 验证，此处先记录特征）

### 1. 剧集组（如高达SEED重置版）

- 特征：TMDB 把重置版放在「剧集组」(episode group) 而非独立季
- 识别：`fetch-summary` 返回的 `episode_groups` 非空
- 处理方向：取 episode group 详情，按 group 的季/集结构重命名

### 2. 多季被塞进 S01（如 Re:Zero）

- 特征：观众认多季，TMDB 全在 S01
- 识别：S01 集数异常多（>26）、跨年
- 处理方向：基于原始文件夹季标注/用户指示拆分

### 3. S00 拆分到不同季（如物语系列）

- 特征：部分季在 S00，观看顺序错乱
- 识别：S00 集数多、有明确剧情编号
- 处理方向：按放送顺序重排，airsbefore_season 等控制播放

### 4. 集合并/拆分

- 特征：一个文件对应多集，或一集拆多文件
- 处理方向：`S01E01-E02`、`S01E01-part1` 命名 -->


## 自动处理 vs override 边界（季/集归属判断）

季/集归属判断（"这批文件属于哪一季、每集对应哪一集"）有较大随机性，不靠规则硬编码。原则：

### 可交给 CLI 自动处理（draft-plan 默认行为）

满足以下条件之一，可按文件名解析：

- 文件名含可解析的季/集标记：`S01E01`、`S01E01-E02`（范围）、`S01E01-part-1`（分段）、`[01]`（方括号集号）、`E01`
- 且季号要么在文件名中，要么能在 folder-spec 的 `target.season` 中明确给定（如源目录是某一季但文件名无 S 标记）

### 需要 override（draft-plan → 编辑 Plan → build-plan --plan）

出现以下任一情况，自动解析不可靠或会错，应走 override（即 agent 编辑 Plan）：

- **季归属不确定**：文件名无季标记，且无法确定是第几季（如 `[01]..[12]` 不知是 S1 还是 S2）
- **集号歧义**：`[01-06]` 可能是 S00 特别篇也可能是 S01 正篇
- **集号需重排**：文件编号与 TMDB 集号不一致（如重置版调整了集序）
- **一文件对应多集**：需指定 `episode_end`（如 `S01E01-E02`）
- **一集拆多文件**：需指定 `part`（如 `S01E01-part-1`）
- **特别篇归季不明**：S00 的某些集实际属于某季中间

### override 工作流

1. `melodyi-filebot draft-plan --folder-spec spec.json --out plan.json`
   按 folder→target 清单调 TMDB/Bangumi 解析来源，生成 Plan 初版（含无法解析项的告警）。
2. agent 用 `fetch-summary <id>` 对照季/集结构，编辑 `plan.json`：直接修改 `episodes[].target.season/episode/episode_end/part`，必要时增删 `episodes[]` 与 `seasons[]` 条目。
3. `melodyi-filebot build-plan --plan plan.json --dest <目标> --with-nfo --out build.json`
   按编辑后的 Plan 构建执行清单（`spec_applied="plan"`）。
4. `execute-plan` dry-run 校验 → `--execute` 执行。

### Plan 结构（agent 编辑对象）

```json
{
  "show": {"tmdb_id": 46260, "language": "zh-CN"},
  "seasons": [{"season": 1, "source": {"provider": "tmdb", "tmdb_id": 46260, "season": 1}}],
  "episodes": [
    {"file": "/abs/path/file.mkv",
     "target": {"season": 1, "episode": 1, "episode_end": null, "part": null},
     "source": {"provider": "tmdb", "tmdb_id": 46260, "season": 1, "episode": 1}}
  ],
  "warnings": []
}
```

季来源由 `seasons[].source` 指定，集来源由 `episodes[].source` 指定（TMDB 缺季时可切 `provider="bangumi"`）。
