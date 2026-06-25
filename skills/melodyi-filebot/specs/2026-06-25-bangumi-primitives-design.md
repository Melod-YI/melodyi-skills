# melodyi-filebot P1 · Bangumi 三原语设计

- 日期：2026-06-25
- 状态：已与用户确认；范围限定三原语 + CLI，`fetch-summary --with-bangumi` 留到下一步
- 上游设计：见 `2026-06-23-melodyi-filebot-design.md` §8 P1

## 1. 目标与范围

实现 Bangumi v0 API 的三个数据获取原语并暴露为 CLI 子命令，供 agent/用户审视 bangumi 返回数据。**不含** `fetch-summary --with-bangumi` 交叉校验与 overview 空缺填充（下一步）。

三个原语：

| 函数 | 端点 | 说明 |
|---|---|---|
| `search_anime(keyword)` | `POST /v0/search/subjects` | `filter.type=[2]` 限定动画；API 硬性返回 ≤10 条/页（实测 perpage 被忽略），不支持自定义每页数 |
| `get_subject(subject_id)` | `GET /v0/subjects/{id}` | 单条目详情 |
| `get_subject_episodes(subject_id, ep_type=0)` | `GET /v0/episodes?subject_id=&type=&limit=50&offset=` | 自动翻页 |

鉴权：匿名 + `User-Agent` 头即可（已实测 200），P1 不需要 token。

## 2. 模块结构（方案 A：自实现 httpx + 镜像 TMDB）

```
melodyi_filebot/
├── bangumi.py     # 新增：httpx 调用封装，结构与 tmdb.py 对称
├── summarize.py   # 扩展：bangumi_* 压缩函数
├── models.py      # 扩展：BangumiSubjectSummary / BangumiEpisodeBrief
└── cli.py         # 扩展：bangumi-search / bangumi-subject / bangumi-episodes
```

httpx 已是依赖，不引新包。结构与现有 `tmdb.py`（调用层）+ `summarize.py`（压缩层）完全对称。

## 3. 数据模型

```python
class BangumiSubjectSummary(BaseModel):
    """Bangumi 条目摘要（搜索/详情共用）"""
    subject_id: int
    type: int            # 2=动画
    name: str            # 原文名
    name_cn: str         # 中文名
    date: Optional[str] = None      # 放送日期 YYYY-MM-DD
    eps: int = 0         # 总集数
    platform: str = ""   # TV/WEB/...
    summary: str = ""    # 完整简介（填充源核心价值，与 TMDB overview 不同）
    summary_length: int = 0

    @property
    def summary_available(self) -> bool:
        return self.summary_length >= 10


class BangumiEpisodeBrief(BaseModel):
    """Bangumi 集摘要"""
    episode_id: int
    type: int            # 0=本篇 1=特别篇 2=OP 3=ED 4=预告 5=MAD 6=其他 7=非正片
    name: str
    name_cn: str
    sort: float          # bangumi sort 可为小数（如 5.5）
    ep: Optional[int] = None
    airdate: Optional[str] = None
    duration: Optional[str] = None    # "00:24:00"
    desc: str = ""       # 集简介（对应 bangumi desc 字段）
    desc_length: int = 0

    @property
    def desc_available(self) -> bool:
        return self.desc_length >= 10
```

字段取最小集（重命名/校验所需），不含 `infobox`/`rating`/`duration_seconds` 等暂不需要的字段。

## 4. bangumi.py 调用细节

模块级 `httpx.Client`：`base_url=https://api.bgm.tv`、固定 `User-Agent: melodyi-filebot/dev (https://github.com/melodyi)`、超时 15s。

`_request(method, path, **kwargs) -> dict`：
- 日志：请求入口（method/path/params）、响应状态
- 404 → `RuntimeError("Bangumi 未找到资源: {method} {path}")`
- 其它非 2xx → `resp.raise_for_status()`
- 返回 `resp.json()`

`search_anime`：`POST /v0/search/subjects`，body `{"keyword","filter":{"type":[2]}}`；响应 `{"data":[...],"total"}` → `summarize.bangumi_subjects_from_search(items)`。**注意**：API 实测忽略 `perpage`，始终返回 ≤10 条，故函数无 perpage 参数。

`get_subject`：`GET /v0/subjects/{id}` → `summarize.bangumi_subject_from_detail(data)`。

`get_subject_episodes`：循环 `offset` 翻页（每页 50）累计到 `total` 或达 2000 上限；超限记 warning 日志；返回 `summarize.bangumi_episodes_from_raw(all_items)`。

## 5. summarize.py 扩展

- `bangumi_subject_from_detail(d) -> BangumiSubjectSummary`：取 id/type/name/name_cn/date/eps/platform/summary，`summary_length=len(summary)`。
- `bangumi_subjects_from_search(items) -> List[...]`：列表版。
- `bangumi_episodes_from_raw(items) -> List[BangumiEpisodeBrief]`：取 id/type/name/name_cn/sort/ep/airdate/duration/desc，`desc_length=len(desc)`。

字段缺失容错：`or ""`/`or 0` 兜底，`None` 字段保持 `None`。

## 6. CLI（cli.py 三个平级子命令）

**统一约定**（与 TMDB 侧一致）：默认文本输出为「列名表头 + `|` 分隔行」表格风格（**无「列含义」前缀**，表头即纯列名）；**文本不外泄完整简介**，只显示 `简介长度`（agent 无需知道简介内容）；`--json` 才输出完整 summary/desc（模型已存）。日志默认静默（仅 ERROR），`-v/--verbose` 才输出 INFO 日志（参考 melodyi-web）；网络/API 错误用 `click.echo(err=True)` + `sys.exit(1)` 友好报错，非 traceback。

| 命令 | 参数 | 文本输出 | `--json` |
|---|---|---|---|
| `bangumi-search <keyword>` | — | 表头 + 行：`bangumi_id | 中文名 | 原名 | 放送日期 | 集数 | 平台 | 简介长度` | 完整模型列表（含 summary） |
| `bangumi-subject <id>` | — | 字段行：`bangumi_id=... | name_cn / name`，第二行 `放送日期 | 集数 | 平台 | 简介可用 | 简介长度` | 完整模型（含 summary） |
| `bangumi-episodes <id>` | `--type`(默认0) | 表头 + 行：`集号 | 中文名 | 原名 | 放送日期 | 时长 | 简介长度` | 完整集列表（含 desc） |

## 7. 错误处理与日志

404 → `RuntimeError`，CLI 捕获后 `click.echo("错误: ...", err=True)` + `sys.exit(1)`，非 traceback；网络错误（`httpx.HTTPError`）同样捕获友好报错。日志默认仅 ERROR（静默），`-v/--verbose` 输出 INFO（含请求/响应/命中数等）。无 token 需求。

## 8. 测试策略

`test_bangumi.py`（mock httpx，与 `test_tmdb.py` mock tmdbsimple 同模式）：
- `search_anime`：构造搜索响应，断言命中数与字段解析、`filter.type=[2]` 请求体正确
- `get_subject`：构造条目响应，断言字段、`summary_available` 阈值
- `get_subject_episodes`：构造 `total=120` 响应验证翻页（两次 offset=0/50），字段解析；`desc` 缺失时 `desc_available=False`
- 404 → `RuntimeError`

`tests/integration/test_real_bangumi.py`：真实 API，`@pytest.mark.integration` 默认 skip（需 `--run-integration`），用 `莉可丽丝` 364450 断言 subject_id/eps=13/集数，容忍多余条目，调用间隔防限流。

## 9. 范围外（YAGNI）

- `fetch-summary --with-bangumi` 交叉校验（下一步）
- TMDB overview 空缺标记与 bangumi 填充（随交叉校验一起）
- bangumi token / 个性化端点（收藏等）
- `infobox`/`rating`/`duration_seconds` 等非必要字段

## 10. 同期 CLI 精炼（基于用户反馈，非 bangumi 专属）

本次随用户反馈一并调整的 TMDB 侧 CLI 行为：

- **去「列含义」前缀**：所有表格表头改为纯列名行（如 `季号 | 名称 | 集数 | 首播日期 | 简介可用`），不再有「列含义：」前缀。
- **fetch-summary 默认不输出剧集组**：剧集组信息默认隐藏，加 `--episode-groups` 才列出（`组ID | 名称 | 类型 | 集数`）。
- **type 映射**：`EpisodeGroupBrief.type`（TMDB 枚举 1..7）经 `type_name` 映射为可读名（1=首播顺序 2=绝对集号 3=DVD 4=数字版 5=剧情篇章 6=制作顺序 7=TV），未知值回退数字字符串；文本不再出现裸数字类型。
- **新增 `episode-group <group_id>` 命令**：`tmdb.get_episode_group` 走 `tmdbsimple.TV_Episode_Groups.info()`，返回 `EpisodeGroupDetail`（含嵌套子组 `EpisodeGroupSub` + 集列表，集带 `season_number` 因组可跨季）；文本按子组分段打印 `S{season}E{episode}` 集列表，`--json` 输出完整结构。用于非标场景1（重置版归在剧集组）。
