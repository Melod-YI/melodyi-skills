# melodyi-filebot 设计文档

- 日期：2026-06-23
- 状态：已与用户确认 §1-§3，§4-§7 已按反馈修订；NFO 详细设计延后至 P2 前重新讨论
- 范围：完整愿景 + 阶段划分，先实现 P0

## 1. 背景与目标

模拟 filebot 的能力，为电影、剧集、动画番剧做批量重命名与目录整理，输出可直接被 Jellyfin 识别（必要时跳过 Jellyfin 自身刮削）的结构。

核心诉求：

1. 调用 TMDB API，按关键字查找剧集信息
2. 执行文件重命名、创建文件夹、移动文件/文件夹（通过终端命令）
3. 默认处理方式 + 在用户额外指示、TMDB 搜索出复数/空/异常结果时向用户确认
4. 必要时直接完成刮削，跳过 Jellyfin 刮削（TMDB 数据异常、不符合用户预期时）
5. 优先考虑剧集完结或部分季完结后的批量场景，不考虑高频单文件处理
6. 对动画番剧，引入 Bangumi 作为辅助数据源，交叉校验 TMDB「不符合用户理解」的情况，并在 TMDB 数据缺失时填充

数据源取向：

- 优先填充 TMDB 数据（演职人员关联、季合并等优势）
- 用 Bangumi 判断 TMDB 是否「不符合用户理解」
- TMDB 数据无法使用或缺内容（如小众番剧缺单集简介）时用 Bangumi 填充
- 仅当 TMDB 某集/某季介绍为空或明显过短（长度 <10）时，才用 Bangumi 数据填充

## 2. 整体架构与目录布局

运行形态：**SKILL.md + Python 辅助 CLI**。SKILL.md 指导 agent 编排流程与确认时机；Python CLI 封装 API 调用、摘要压缩、计划构建、NFO 生成、文件操作。agent 只处理摘要与决策，完整元数据不进上下文。遵循 monorepo 约定：CLI 代码放 `packages/melodyi-filebot/`，轻量 `SKILL.md` 放 `skills/melodyi-filebot/`。

```
packages/melodyi-filebot/          # CLI 包（pip install -e 安装）
├── pyproject.toml
├── melodyi_filebot/               # Python 包
│   ├── cli.py            # Click 入口：search/fetch-summary/build-plan/execute-plan/undo
│   ├── tmdb.py           # TMDB 调用（初期 import tmdbsimple，后续或自实现）
│   ├── bangumi.py        # Bangumi v0 调用（P1 引入）
│   ├── summarize.py      # 原始元数据 → 进上下文的摘要
│   ├── planner.py        # 构建重命名/整理/NFO 计划
│   ├── nfo.py            # NFO 生成（P2 引入，P2 前重新设计）
│   └── fsops.py          # 文件扫描、重命名、移动、事务日志、undo
└── tests/

skills/melodyi-filebot/            # 轻量 skill（sync-skills.sh 同步）
├── SKILL.md
├── docs/
│   └── search-heuristics.md  # 知识沉淀文档（随 skill 发布，可累积）
└── specs/                    # 本设计文档
```

### 职责边界

- **agent（SKILL.md 驱动）**：文件名语义解析、关键字提取、候选消歧、用户确认、非标场景的映射决策
- **CLI（Python）**：API 调用、摘要压缩、计划构建、NFO 生成、文件操作
- **进上下文的只有**：搜索候选摘要、剧/季/集结构摘要、计划 diff。完整 overview、credits、images 等不进上下文

### 配置

- TMDB key：环境变量 `TMDB_API_KEY` 或 `~/.melodyi-filebot/config.yaml`
- Bangumi token：可选（匿名 + UA 即可，参考 dantalian 实现）

## 3. 关键字解析与搜索策略（含知识沉淀）

典型痛点：`[Prejudice-Studio] 莉可丽丝：友谊是时间的窃贼 Lycoris Recoil_ Friends are thieves of time [01-06]...` 直接搜长标题会 0 结果或错配——资源方视角是「单独一季」，但 TMDB 把它归在《莉可丽丝》主剧的 S00 特别篇。处理为多级回退：

1. agent 解析文件名，提取候选关键字（主标题、副标题分别保留，如 `莉可丽丝` + `友谊是时间的窃贼`）
2. `search` 命令支持多关键字尝试：先长标题 → 0 结果则退到短主标题；对结果做 S00/特别篇命中提示
3. 知识沉淀文档 `docs/search-heuristics.md`（随用例累积）：
   - 已知易错案例（如本例：`xxx：副标题` 形式多为 TMDB 的 S00 特别篇）
   - 启发式规则（资源方单列的剧场版/OVA/特别篇常对应 TMDB S00；重置版常落在 episode group）
   - 检索失败时的备选关键词构造法
4. 仍无法判定 → 询问用户：把候选 + 命中位置摆给用户确认

### 文件名示例（用于关键字提取测试）

文件夹名：
- `[WEBrip] Super no Ura de Yani Suu Futari S01 [ktnbytes]`
- `[Prejudice-Studio] 莉可丽丝：友谊是时间的窃贼 Lycoris Recoil_ Friends are thieves of time [01-06][Bilibili WEB-DL 1080p AVC 8bit AAC MP4][简日内嵌]`
- `高达创战者.Gundam.Build.Fighters.2013.S01.2160p.WEB-DL.H265.AAC-PTerWEB`

文件名：
- `Gundam.Build.Fighters.2013.S01E01.2160p.WEB-DL.H265.AAC-PTerWEB.mp4`
- `[VCB-Studio] Amagami SS+ Plus [10][Ma10p_1080p][x265_flac_aac].mkv`
- `Super no Ura de Yani Suu Futari 2026 S01E01-[1080p][WEBRIP][AV1.AAC].mkv`

## 4. 数据流与摘要格式

核心原则：**进上下文的只有摘要和计划，完整元数据只用于 NFO 生成**。

### `fetch-summary` 返回结构

```json
{
  "show": {
    "tmdb_id": 46260,
    "title": "莉可丽丝",
    "original_title": "リコリス・リコイル",
    "year": 2022,
    "total_seasons": 1,
    "total_episodes": 13,
    "overview_available": true,
    "overview_length": 245
  },
  "seasons": [
    {
      "season_number": 0,
      "name": "Specials",
      "episode_count": 6,
      "first_air_date": "2022-09-28",
      "last_air_date": "2023-02-22",
      "overview_available": true
    }
  ],
  "episode_groups": [
    {"id": "abc123", "name": "HD Remaster", "type": 1}
  ],
  "episodes": {
    "lazy": true,
    "note": "使用 fetch-summary --episodes 获取具体集摘要"
  }
}
```

设计要点：
- `overview_available` / `overview_length` 标记而非原文，agent 据此判断是否需 Bangumi 补全
- `episode_groups` 列出可用剧集组（非标场景1 需要）
- episodes 默认不展开，需要时用 `--episodes` 取具体集摘要（如 `S01E01: "标题", overview_len=180`）
- 完整 overview、credits、images 等只在 NFO 生成时由 CLI 内部读取，不进 agent 上下文

### `build-plan` 返回结构

```json
{
  "operations": [
    {"type": "mkdir", "path": "Shows/莉可丽丝 (2022) [tmdbid-46260]/Season 01"},
    {"type": "move", "source": ".../莉可丽丝 S01E01.mkv", "target": ".../Season 01/莉可丽丝 (2022) S01E01.mkv"}
  ],
  "spec_applied": "standard",
  "warnings": ["S00 有 6 集，可能需要手动确认归属"]
}
```

P0 不含 `nfo` 类型操作。`spec_applied` 仅作为汇报字段，标识本计划是标准流程还是 agent 构造的自定义映射（如 episode group / 季重排 / 集合并拆分），**不是 CLI 的模式开关参数**——映射内容由 agent 决定（见 §5）。

## 5. 非标场景：agent 自由 + 通用执行

**不**做 `--season-split`/`--season-remap`/`--episode-map`/`--episode-group` 这类模式开关（一定有覆盖不到的情况）。改为：

- **agent 负责决策映射**：读取摘要后，用自然语言理解构造一份「目标结构 spec」（文件 → 目标季/集/[part]/[合并] 的映射），覆盖任意场景
- **CLI 职责收敛为三件事**：① 按需提供数据（`fetch-summary` 可暴露 episode group 详情、集列表）；② 校验 spec 合法性（目标路径无冲突、季集编号合理）；③ 执行 + 记事务日志
- **四个历史场景退化为「示例映射」**，写进 `search-heuristics.md` 作为 agent 参考，而非 build-plan 的内置分支
- 真正遇到 spec 表达不了的极端情况，agent 在 SKILL.md 流程里降级为「手动逐文件操作 + 询问用户」

### 四个历史非标场景（作为示例，P3 验证）

1. 《机动战士高达SEED》重置版：TMDB 把重置版放在「剧集组」而非独立季。→ agent 从 `fetch-summary` 的 `episode_groups` 取 group 详情，构造按 group 结构的映射，重命名（及后续 NFO）按 group 信息填充
2. **《Re:Zero》全塞 S01**：TMDB 把多季塞在第一季。→ agent 基于原始文件夹季标注/用户指示，构造把 S01E26-50 拆为 S02 的映射
3. **《物语系列》S00 拆分**：部分季被合并进 S00，观看顺序错乱。→ agent 根据知识沉淀/放送顺序，构造 S00E01→S01Exx、S03→S04 等重排映射
4. **集合并/拆分**：一个文件对应多集，或一集拆多文件。→ agent 构造 `file→S01E01-E02`、`file→S01E03-part1` 映射

这些场景的 NFO 填充细节**延后到 NFO 重新设计时确认**。

## 6. Jellyfin 目录与 NFO 规范（调研结论）

### 目录结构（默认行为基准）

- 电影：`Movies/电影名 (年) [tmdbid-xxx]/电影名 (年).mkv`
- 剧集：`Shows/剧名 (年) [tmdbid-xxx]/Season 01/剧名 (年) S01E01.mkv`
- Season 文件夹必须写 `Season 01`（不能写 `S01`）
- 多集合并文件：`S01E01-E02.mkv`
- 多分段文件：`S01E01-part-1.mkv`、`S01E01-part-2.mkv`
- 特别篇：`Season 00` 文件夹
- 元数据 provider id 格式：`[tmdbid-xxx]`、`[imdbid-tt00000000]`
- 禁用字符：`< > : " / \ | ? *`

### NFO 文件（关键：本地 NFO 优先级高于远程 TMDB 且无法关闭 → 填好 NFO 即等于跳过 Jellyfin 刮削）

- 电影：`movie.nfo` 或 `<文件名>.nfo`
- 剧集：`tvshow.nfo`（series 根）
- 季：`season.nfo`（季文件夹内）
- 集：`<文件名>.nfo`（与媒体同目录同名）
- 标识：`<uniqueid type="tmdbid">`、`<tmdbid>`、`<imdbid>`、`<tvdbid>`
- 多评分：`<ratings><rating name="..." default="true">`
- 特别篇播放顺序：`airsbefore_season`、`airsbefore_episode`、`airsafter_season`、`displayseason`、`displayepisode`
- 字段锁定：`lockdata`、`lockedfields`

参考实现：dantalian 的 `nfogen/nfo.rs`（用 bangumi 作 uniqueid， ours 用 tmdb 为主）。

## 7. 执行与安全（dry-run + 确认 + 回滚）

默认 dry-run：先生成「将要做什么」的计划（重命名/移动映射表、目录结构预览），不触碰文件；用户确认后 CLI 才真正执行。

### 可逆性保障

**默认方案：事务日志 + `undo` 命令**

- `execute-plan` 执行前，把每步操作（mv/rename/mkdir）及其逆操作写入 `.snapshot.json`（原始路径 → 新路径的完整映射，存在 skill 工作目录而非媒体库）
- 因操作只做 rename/move，不改内容、不删源，每步可逆
- `undo <snapshot>` 按逆序回放逆操作，恢复原始目录结构
- `execute-plan` 默认先做 dry-run 校验（目标路径无冲突、源文件存在），失败则整体不执行

**可选 `--keep-hardlink`**：同卷情况下对源文件改用硬链接保留一份原件（仅当用户明确要物理双份时），默认关闭以避免 Jellyfin 重复扫描。

hardlink 双份方案的问题：跨卷移动不支持（NTFS 硬链接仅同卷）、原件与副本都在媒体库路径下会触发 Jellyfin 重复扫描、真正删除前磁盘不释放。故默认走事务日志可逆，hardlink 仅作可选物理双份。

## 8. 阶段划分

| 阶段 | 内容 |
|---|---|
| **P0** | MVP：tmdb 搜索 + fetch-summary + build-plan（无 NFO）+ execute-plan + undo，dry-run 默认，知识沉淀文档（含 Lycoris 案例） |
| **P1** | bangumi 信息获取：`bangumi.py`（search_anime、get_subject、get_subject_episodes），`fetch-summary --with-bangumi` 交叉校验，标记 TMDB overview 空缺。仍不做 NFO |
| **【重新设计检查点】** | 基于 P0/P1 拿到的真实 tmdb/bangumi 数据，重新进入 brainstorming，细化 NFO 设计（字段集、source 选择策略、非标场景 NFO 填充、agent 与代码边界） |
| **P2** | NFO 生成：按检查点设计实现 `nfo.py`，CLI 增加 NFO 相关能力 |
| **P3** | 剩余功能：非标场景 agent 自由处理验证、build-plan spec 必要扩展、双源填充 |

### NFO 设计的当前约束（不固化字段，留到检查点细化）

- **目标**：让 Jellyfin 直接识别、跳过刮削
- **约束**：代码驱动生成（agent 只指定信息源 + 少量字段，不传全部参数）；Bangumi 仅在 TMDB overview 为空或 <10 字时补全
- **待定**：字段集、source 选择、覆盖场景的 NFO 填充方式

### P0 交付物

- `SKILL.md`：编排流程、确认时机、知识沉淀文档引用
- `cli.py`：`search`、`fetch-summary`、`build-plan`、`execute-plan`、`undo`
- `tmdb.py`：TMDB 调用（初期 import tmdbsimple）
- `summarize.py`：摘要压缩
- `planner.py`：计划构建（P0 不含 NFO）
- `fsops.py`：文件扫描、重命名、移动、事务日志、undo
- `tests/`：标准用例 + Lycoris Recoil 案例
- `docs/search-heuristics.md`：知识沉淀文档（含 Lycoris 案例）

## 9. 测试策略

原则：每个修复/功能配测试，避免未来再错。

### P0 测试

1. `search` 命令：关键字提取（从各种 release 名提取主标题）、TMDB 搜索多关键字回退逻辑（mock 响应）
2. `fetch-summary`：摘要压缩（只返回 title + 结构 + overview_length，不含完整 overview）、`episode_groups` 字段存在性
3. `build-plan`：标准剧集/电影重命名（mock 文件清单 + TMDB 响应，验证操作列表）
4. `execute-plan` + `undo`：事务日志写入、undo 按逆序回放恢复、dry-run 模式校验
5. Lycoris Recoil 案例：长标题 0 结果回退到短标题，命中 TMDB 主剧，提示 S00 特别篇

### P1 测试

bangumi 搜索与交叉校验（mock 响应）。

### P3 测试（推迟到 NFO 重新设计后细化）

四个非标场景端到端用例，使用保存的 tmdb/bangumi JSON 快照作 fixture，避免 API 调用不稳定。NFO 字段未定时无法写断言，当前仅保留场景的「数据获取 + 映射决策」可测部分。

## 10. 上下文占用

早期仅靠日志记录上下文占用情况，为后续优化提供依据，不做提前优化。剧集元数据可能很大且大部分对 LLM 判断无意义（如完整剧/季/集介绍），进上下文的应是摘要（title + 结构），NFO 由代码生成。

## 11. 范围外（YAGNI）

- 高频单文件处理场景
- NFO 字段与 source 选择的最终细节（留到检查点）
- build-plan 的模式开关式参数（改由 agent 构造通用 spec）
