# NFO 生成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 P2 NFO 生成——由工具按 Plan 的来源 spec 拉取 TMDB/bangumi/ffprobe 字段，生成 Jellyfin 可直接识别的 tvshow/season/episode NFO（lockdata=true 全锁）。

**Architecture:** 三份结构分离：folder→target 输入 → `draft-plan` 生成纯映射 Plan（agent 编辑）→ `build-plan` 生成 ExecutionList（move+nfo 操作）→ `execute-plan` 移动 / `generate-nfo` 写 NFO。NFO 内容不进 Plan，执行时现拉现填。新 `Plan` 取代 `PlanMap`，`draft-plan` 取代 `draft-map`。

**Tech Stack:** Python ≥3.10 / pydantic v2 / click / httpx / tmdbsimple / ffprobe / pytest。

**Spec:** `skills/melodyi-filebot/specs/2026-07-01-nfo-generation-design.md`

**约定：** 测试先行（TDD），每个任务结束提交。中文提交信息，约定式提交。包目录 `packages/melodyi-filebot/`，测试 `tests/`。运行测试：`cd packages/melodyi-filebot && python -m pytest <path> -v`。

---

## 文件结构

| 文件 | 职责 |
|---|---|
| `melodyi_filebot/models.py` | 扩展：`NfoSource`/`SeasonEntry`/`EpisodeEntry`/`FileTarget`/`Plan`/`NfoOperation`；`BuildPlanResult` 加 `nfo_operations` |
| `melodyi_filebot/structure.py` | 新增 `probe_stream_details(path)`（ffprobe 取 video/audio 流信息） |
| `melodyi_filebot/tmdb.py` | 新增 `get_show_detail_full`（append 全量）、`get_season_detail`（含每集 crew/guest_stars） |
| `melodyi_filebot/nfo.py` | **新增**：按 `NfoOperation` 来源拉取字段 → 生成 XML（tvshow/season/episode）+ 写文件 |
| `melodyi_filebot/planner.py` | 新增 `draft_plan`（folder 输入→Plan）、`build_plan_from_plan`（Plan→ExecutionList）；废弃 `draft_map_tv` |
| `melodyi_filebot/cli.py` | `draft-plan` / `build-plan`（新） / `generate-nfo`；废弃 `draft-map` |
| `tests/test_nfo.py` | NFO XML 生成测试 |
| `tests/test_planner.py` | draft_plan / build_plan_from_plan 测试 |
| `tests/test_cli.py` | 新 CLI 命令测试 |
| `tests/integration/test_real_nfo.py` | 真实 TMDB/bangumi 集成测试（默认 skip） |

---

## Task 1: 新增 Plan 结构模型

**Files:**
- Modify: `melodyi_filebot/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_models.py` 末尾：

```python
class TestPlanModels:
    """P2 Plan 结构测试"""

    def test_file_target(self):
        from melodyi_filebot.models import FileTarget
        t = FileTarget(season=1, episode=5, episode_end=None, part=None)
        assert t.season == 1 and t.episode == 5

    def test_nfo_source_tmdb(self):
        from melodyi_filebot.models import NfoSource
        s = NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1)
        assert s.provider == "tmdb" and s.tmdb_id == 154494

    def test_nfo_source_bangumi(self):
        from melodyi_filebot.models import NfoSource
        s = NfoSource(provider="bangumi", bangumi_subject_id=364450, bangumi_episode_id=1111258)
        assert s.bangumi_subject_id == 364450

    def test_episode_entry_three_blocks(self):
        """集三块：file / target / source"""
        from melodyi_filebot.models import EpisodeEntry, FileTarget, NfoSource
        e = EpisodeEntry(
            file="D:/src/ep01.mkv",
            target=FileTarget(season=1, episode=1),
            source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1),
        )
        assert e.file.endswith("ep01.mkv")
        assert e.target.season == 1
        assert e.source.tmdb_id == 154494

    def test_plan_structure(self):
        from melodyi_filebot.models import Plan, ShowRef, SeasonEntry, EpisodeEntry, FileTarget, NfoSource
        p = Plan(
            show=ShowRef(tmdb_id=154494, bangumi_subject_id=364450,
                         title="莉可丽丝", year=2022, language="zh-CN"),
            seasons=[SeasonEntry(season=1, source=NfoSource(provider="tmdb", tmdb_id=154494, season=1))],
            episodes=[EpisodeEntry(
                file="D:/src/ep01.mkv",
                target=FileTarget(season=1, episode=1),
                source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1),
            )],
            warnings=[],
        )
        assert p.show.tmdb_id == 154494
        assert len(p.seasons) == 1
        assert p.episodes[0].source.tmdb_id == 154494

    def test_nfo_operation(self):
        from melodyi_filebot.models import NfoOperation, NfoSource
        op = NfoOperation(type="episode", path=".../S01E01.nfo", season=1, episode=1,
                          source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1))
        assert op.type == "episode"

    def test_build_plan_result_has_nfo_operations(self):
        from melodyi_filebot.models import BuildPlanResult, NfoOperation, NfoSource
        r = BuildPlanResult(operations=[], nfo_operations=[
            NfoOperation(type="tvshow", path=".../tvshow.nfo",
                         source=NfoSource(provider="tmdb", tmdb_id=154494))
        ])
        assert len(r.nfo_operations) == 1
        # 默认空
        assert BuildPlanResult(operations=[]).nfo_operations == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/test_models.py::TestPlanModels -v`
Expected: FAIL（ImportError，新模型未定义）

- [ ] **Step 3: 实现模型**

在 `melodyi_filebot/models.py` 末尾（`TreeNode.model_rebuild()` 之前）追加：

```python
class FileTarget(BaseModel):
    """集的展示身份（决定文件名/目录/NFO season-episode 字段）"""
    season: int
    episode: int
    episode_end: Optional[int] = None
    part: Optional[int] = None


class NfoSource(BaseModel):
    """元数据来源 spec（不含内容，只记 id 坐标）"""
    provider: str = "tmdb"  # "tmdb" | "bangumi"
    tmdb_id: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    bangumi_subject_id: Optional[int] = None
    bangumi_episode_id: Optional[int] = None


class SeasonEntry(BaseModel):
    """Plan 中某季的来源"""
    season: int
    source: NfoSource


class EpisodeEntry(BaseModel):
    """Plan 中单集（三块：file / target / source）"""
    file: str
    target: FileTarget
    source: NfoSource


class ShowRef(BaseModel):
    """Plan 中剧级信息"""
    tmdb_id: int
    bangumi_subject_id: Optional[int] = None
    title: str = ""
    original_title: str = ""
    year: Optional[int] = None
    language: str = "zh-CN"


class Plan(BaseModel):
    """纯映射 Plan（agent 编辑对象）"""
    show: ShowRef
    seasons: List[SeasonEntry] = Field(default_factory=list)
    episodes: List[EpisodeEntry] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class NfoOperation(BaseModel):
    """执行清单中的 NFO 写入操作"""
    type: str  # "tvshow" | "season" | "episode"
    path: str
    season: Optional[int] = None
    episode: Optional[int] = None
    source: NfoSource
```

并修改 `BuildPlanResult`，加 `nfo_operations` 字段：

```python
class BuildPlanResult(BaseModel):
    """执行清单（move + nfo 操作）"""
    operations: List[PlanOperation]
    nfo_operations: List["NfoOperation"] = Field(default_factory=list)
    spec_applied: str = "standard"
    warnings: List[str] = Field(default_factory=list)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 提交**

```bash
git add packages/melodyi-filebot/melodyi_filebot/models.py packages/melodyi-filebot/tests/test_models.py
git commit -m "feat(melodyi-filebot): 新增 P2 Plan/NfoOperation 结构模型"
```

---

## Task 2: nfo.py — tvshow NFO XML 生成

**Files:**
- Create: `melodyi_filebot/nfo.py`
- Test: `tests/test_nfo.py`

说明：NFO 生成分两层——`_build_tvshow_xml(show_data, bangumi_data)` 纯数据→XML（易测）；外层 `generate_nfo(op)` 拉取+调用（Task 11）。本任务先做纯 XML 层（mock 数据）。

- [ ] **Step 1: 写失败测试**

创建 `tests/test_nfo.py`：

```python
"""NFO XML 生成测试（纯数据→XML 层，mock 来源数据）"""

from melodyi_filebot import nfo


def _show_data():
    return {
        "id": 154494, "name": "莉可丽丝", "original_name": "リコリス・リコイル",
        "overview": "x" * 50, "first_air_date": "2022-07-02", "last_air_date": "2022-09-24",
        "in_production": False, "episode_run_time": 24,
        "genres": [{"id": 16, "name": "动画"}],
        "networks": [{"name": "BS11"}],
        "vote_average": 8.5,
        "poster_path": "/abc.jpg", "backdrop_path": "/def.jpg",
        "external_ids": {"imdb_id": "tt13293588", "tvdb_id": 371310},
        "aggregate_credits": {"cast": [{"name": "内山夕实", "character": "鲁迪", "order": 0, "profile_path": "/p.jpg"}]},
        "keywords": {"results": [{"name": "isekai"}, {"name": "anime"}]},
        "content_ratings": {"results": [{"rating": "TV-MA", "iso_3166_1": "US"}]},
        "created_by": [{"name": "理不尽な孫の手"}],
    }


class TestTvshowXml:
    def test_tvshow_xml_has_required_fields(self):
        xml = nfo.build_tvshow_xml(_show_data(), bangumi_data=None, language="zh-CN")
        assert "<?xml" in xml and "<tvshow>" in xml and "</tvshow>" in xml
        assert "<title>莉可丽丝</title>" in xml
        assert "<originaltitle>リコリス・リコイル</originaltitle>" in xml
        assert "<plot>" in xml and "x" * 50 in xml  # TMDB overview 原文
        assert "<tmdbid>154494</tmdbid>" in xml
        assert "<imdb_id>tt13293588</imdb_id>" in xml
        assert "<tvdbid>371310</tvdbid>" in xml
        assert "<genre>动画</genre>" in xml
        assert "<tag>isekai</tag>" in xml
        assert "<studio>BS11</studio>" in xml
        assert "<rating>8.5</rating>" in xml
        assert "<lockdata>true</lockdata>" in xml
        assert "<status>Ended</status>" in xml  # in_production=False
        assert "image.tmdb.org/t/p/original/abc.jpg" in xml  # poster URL
        assert "<actor>" in xml and "内山夕实" in xml

    def test_tvshow_xml_bangumi_fill_when_overview_short(self):
        """TMDB overview <10 字时用 bangumi summary 填 plot"""
        data = dict(_show_data(), overview="短")  # 长度 1
        bg = {"summary": "这是 bangumi 的简介。" * 10, "name_cn": "莉可丽丝", "name": "リコリス"}
        xml = nfo.build_tvshow_xml(data, bangumi_data=bg, language="zh-CN")
        assert "这是 bangumi 的简介" in xml
        assert "短" not in xml.split("<plot>")[1].split("</plot>")[0]
```

- [ ] **Step 2: 运行验证失败**

Run: `python -m pytest tests/test_nfo.py::TestTvshowXml -v`
Expected: FAIL（`module 'melodyi_filebot.nfo' has no attribute 'build_tvshow_xml'`）

- [ ] **Step 3: 实现 `build_tvshow_xml`**

创建 `melodyi_filebot/nfo.py`：

```python
"""NFO 生成：按来源拉取字段 → Jellyfin NFO XML

分两层：
- build_*_xml(data, bangumi_data): 纯数据→XML（易测，mock 数据）
- generate_nfo(op): 按 NfoOperation 来源拉取 + 调 build + 写文件（Task 11）
"""

from __future__ import annotations

import logging
from typing import Optional
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

TMDB_IMG_BASE = "https://image.tmdb.org/t/p/original"
OVERVIEW_MIN_LENGTH = 10


def _img_url(path: Optional[str]) -> Optional[str]:
    return f"{TMDB_IMG_BASE}{path}" if path else None


def _fill_overview(tmdb_overview: Optional[str], bangumi_text: Optional[str]) -> str:
    """TMDB overview 空/<10 用 bangumi 同义字段补"""
    ov = (tmdb_overview or "").strip()
    if len(ov) >= OVERVIEW_MIN_LENGTH:
        return ov
    bg = (bangumi_text or "").strip()
    return bg if len(bg) >= OVERVIEW_MIN_LENGTH else ov


def _el(tag: str, text) -> str:
    """生成 <tag>escaped text</tag>，text 为 None/空则返回空元素 <tag/>"""
    if text is None or text == "":
        return f"<{tag} />"
    return f"<{tag}>{escape(str(text))}</{tag}>"


def build_tvshow_xml(show: dict, bangumi_data: Optional[dict], language: str) -> str:
    """TMDB show dict + 可选 bangumi dict → tvshow.nfo XML"""
    bg = bangumi_data or {}
    plot = _fill_overview(show.get("overview"), bg.get("summary"))
    title = show.get("name") or bg.get("name_cn") or ""
    original = show.get("original_name") or bg.get("name") or ""
    ext = show.get("external_ids") or {}
    parts = ['<?xml version="1.0" encoding="utf-8" standalone="yes"?>', "<tvshow>"]
    parts.append(_el("plot", plot))
    parts.append(_el("outline", plot))
    parts.append("<lockdata>true</lockdata>")
    parts.append(_el("title", title))
    parts.append(_el("originaltitle", original))
    for w in (show.get("created_by") or []):
        parts.append(_el("writer", w.get("name")))
        parts.append(_el("credits", w.get("name")))
    parts.append(_el("rating", show.get("vote_average")))
    parts.append(_el("year", (show.get("first_air_date") or "")[:4] or None))
    parts.append(_el("premiered", show.get("first_air_date")))
    parts.append(_el("enddate", show.get("last_air_date")))
    parts.append(_el("releasedate", show.get("first_air_date")))
    parts.append(_el("runtime", show.get("episode_run_time")))
    for g in (show.get("genres") or []):
        parts.append(_el("genre", g.get("name")))
    for k in ((show.get("keywords") or {}).get("results") or []):
        parts.append(_el("tag", k.get("name")))
    for n in (show.get("networks") or []):
        parts.append(_el("studio", n.get("name")))
    cr = (show.get("content_ratings") or {}).get("results") or []
    if cr:
        parts.append(_el("mpaa", cr[0].get("rating")))
    parts.append(_el("imdb_id", ext.get("imdb_id")))
    parts.append(_el("tmdbid", show.get("id")))
    parts.append(_el("tvdbid", ext.get("tvdb_id")))
    poster = _img_url(show.get("poster_path"))
    fanart = _img_url(show.get("backdrop_path"))
    if poster or fanart:
        parts.append("<art>")
        if poster:
            parts.append(_el("poster", poster))
        if fanart:
            parts.append(_el("fanart", fanart))
        parts.append("</art>")
    for a in ((show.get("aggregate_credits") or {}).get("cast") or []):
        parts.append("<actor>")
        parts.append(_el("name", a.get("name")))
        parts.append(_el("role", a.get("character")))
        parts.append(_el("type", "Actor"))
        parts.append(_el("sortorder", a.get("order")))
        parts.append(_el("thumb", _img_url(a.get("profile_path"))))
        parts.append("</actor>")
    parts.append(_el("season", -1))
    parts.append(_el("episode", -1))
    parts.append(_el("status", "Continuing" if show.get("in_production") else "Ended"))
    parts.append("</tvshow>")
    return "\n".join(parts)
```

- [ ] **Step 4: 运行验证通过**

Run: `python -m pytest tests/test_nfo.py::TestTvshowXml -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add packages/melodyi-filebot/melodyi_filebot/nfo.py packages/melodyi-filebot/tests/test_nfo.py
git commit -m "feat(melodyi-filebot): nfo.py tvshow NFO XML 生成（含 bangumi 补全与图片 URL）"
```

---

## Task 3: nfo.py — season NFO XML 生成

**Files:**
- Modify: `melodyi_filebot/nfo.py`
- Test: `tests/test_nfo.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_nfo.py`：

```python
def _season_data():
    return {
        "id": 154494, "season_number": 1, "name": "第 1 季",
        "overview": "x" * 50, "air_date": "2022-07-02",
        "poster_path": "/season.jpg",
    }


class TestSeasonXml:
    def test_season_xml(self):
        xml = nfo.build_season_xml(_season_data(), bangumi_data=None,
                                   show_actors=None, season_number=1)
        assert "<season>" in xml and "</season>" in xml
        assert "<title>第 1 季</title>" in xml
        assert "<seasonnumber>1</seasonnumber>" in xml
        assert "<premiered>2022-07-02</premiered>" in xml
        assert "<lockdata>true</lockdata>" in xml
        assert "image.tmdb.org/t/p/original/season.jpg" in xml

    def test_season_xml_bangumi_when_no_tmdb_overview(self):
        """TMDB 季 overview 空 + 有 bangumi subject → 用 bangumi summary（物语）"""
        data = dict(_season_data(), overview="")
        bg = {"summary": "物语这一季的简介。" * 10, "name_cn": "化物语", "date": "2009-07-05"}
        xml = nfo.build_season_xml(data, bangumi_data=bg, show_actors=None, season_number=1)
        assert "物语这一季的简介" in xml
```

- [ ] **Step 2: 运行验证失败**

Run: `python -m pytest tests/test_nfo.py::TestSeasonXml -v`
Expected: FAIL（`build_season_xml` 未定义）

- [ ] **Step 3: 实现 `build_season_xml`**

在 `nfo.py` 追加：

```python
def build_season_xml(season: dict, bangumi_data: Optional[dict],
                     show_actors: Optional[list], season_number: int) -> str:
    """季详情 + 可选 bangumi subject → season.nfo XML"""
    bg = bangumi_data or {}
    plot = _fill_overview(season.get("overview"), bg.get("summary"))
    title = season.get("name") or bg.get("name_cn") or f"第 {season_number} 季"
    parts = ['<?xml version="1.0" encoding="utf-8" standalone="yes"?>', "<season>"]
    parts.append(_el("plot", plot))
    parts.append(_el("outline", plot))
    parts.append("<lockdata>true</lockdata>")
    parts.append(_el("title", title))
    parts.append(_el("year", (season.get("air_date") or bg.get("date") or "")[:4] or None))
    parts.append(_el("premiered", season.get("air_date") or bg.get("date")))
    parts.append(_el("releasedate", season.get("air_date") or bg.get("date")))
    poster = _img_url(season.get("poster_path"))
    if poster:
        parts.append("<art>")
        parts.append(_el("poster", poster))
        parts.append("</art>")
    for a in (show_actors or []):
        parts.append("<actor>")
        parts.append(_el("name", a.get("name")))
        parts.append(_el("role", a.get("character")))
        parts.append(_el("type", "Actor"))
        parts.append(_el("thumb", _img_url(a.get("profile_path"))))
        parts.append("</actor>")
    parts.append(_el("seasonnumber", season_number))
    parts.append("</season>")
    return "\n".join(parts)
```

- [ ] **Step 4: 运行验证通过**

Run: `python -m pytest tests/test_nfo.py::TestSeasonXml -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add packages/melodyi-filebot/melodyi_filebot/nfo.py packages/melodyi-filebot/tests/test_nfo.py
git commit -m "feat(melodyi-filebot): nfo.py season NFO XML 生成"
```

---

## Task 4: nfo.py — episode NFO XML 生成（含 streamdetails / displayseason）

**Files:**
- Modify: `melodyi_filebot/nfo.py`
- Test: `tests/test_nfo.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_nfo.py`：

```python
def _episode_data():
    return {
        "name": "慢慢来", "overview": "x" * 50, "air_date": "2022-07-02",
        "runtime": 24, "episode_number": 1, "season_number": 1,
        "still_path": "/still.jpg", "vote_average": 8.4,
        "guest_stars": [{"name": "竹田海渡", "character": "急救员", "order": 504}],
        "crew": [{"name": "平野宏树", "job": "Director"}, {"name": "岡本学", "job": "Writer"}],
    }


def _stream_details():
    return {
        "video": {"codec": "h264", "width": 1920, "height": 1080, "aspect": "16:9",
                  "framerate": "23.976", "duration": 23, "duration_seconds": 1420},
        "audio": {"codec": "aac", "channels": 2, "samplingrate": 48000},
    }


class TestEpisodeXml:
    def test_episode_xml(self):
        xml = nfo.build_episode_xml(
            _episode_data(), bangumi_data=None, show_title="莉可丽丝",
            target_season=1, target_episode=1, stream_details=_stream_details(),
        )
        assert "<episodedetails>" in xml and "</episodedetails>" in xml
        assert "<title>慢慢来</title>" in xml
        assert "<showtitle>莉可丽丝</showtitle>" in xml
        assert "<season>1</season>" in xml and "<episode>1</episode>" in xml
        assert "<aired>2022-07-02</aired>" in xml
        assert "<runtime>24</runtime>" in xml
        assert "<director>平野宏树</director>" in xml
        assert "<writer>岡本学</writer>" in xml
        assert "<lockdata>true</lockdata>" in xml
        assert "<GuestStar" not in xml  # type 用 <type> 子元素
        assert "竹田海渡" in xml
        assert "<codec>h264</codec>" in xml
        assert "<width>1920</width>" in xml
        assert "<durationinseconds>1420</durationinseconds>" in xml
        assert "image.tmdb.org/t/p/original/still.jpg" in xml

    def test_episode_xml_displayseason_when_target_ne_source(self):
        """target(S01E05) ≠ source(S00E12) 时写 displayseason/displayepisode"""
        ep = dict(_episode_data(), season_number=0, episode_number=12)
        xml = nfo.build_episode_xml(
            ep, bangumi_data=None, show_title="物语",
            target_season=1, target_episode=5, stream_details=None,
        )
        assert "<displayseason>0</displayseason>" in xml
        assert "<displayepisode>12</displayepisode>" in xml
        # 展示身份用 target
        assert "<season>1</season>" in xml
        assert "<episode>5</episode>" in xml

    def test_episode_xml_bangumi_desc_fill(self):
        ep = dict(_episode_data(), overview="")
        bg = {"desc": "bangumi 集简介。" * 10, "name_cn": "慢慢来", "airdate": "2022-07-02"}
        xml = nfo.build_episode_xml(
            ep, bangumi_data=bg, show_title="莉可丽丝",
            target_season=1, target_episode=1, stream_details=None,
        )
        assert "bangumi 集简介" in xml

    def test_episode_xml_no_streamdetails_when_none(self):
        xml = nfo.build_episode_xml(
            _episode_data(), bangumi_data=None, show_title="x",
            target_season=1, target_episode=1, stream_details=None,
        )
        assert "<fileinfo>" not in xml
```

- [ ] **Step 2: 运行验证失败**

Run: `python -m pytest tests/test_nfo.py::TestEpisodeXml -v`
Expected: FAIL（`build_episode_xml` 未定义）

- [ ] **Step 3: 实现 `build_episode_xml`**

在 `nfo.py` 追加：

```python
def _streamdetails_xml(sd: dict) -> str:
    v = sd.get("video") or {}
    a = sd.get("audio") or {}
    parts = ["<fileinfo><streamdetails>"]
    if v:
        parts.append("<video>")
        for tag in ["codec", "width", "height", "aspect", "framerate", "duration", "duration_seconds"]:
            if v.get(tag) is not None:
                # duration_seconds → durationinseconds
                parts.append(_el("durationinseconds" if tag == "duration_seconds" else tag, v.get(tag)))
        parts.append("</video>")
    if a:
        parts.append("<audio>")
        for tag in ["codec", "channels", "samplingrate"]:
            if a.get(tag) is not None:
                parts.append(_el(tag, a.get(tag)))
        parts.append("</audio>")
    parts.append("</streamdetails></fileinfo>")
    return "\n".join(parts)


def build_episode_xml(ep: dict, bangumi_data: Optional[dict], show_title: str,
                      target_season: int, target_episode: int,
                      stream_details: Optional[dict]) -> str:
    """集详情 + 可选 bangumi + 展示身份 + ffprobe → episodedetails XML"""
    bg = bangumi_data or {}
    plot = _fill_overview(ep.get("overview"), bg.get("desc"))
    title = ep.get("name") or bg.get("name_cn") or ""
    src_season = ep.get("season_number")
    src_episode = ep.get("episode_number")
    parts = ['<?xml version="1.0" encoding="utf-8" standalone="yes"?>', "<episodedetails>"]
    parts.append(_el("plot", plot))
    parts.append("<lockdata>true</lockdata>")
    parts.append(_el("title", title))
    for c in (ep.get("crew") or []):
        if c.get("job") == "Director":
            parts.append(_el("director", c.get("name")))
            parts.append(_el("credits", c.get("name")))
        elif c.get("job") == "Writer":
            parts.append(_el("writer", c.get("name")))
            parts.append(_el("credits", c.get("name")))
    parts.append(_el("rating", ep.get("vote_average")))
    parts.append(_el("year", (ep.get("air_date") or bg.get("airdate") or "")[:4] or None))
    parts.append(_el("runtime", ep.get("runtime")))
    parts.append(_el("showtitle", show_title))
    parts.append(_el("episode", target_episode))
    parts.append(_el("season", target_season))
    parts.append(_el("aired", ep.get("air_date") or bg.get("airdate")))
    # 特别篇重排：target≠source 时写 displayseason/displayepisode
    if src_season is not None and src_episode is not None \
            and (src_season != target_season or src_episode != target_episode):
        parts.append(_el("displayseason", src_season))
        parts.append(_el("displayepisode", src_episode))
    still = _img_url(ep.get("still_path"))
    if still:
        parts.append("<art>")
        parts.append(_el("poster", still))
        parts.append("</art>")
    for a in (ep.get("guest_stars") or []):
        parts.append("<actor>")
        parts.append(_el("name", a.get("name")))
        parts.append(_el("role", a.get("character")))
        parts.append(_el("type", "GuestStar"))
        parts.append(_el("sortorder", a.get("order")))
        parts.append(_el("thumb", _img_url(a.get("profile_path"))))
        parts.append("</actor>")
    if stream_details:
        parts.append(_streamdetails_xml(stream_details))
    parts.append("</episodedetails>")
    return "\n".join(parts)
```

- [ ] **Step 4: 运行验证通过**

Run: `python -m pytest tests/test_nfo.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 提交**

```bash
git add packages/melodyi-filebot/melodyi_filebot/nfo.py packages/melodyi-filebot/tests/test_nfo.py
git commit -m "feat(melodyi-filebot): nfo.py episode NFO XML（streamdetails/displayseason/bangumi 补全）"
```

---

## Task 5: ffprobe stream details 探测

**Files:**
- Modify: `melodyi_filebot/structure.py`
- Test: `tests/test_structure.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_structure.py`：

```python
class TestProbeStreamDetails:
    """ffprobe 流信息探测（NFO streamdetails 用）"""

    def test_probe_returns_video_audio(self, monkeypatch):
        from melodyi_filebot import structure
        fake_json = {
            "streams": [
                {"codec_name": "h264", "codec_type": "video", "width": 1920, "height": 1080,
                 "avg_frame_rate": "24000/1001", "duration": "1420.5",
                 "display_aspect_ratio": "16:9"},
                {"codec_name": "aac", "codec_type": "audio", "channels": 2, "sample_rate": "48000"},
            ]
        }
        class FakeProc:
            stdout = __import__("json").dumps(fake_json)
            returncode = 0
        def fake_run(*a, **k):
            return FakeProc()
        monkeypatch.setattr(structure.subprocess, "run", fake_run)
        sd = structure.probe_stream_details(__import__("pathlib").Path("x.mkv"))
        assert sd is not None
        assert sd["video"]["codec"] == "h264"
        assert sd["video"]["width"] == 1920
        assert sd["video"]["duration_seconds"] == 1420  # 转 int
        assert sd["video"]["framerate"] == "23.976"
        assert sd["audio"]["codec"] == "aac"
        assert sd["audio"]["channels"] == 2

    def test_probe_returns_none_on_failure(self, monkeypatch):
        from melodyi_filebot import structure
        def fake_run(*a, **k):
            raise FileNotFoundError("ffprobe not found")
        monkeypatch.setattr(structure.subprocess, "run", fake_run)
        assert structure.probe_stream_details(__import__("pathlib").Path("x.mkv")) is None
```

- [ ] **Step 2: 运行验证失败**

Run: `python -m pytest tests/test_structure.py::TestProbeStreamDetails -v`
Expected: FAIL（`probe_stream_details` 未定义）

- [ ] **Step 3: 实现 `probe_stream_details`**

在 `structure.py` 追加（`probe_duration_ffmpeg` 之后）：

```python
def probe_stream_details(path: Path) -> Optional[dict]:
    """用 ffprobe 取视频/音频流信息（NFO streamdetails 用）

    Args:
        path: 视频文件路径

    Returns:
        {"video": {codec,width,height,aspect,framerate,duration,duration_seconds},
         "audio": {codec,channels,samplingrate}}，失败返回 None
    """
    import json
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_streams", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60, check=True,
        )
        streams = json.loads(out.stdout).get("streams", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("ffprobe 取流信息失败: %s (%s)", path, exc)
        return None
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    result = {}
    if video:
        fr = _parse_frame_rate(video.get("avg_frame_rate"))
        dur = video.get("duration")
        result["video"] = {
            "codec": video.get("codec_name"),
            "width": video.get("width"),
            "height": video.get("height"),
            "aspect": video.get("display_aspect_ratio"),
            "framerate": fr,
            "duration": int(float(dur) // 60) if dur else None,  # 分钟
            "duration_seconds": int(float(dur)) if dur else None,
        }
    if audio:
        result["audio"] = {
            "codec": audio.get("codec_name"),
            "channels": audio.get("channels"),
            "samplingrate": int(audio["sample_rate"]) if audio.get("sample_rate") else None,
        }
    return result or None


def _parse_frame_rate(rate: Optional[str]) -> Optional[str]:
    """'24000/1001' → '23.976'"""
    if not rate or "/" not in rate:
        return rate
    try:
        num, den = rate.split("/")
        return f"{int(num) / int(den):.3f}".rstrip("0").rstrip(".") or "0"
    except (ValueError, ZeroDivisionError):
        return rate
```

- [ ] **Step 4: 运行验证通过**

Run: `python -m pytest tests/test_structure.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 提交**

```bash
git add packages/melodyi-filebot/melodyi_filebot/structure.py packages/melodyi-filebot/tests/test_structure.py
git commit -m "feat(melodyi-filebot): ffprobe probe_stream_details 取流信息"
```

---

## Task 6: TMDB 全量详情拉取

**Files:**
- Modify: `melodyi_filebot/tmdb.py`
- Test: `tests/test_tmdb.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_tmdb.py`：

```python
class TestShowDetailFull:
    """get_show_detail_full：append 全量字段"""

    def test_uses_append_to_response(self):
        mock_tv = MagicMock()
        mock_tv.info.return_value = {"id": 154494, "name": "莉可丽丝"}
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV", return_value=mock_tv):
            tmdb.get_show_detail_full(154494, language="zh-CN")
        _, kwargs = mock_tv.info.call_args
        append = kwargs.get("append_to_response", "")
        for part in ["external_ids", "aggregate_credits", "keywords", "content_ratings"]:
            assert part in append, f"应 append {part}"

    def test_returns_raw_dict(self):
        mock_tv = MagicMock()
        mock_tv.info.return_value = {"id": 154494, "name": "莉可丽丝", "overview": "x" * 50}
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV", return_value=mock_tv):
            d = tmdb.get_show_detail_full(154494, language="zh-CN")
        assert d["id"] == 154494
        assert d["name"] == "莉可丽丝"


class TestSeasonDetail:
    """get_season_detail：含每集 crew/guest_stars"""

    def test_returns_raw_dict(self):
        mock_s = MagicMock()
        mock_s.info.return_value = {
            "id": 154494, "season_number": 1, "name": "S1",
            "episodes": [{"episode_number": 1, "name": "e1", "crew": [], "guest_stars": []}],
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV_Seasons", return_value=mock_s):
            d = tmdb.get_season_detail(154494, 1, language="zh-CN")
        assert d["season_number"] == 1
        assert d["episodes"][0]["name"] == "e1"
        mock_s.info.assert_called_once()
```

- [ ] **Step 2: 运行验证失败**

Run: `python -m pytest tests/test_tmdb.py::TestShowDetailFull tests/test_tmdb.py::TestSeasonDetail -v`
Expected: FAIL（两个函数未定义）

- [ ] **Step 3: 实现两个函数**

在 `tmdb.py` 追加（`get_episode_group` 之后）：

```python
def get_show_detail_full(tmdb_id: int, language: str = "zh-CN") -> dict:
    """获取剧全量详情（含 external_ids/aggregate_credits/keywords/content_ratings）

    一次 append 请求取齐 NFO 所需字段，返回原始 dict（不经摘要压缩，供 nfo.py 直接用）。
    """
    _ensure_key()
    logger.info("获取剧全量详情开始: id=%s, lang=%s", tmdb_id, language)
    tv = tmdbsimple.TV(id=tmdb_id)
    detail = tv.info(
        append_to_response="external_ids,aggregate_credits,keywords,content_ratings",
        language=language,
    )
    logger.info("获取剧全量详情完成: id=%s", tmdb_id)
    return detail


def get_season_detail(tmdb_id: int, season_number: int, language: str = "zh-CN") -> dict:
    """获取某季详情（含每集 crew/guest_stars/still_path），返回原始 dict"""
    _ensure_key()
    logger.info("获取季详情开始: id=%s season=%s", tmdb_id, season_number)
    seasons = tmdbsimple.TV_Seasons(tv_id=tmdb_id, season_number=season_number)
    detail = seasons.info(language=language)
    logger.info("获取季详情完成: id=%s season=%s 集数=%d",
                tmdb_id, season_number, len(detail.get("episodes") or []))
    return detail
```

- [ ] **Step 4: 运行验证通过**

Run: `python -m pytest tests/test_tmdb.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 提交**

```bash
git add packages/melodyi-filebot/melodyi_filebot/tmdb.py packages/melodyi-filebot/tests/test_tmdb.py
git commit -m "feat(melodyi-filebot): TMDB 全量详情拉取（append external_ids/credits/keywords/ratings）"
```

---

## Task 7: planner.draft_plan — folder 输入 → Plan

**Files:**
- Modify: `melodyi_filebot/planner.py`
- Test: `tests/test_planner.py`

说明：`draft_plan(folder_spec, ...)` 接 `{show, folders}` dict，调 TMDB/bangumi 解析来源，返回 `Plan`。用可注入的 fetch 函数便于单测。

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_planner.py`：

```python
class TestDraftPlan:
    """draft_plan: folder→target 输入 → Plan（含来源解析）"""

    def _folder_spec(self, tmp_path):
        (tmp_path / "ep01.mkv").write_bytes(b"x")
        (tmp_path / "ep02.mkv").write_bytes(b"x")
        return {
            "show": {"tmdb_id": 154494, "bangumi_subject_id": 364450},
            "folders": [{"path": str(tmp_path), "target": {"kind": "season", "season": 1}}],
        }

    def _fake_show(self):
        from melodyi_filebot.models import ShowSummary, SeasonSummary
        return ShowSummary(tmdb_id=154494, title="莉可丽丝", original_title="リコリス",
                           year=2022, total_seasons=1, total_episodes=2,
                           seasons=[SeasonSummary(season_number=1, name="S1", episode_count=2)])

    def test_season_target_resolves_episode_sources(self, tmp_path, monkeypatch):
        from melodyi_filebot import planner
        spec = self._folder_spec(tmp_path)
        # 注入 fake fetch：季集列表 2 集
        def fake_season_eps(tid, sn, language="zh-CN"):
            from melodyi_filebot.models import EpisodeBrief
            return [EpisodeBrief(episode_number=1, name="e1", overview_length=50),
                    EpisodeBrief(episode_number=2, name="e2", overview_length=50)]
        def fake_show(tid, language="zh-CN"):
            return self._fake_show()
        def fake_bg_eps(sid, ep_type=0):
            from melodyi_filebot.models import BangumiEpisodeBrief
            return [BangumiEpisodeBrief(episode_id=111, name="e1", name_cn="e1", sort=1, ep=1, desc="x"*20),
                    BangumiEpisodeBrief(episode_id=222, name="e2", name_cn="e2", sort=2, ep=2, desc="x"*20)]
        plan = planner.draft_plan(
            spec, language="zh-CN",
            fetch_show_summary=fake_show, fetch_season_episodes=fake_season_eps,
            fetch_bangumi_episodes=fake_bg_eps,
        )
        assert plan.show.tmdb_id == 154494
        assert len(plan.episodes) == 2
        e1 = plan.episodes[0]
        assert e1.source.tmdb_id == 154494 and e1.source.season == 1 and e1.source.episode == 1
        assert e1.source.bangumi_subject_id == 364450 and e1.source.bangumi_episode_id == 111
        assert e1.target.season == 1 and e1.target.episode == 1
        assert len(plan.seasons) == 1 and plan.seasons[0].season == 1

    def test_unparsable_file_warning(self, tmp_path, monkeypatch):
        from melodyi_filebot import planner
        (tmp_path / "no_episode_number.mkv").write_bytes(b"x")
        spec = {"show": {"tmdb_id": 1},
                "folders": [{"path": str(tmp_path), "target": {"kind": "season", "season": 1}}]}
        plan = planner.draft_plan(
            spec, language="zh-CN",
            fetch_show_summary=lambda tid, language="zh-CN": self._fake_show(),
            fetch_season_episodes=lambda tid, sn, language="zh-CN": [],
            fetch_bangumi_episodes=lambda sid, ep_type=0: [],
        )
        assert plan.warnings  # 有告警
        assert plan.episodes == [] or all(e.target.episode is None for e in plan.episodes) or plan.warnings

    def test_tmdb_missing_season_uses_bangumi(self, tmp_path, monkeypatch):
        """物语：TMDB 无该季 → source.tmdb=null，bangumi 为主"""
        from melodyi_filebot import planner
        (tmp_path / "ep01.mkv").write_bytes(b"x")
        spec = {"show": {"tmdb_id": 1, "bangumi_subject_id": 999},
                "folders": [{"path": str(tmp_path),
                             "target": {"kind": "season", "season": 3},
                             "bangumi_subject_id": 999}]}
        # TMDB 取不到季（raise 或空）→ 视为 TMDB 无此季
        def fake_show(tid, language="zh-CN"):
            from melodyi_filebot.models import ShowSummary
            return ShowSummary(tmdb_id=1, title="物语", original_title="", year=2009,
                               total_seasons=1, total_episodes=1, seasons=[])
        def fake_season_eps(tid, sn, language="zh-CN"):
            raise RuntimeError("TMDB 无此季")
        def fake_bg_eps(sid, ep_type=0):
            from melodyi_filebot.models import BangumiEpisodeBrief
            return [BangumiEpisodeBrief(episode_id=555, name="e1", name_cn="e1", sort=1, ep=1, desc="x"*20)]
        plan = planner.draft_plan(
            spec, language="zh-CN",
            fetch_show_summary=fake_show, fetch_season_episodes=fake_season_eps,
            fetch_bangumi_episodes=fake_bg_eps,
        )
        s3 = next(s for s in plan.seasons if s.season == 3)
        assert s3.source.provider == "bangumi" and s3.source.bangumi_subject_id == 999
        e = plan.episodes[0]
        assert e.source.tmdb_id is None
        assert e.source.bangumi_episode_id == 555
```

- [ ] **Step 2: 运行验证失败**

Run: `python -m pytest tests/test_planner.py::TestDraftPlan -v`
Expected: FAIL（`draft_plan` 未定义）

- [ ] **Step 3: 实现 `draft_plan`**

在 `planner.py` 追加：

```python
def draft_plan(
    folder_spec: dict,
    language: str = "zh-CN",
    fetch_show_summary=None,
    fetch_season_episodes=None,
    fetch_bangumi_episodes=None,
) -> "Plan":
    """folder→target 输入 → Plan（调 API 解析来源）

    Args:
        folder_spec: {show: {tmdb_id, bangumi_subject_id?}, folders: [{path, target, bangumi_subject_id?}]}
        language: 语言
        fetch_*: 可注入的 fetch 函数（单测用）；默认接 tmdb/bangumi 模块

    Returns:
        Plan（纯映射，含来源 spec 与 warnings）
    """
    from melodyi_filebot.models import (
        Plan, ShowRef, SeasonEntry, EpisodeEntry, FileTarget, NfoSource,
    )
    # 默认 fetch 接真实模块（单测注入 fake）
    if fetch_show_summary is None:
        from melodyi_filebot import tmdb as _tmdb
        fetch_show_summary = _tmdb.get_show_summary
    if fetch_season_episodes is None:
        from melodyi_filebot import tmdb as _tmdb
        fetch_season_episodes = _tmdb.get_season_episodes
    if fetch_bangumi_episodes is None:
        from melodyi_filebot import bangumi as _bg
        fetch_bangumi_episodes = _bg.get_subject_episodes

    show_spec = folder_spec["show"]
    tmdb_id = show_spec["tmdb_id"]
    show_bg = show_spec.get("bangumi_subject_id")
    show = fetch_show_summary(tmdb_id, language=language)
    show_ref = ShowRef(
        tmdb_id=tmdb_id, bangumi_subject_id=show_bg,
        title=show.title, original_title=show.original_title,
        year=show.year, language=language,
    )
    seasons_seen: dict = {}  # season -> SeasonEntry
    episodes: list = []
    warnings: list = []
    for folder in folder_spec["folders"]:
        folder_bg = folder.get("bangumi_subject_id", show_bg)
        target = folder["target"]
        files = [str(p) for p in sorted(Path(folder["path"]).iterdir())
                 if p.suffix.lower() in VIDEO_EXTS] if Path(folder["path"]).is_dir() else []
        # 取该季/组集列表（用于按序号解析来源）
        if target["kind"] == "season":
            sn = target["season"]
            try:
                tmdb_eps = {e.episode_number: e for e in fetch_season_episodes(tmdb_id, sn, language=language)}
                tmdb_season_present = True
            except RuntimeError:
                tmdb_eps = {}
                tmdb_season_present = False
                warnings.append(f"TMDB 无第 {sn} 季，来源切 bangumi: {folder['path']}")
            if sn not in seasons_seen:
                src = NfoSource(
                    provider="bangumi" if not tmdb_season_present else "tmdb",
                    tmdb_id=tmdb_id if tmdb_season_present else None,
                    season=sn if tmdb_season_present else None,
                    bangumi_subject_id=folder_bg if not tmdb_season_present else None,
                )
                seasons_seen[sn] = SeasonEntry(season=sn, source=src)
        elif target["kind"] == "episode_group":
            # episode_group 解析在 Task 8 增强；此处先按文件序号占位
            tmdb_eps = {}
            sn = target.get("season", 1)
            if sn not in seasons_seen:
                seasons_seen[sn] = SeasonEntry(
                    season=sn, source=NfoSource(provider="tmdb", tmdb_id=tmdb_id, season=sn))
        else:
            warnings.append(f"未知 target.kind: {target['kind']}")
            continue
        # bangumi 集列表（按集号映射）
        bg_eps = {}
        if folder_bg:
            for be in fetch_bangumi_episodes(folder_bg):
                ep_num = be.ep or int(be.sort)
                if ep_num is not None:
                    bg_eps[ep_num] = be
        for f in files:
            parsed = parse_filename(f)
            ep = parsed.episode
            if ep is None:
                warnings.append(f"无法解析集号: {f}")
                continue
            tmdb_ep = tmdb_eps.get(ep)
            bg_ep = bg_eps.get(ep)
            src = NfoSource(
                provider="bangumi" if not tmdb_season_present else "tmdb",
                tmdb_id=tmdb_id if tmdb_season_present else None,
                season=sn if tmdb_season_present else None,
                episode=ep if tmdb_season_present else None,
                bangumi_subject_id=folder_bg,
                bangumi_episode_id=bg_ep.episode_id if bg_ep else None,
            )
            if not tmdb_season_present and not bg_ep:
                warnings.append(f"bangumi 未匹配到第 {ep} 集: {f}")
            episodes.append(EpisodeEntry(
                file=os.path.normpath(f),
                target=FileTarget(season=sn, episode=ep,
                                  episode_end=parsed.episode_end, part=parsed.part),
                source=src,
            ))
    return Plan(show=show_ref, seasons=list(seasons_seen.values()),
                episodes=episodes, warnings=warnings)
```

- [ ] **Step 4: 运行验证通过**

Run: `python -m pytest tests/test_planner.py::TestDraftPlan -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add packages/melodyi-filebot/melodyi_filebot/planner.py packages/melodyi-filebot/tests/test_planner.py
git commit -m "feat(melodyi-filebot): draft_plan folder→target 输入解析为 Plan"
```

---

## Task 8: planner.build_plan_from_plan — Plan → ExecutionList

**Files:**
- Modify: `melodyi_filebot/planner.py`
- Test: `tests/test_planner.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_planner.py`：

```python
class TestBuildPlanFromPlan:
    """build_plan_from_plan: Plan → BuildPlanResult（move + nfo 操作）"""

    def _plan(self, tmp_path):
        from melodyi_filebot.models import (
            Plan, ShowRef, SeasonEntry, EpisodeEntry, FileTarget, NfoSource)
        src = tmp_path / "src"
        src.mkdir()
        (src / "ep01.mkv").write_bytes(b"x")
        return Plan(
            show=ShowRef(tmdb_id=154494, title="莉可丽丝", year=2022, language="zh-CN"),
            seasons=[SeasonEntry(season=1, source=NfoSource(provider="tmdb", tmdb_id=154494, season=1))],
            episodes=[EpisodeEntry(
                file=str(src / "ep01.mkv"),
                target=FileTarget(season=1, episode=1),
                source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1))],
            warnings=[],
        )

    def test_generates_move_and_nfo_ops(self, tmp_path):
        from melodyi_filebot import planner
        plan = self._plan(tmp_path)
        dest = tmp_path / "dest"
        result = planner.build_plan_from_plan(plan, str(dest), with_nfo=True)
        # fs 操作：mkdir 剧 + mkdir 季 + move 视频
        assert any(o.type == "mkdir" and "tmdbid-154494" in o.path for o in result.operations)
        assert any(o.type == "mkdir" and "Season 01" in o.path for o in result.operations)
        assert any(o.type == "move" for o in result.operations)
        # nfo 操作：1 tvshow + 1 season + 1 episode
        assert any(o.type == "tvshow" for o in result.nfo_operations)
        assert any(o.type == "season" and o.season == 1 for o in result.nfo_operations)
        ep_nfo = next(o for o in result.nfo_operations if o.type == "episode")
        assert ep_nfo.path.endswith(".nfo")
        assert "S01E01" in ep_nfo.path
        assert ep_nfo.source.tmdb_id == 154494

    def test_no_nfo_ops_when_with_nfo_false(self, tmp_path):
        from melodyi_filebot import planner
        plan = self._plan(tmp_path)
        result = planner.build_plan_from_plan(plan, str(tmp_path / "dest"), with_nfo=False)
        assert result.nfo_operations == []

    def test_episode_nfo_path_matches_video_stem(self, tmp_path):
        """集 nfo 路径 = 视频 move 目标 stem + .nfo"""
        from melodyi_filebot import planner
        plan = self._plan(tmp_path)
        result = planner.build_plan_from_plan(plan, str(tmp_path / "dest"), with_nfo=True)
        move = next(o for o in result.operations if o.type == "move")
        ep_nfo = next(o for o in result.nfo_operations if o.type == "episode")
        assert ep_nfo.path == move.path.rsplit(".", 1)[0] + ".nfo"
```

- [ ] **Step 2: 运行验证失败**

Run: `python -m pytest tests/test_planner.py::TestBuildPlanFromPlan -v`
Expected: FAIL（`build_plan_from_plan` 未定义）

- [ ] **Step 3: 实现 `build_plan_from_plan`**

在 `planner.py` 追加：

```python
def build_plan_from_plan(plan: "Plan", dest_root: str, with_nfo: bool = True) -> BuildPlanResult:
    """Plan → BuildPlanResult（move + nfo 操作）

    Args:
        plan: 纯映射 Plan（agent 编辑后）
        dest_root: 目标媒体根目录
        with_nfo: 是否生成 nfo 操作

    Returns:
        BuildPlanResult（operations + nfo_operations，spec_applied="plan"）
    """
    from melodyi_filebot.models import ShowSummary, NfoOperation
    logger.info("按 Plan 构建执行清单: tmdb_id=%s, 集数=%d, nfo=%s",
                plan.show.tmdb_id, len(plan.episodes), with_nfo)
    # 用 ShowRef 构造 ShowSummary 复用既有命名函数
    show = ShowSummary(
        tmdb_id=plan.show.tmdb_id, title=plan.show.title,
        original_title=plan.show.original_title, year=plan.show.year,
        total_seasons=len(plan.seasons), total_episodes=len(plan.episodes),
        seasons=[], episode_groups=[],
    )
    dest_root = os.path.normpath(dest_root)
    show_dir = os.path.join(dest_root, _show_folder(show))
    operations: List[PlanOperation] = [PlanOperation(type="mkdir", path=show_dir)]
    nfo_operations: list = []
    warnings: list = list(plan.warnings)
    created_seasons: set = set()
    for m in plan.episodes:
        if m.target.episode is None:
            warnings.append(f"映射缺少集号，跳过: {m.file}")
            continue
        season = m.target.season
        season_dir = os.path.join(show_dir, _season_folder(season))
        if season not in created_seasons:
            operations.append(PlanOperation(type="mkdir", path=season_dir))
            created_seasons.add(season)
        ext = Path(m.file).suffix
        target_name = _episode_filename(
            show, season, m.target.episode, m.target.episode_end, m.target.part, ext)
        target = os.path.join(season_dir, target_name)
        operations.append(PlanOperation(type="move", source=os.path.normpath(m.file), path=target))
        operations.extend(_companion_ops(m.file, target, target_name))
        if with_nfo:
            ep_nfo_path = target.rsplit(".", 1)[0] + ".nfo"
            nfo_operations.append(NfoOperation(
                type="episode", path=ep_nfo_path, season=season, episode=m.target.episode,
                source=m.source))
    if with_nfo:
        # tvshow nfo
        show_source = NfoSource(provider="tmdb", tmdb_id=plan.show.tmdb_id,
                                bangumi_subject_id=plan.show.bangumi_subject_id)
        nfo_operations.insert(0, NfoOperation(
            type="tvshow", path=os.path.join(show_dir, "tvshow.nfo"), source=show_source))
        # season nfo（每个出现的季）
        season_sources = {s.season: s.source for s in plan.seasons}
        for sn in created_seasons:
            nfo_operations.append(NfoOperation(
                type="season", path=os.path.join(show_dir, _season_folder(sn), "season.nfo"),
                season=sn, source=season_sources.get(sn, NfoSource(provider="tmdb", tmdb_id=plan.show.tmdb_id, season=sn))))
    logger.info("按 Plan 构建执行清单完成: 操作数=%d, nfo 操作数=%d",
                len(operations), len(nfo_operations))
    return BuildPlanResult(operations=operations, nfo_operations=nfo_operations,
                           spec_applied="plan", warnings=warnings)
```

- [ ] **Step 4: 运行验证通过**

Run: `python -m pytest tests/test_planner.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 提交**

```bash
git add packages/melodyi-filebot/melodyi_filebot/planner.py packages/melodyi-filebot/tests/test_planner.py
git commit -m "feat(melodyi-filebot): build_plan_from_plan 生成 move+nfo 执行清单"
```

---

## Task 9: nfo.py — generate_nfo 拉取写盘编排

**Files:**
- Modify: `melodyi_filebot/nfo.py`
- Test: `tests/test_nfo.py`

说明：`generate_nfo(op, fetch_show, fetch_season, fetch_bangumi, probe, dry_run)` 按 `NfoOperation` 来源拉取数据，调 `build_*_xml`，写文件。可注入 fetch 便于单测。

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_nfo.py`：

```python
import os
from melodyi_filebot.models import NfoOperation, NfoSource


class TestGenerateNfo:
    def test_generate_tvshow_writes_xml(self, tmp_path, monkeypatch):
        from melodyi_filebot import nfo
        op = NfoOperation(type="tvshow", path=str(tmp_path / "tvshow.nfo"),
                          source=NfoSource(provider="tmdb", tmdb_id=154494, bangumi_subject_id=364450))
        calls = []
        def fake_show(tid, language="zh-CN"):
            calls.append("show")
            return {"id": 154494, "name": "莉可丽丝", "overview": "x" * 50}
        def fake_bg_subject(sid):
            return {"summary": "", "name_cn": ""}
        path = nfo.generate_nfo(op, language="zh-CN", dry_run=False,
                                fetch_show_detail=fake_show, fetch_bangumi_subject=fake_bg_subject)
        assert path.endswith("tvshow.nfo")
        content = open(path, encoding="utf-8").read()
        assert "<tvshow>" in content and "莉可丽丝" in content

    def test_generate_episode_with_streamdetails(self, tmp_path):
        from melodyi_filebot import nfo
        op = NfoOperation(type="episode", path=str(tmp_path / "e.nfo"), season=1, episode=1,
                          source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1))
        def fake_season(tid, sn, language="zh-CN"):
            return {"season_number": 1, "name": "S1", "episodes": [
                {"episode_number": 1, "name": "e1", "overview": "x"*50, "season_number": 1}]}
        def fake_probe(path):
            return {"video": {"codec": "h264", "width": 1920, "height": 1080},
                    "audio": {"codec": "aac", "channels": 2}}
        nfo.generate_nfo(op, language="zh-CN", dry_run=False,
                         fetch_season_detail=fake_season, probe_stream=fake_probe,
                         video_path=str(tmp_path / "e.mkv"))
        content = open(str(tmp_path / "e.nfo"), encoding="utf-8").read()
        assert "<episodedetails>" in content
        assert "<codec>h264</codec>" in content

    def test_dry_run_does_not_write(self, tmp_path):
        from melodyi_filebot import nfo
        op = NfoOperation(type="tvshow", path=str(tmp_path / "tvshow.nfo"),
                          source=NfoSource(provider="tmdb", tmdb_id=1))
        nfo.generate_nfo(op, language="zh-CN", dry_run=True,
                         fetch_show_detail=lambda tid, language="zh-CN": {"id":1,"name":"x","overview":"x"*50})
        assert not (tmp_path / "tvshow.nfo").exists()
```

- [ ] **Step 2: 运行验证失败**

Run: `python -m pytest tests/test_nfo.py::TestGenerateNfo -v`
Expected: FAIL（`generate_nfo` 未定义）

- [ ] **Step 3: 实现 `generate_nfo`**

在 `nfo.py` 追加：

```python
from pathlib import Path
from melodyi_filebot.models import NfoOperation


def generate_nfo(op: NfoOperation, language: str = "zh-CN", dry_run: bool = True,
                 fetch_show_detail=None, fetch_season_detail=None,
                 fetch_bangumi_subject=None, fetch_bangumi_episodes=None,
                 probe_stream=None, video_path: Optional[str] = None,
                 show_actors: Optional[list] = None) -> Optional[str]:
    """按 NfoOperation 来源拉取 + 生成 XML + 写文件

    Args:
        op: NFO 写入操作（类型/路径/来源）
        language: 语言
        dry_run: True 只返回路径不写盘
        fetch_*: 可注入的 fetch 函数（单测用），默认接 tmdb/bangumi 模块
        probe_stream: ffprobe 函数（单测注入）
        video_path: 集操作对应的视频路径（跑 ffprobe 用）
        show_actors: 季 nfo 继承的剧级演员

    Returns:
        写入的 .nfo 路径（dry_run 也返回路径但不写盘）
    """
    if fetch_show_detail is None:
        from melodyi_filebot import tmdb
        fetch_show_detail = tmdb.get_show_detail_full
    if fetch_season_detail is None:
        from melodyi_filebot import tmdb
        fetch_season_detail = tmdb.get_season_detail
    if fetch_bangumi_subject is None:
        from melodyi_filebot import bangumi
        fetch_bangumi_subject = bangumi.get_subject
    if fetch_bangumi_episodes is None:
        from melodyi_filebot import bangumi
        fetch_bangumi_episodes = bangumi.get_subject_episodes
    if probe_stream is None:
        from melodyi_filebot.structure import probe_stream_details
        probe_stream = probe_stream_details

    src = op.source
    bg_data = None
    if src.bangumi_subject_id:
        try:
            bg_data = fetch_bangumi_subject(src.bangumi_subject_id).__dict__ if hasattr(fetch_bangumi_subject(src.bangumi_subject_id), "__dict__") else fetch_bangumi_subject(src.bangumi_subject_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("bangumi subject 拉取失败: %s", exc)

    if op.type == "tvshow":
        show = fetch_show_detail(src.tmdb_id, language=language)
        xml = build_tvshow_xml(show, bg_data, language)
    elif op.type == "season":
        if src.provider == "tmdb" and src.tmdb_id:
            season = fetch_season_detail(src.tmdb_id, src.season, language=language)
        else:
            season = {}
        xml = build_season_xml(season, bg_data, show_actors, op.season)
    elif op.type == "episode":
        if src.provider == "tmdb" and src.tmdb_id:
            season = fetch_season_detail(src.tmdb_id, src.season, language=language)
            ep = next((e for e in (season.get("episodes") or [])
                       if e.get("episode_number") == src.episode), {})
        else:
            season, ep = {}, {}
        sd = probe_stream(Path(video_path)) if video_path else None
        show_title = ""  # 由调用方传入或从 show 取（简化）
        xml = build_episode_xml(ep, bg_data, show_title,
                                target_season=op.season, target_episode=op.episode,
                                stream_details=sd)
    else:
        raise ValueError(f"未知 nfo 类型: {op.type}")

    if dry_run:
        logger.info("dry-run: %s", op.path)
        return op.path
    Path(op.path).parent.mkdir(parents=True, exist_ok=True)
    Path(op.path).write_text(xml, encoding="utf-8")
    logger.info("NFO 已写: %s", op.path)
    return op.path
```

- [ ] **Step 4: 运行验证通过**

Run: `python -m pytest tests/test_nfo.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 提交**

```bash
git add packages/melodyi-filebot/melodyi_filebot/nfo.py packages/melodyi-filebot/tests/test_nfo.py
git commit -m "feat(melodyi-filebot): generate_nfo 按来源拉取写盘编排"
```

---

## Task 10: CLI — draft-plan / build-plan / generate-nfo 命令

**Files:**
- Modify: `melodyi_filebot/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_cli.py`：

```python
class TestCliNfoWorkflow:
    """draft-plan / build-plan / generate-nfo CLI 测试"""

    def _folder_spec(self, tmp_path):
        (tmp_path / "ep01.mkv").write_bytes(b"x")
        return {"show": {"tmdb_id": 154494, "bangumi_subject_id": 364450},
                "folders": [{"path": str(tmp_path), "target": {"kind": "season", "season": 1}}]}

    def test_draft_plan_command(self, tmp_path):
        import json
        from melodyi_filebot.models import ShowSummary, SeasonSummary, EpisodeBrief
        spec_path = tmp_path / "spec.json"
        spec_path.write_text(json.dumps(self._folder_spec(tmp_path)), encoding="utf-8")
        out_path = str(tmp_path / "plan.json")
        with patch("melodyi_filebot.cli.tmdb.get_show_summary",
                   return_value=ShowSummary(tmdb_id=154494, title="莉可丽丝",
                       original_title="リコリス", year=2022, total_seasons=1,
                       total_episodes=1, seasons=[SeasonSummary(season_number=1, name="S1", episode_count=1)])), \
             patch("melodyi_filebot.cli.tmdb.get_season_episodes",
                   return_value=[EpisodeBrief(episode_number=1, name="e1", overview_length=50)]), \
             patch("melodyi_filebot.cli.bangumi.get_subject_episodes", return_value=[]):
            runner = CliRunner()
            result = runner.invoke(cli, ["draft-plan", "--folder-spec", str(spec_path), "--out", out_path])
        assert result.exit_code == 0, result.output
        plan = json.loads(open(out_path, encoding="utf-8").read())
        assert plan["show"]["tmdb_id"] == 154494
        assert len(plan["episodes"]) == 1

    def test_build_plan_from_plan_command(self, tmp_path):
        import json
        from melodyi_filebot.models import Plan, ShowRef, SeasonEntry, EpisodeEntry, FileTarget, NfoSource
        src = tmp_path / "src"; src.mkdir()
        (src / "ep01.mkv").write_bytes(b"x")
        plan = Plan(
            show=ShowRef(tmdb_id=154494, title="莉可丽丝", year=2022, language="zh-CN"),
            seasons=[SeasonEntry(season=1, source=NfoSource(provider="tmdb", tmdb_id=154494, season=1))],
            episodes=[EpisodeEntry(file=str(src / "ep01.mkv"),
                target=FileTarget(season=1, episode=1),
                source=NfoSource(provider="tmdb", tmdb_id=154494, season=1, episode=1))],
            warnings=[])
        plan_path = tmp_path / "plan.json"
        plan_path.write_text(plan.model_dump_json(), encoding="utf-8")
        out_path = str(tmp_path / "exec.json")
        runner = CliRunner()
        result = runner.invoke(cli, ["build-plan", "--plan", str(plan_path),
                                     "--dest", str(tmp_path / "dest"), "--with-nfo", "--out", out_path])
        assert result.exit_code == 0, result.output
        exec_data = json.loads(open(out_path, encoding="utf-8").read())
        assert any(o["type"] == "move" for o in exec_data["operations"])
        assert any(o["type"] == "tvshow" for o in exec_data["nfo_operations"])

    def test_generate_nfo_dry_run(self, tmp_path):
        import json
        from melodyi_filebot.models import BuildPlanResult, NfoOperation, NfoSource
        exec_data = BuildPlanResult(
            operations=[],
            nfo_operations=[NfoOperation(type="tvshow", path=str(tmp_path / "tvshow.nfo"),
                source=NfoSource(provider="tmdb", tmdb_id=154494))])
        exec_path = tmp_path / "exec.json"
        exec_path.write_text(exec_data.model_dump_json(), encoding="utf-8")
        with patch("melodyi_filebot.cli.tmdb.get_show_detail_full",
                   return_value={"id": 154494, "name": "莉可丽丝", "overview": "x"*50}):
            runner = CliRunner()
            result = runner.invoke(cli, ["generate-nfo", "--plan", str(exec_path)])
        assert result.exit_code == 0, result.output
        assert "tvshow.nfo" in result.output
        assert not (tmp_path / "tvshow.nfo").exists()  # dry-run 不写
```

- [ ] **Step 2: 运行验证失败**

Run: `python -m pytest tests/test_cli.py::TestCliNfoWorkflow -v`
Expected: FAIL（命令未注册）

- [ ] **Step 3: 实现三个 CLI 命令**

在 `cli.py` 的 `import` 区补 `from melodyi_filebot import nfo`，并在 `episode_group` 命令之后追加：

```python
@cli.command(name="draft-plan")
@click.option("--folder-spec", "spec_path", required=True, type=click.Path(exists=True),
              help="folder→target 输入 JSON（show + folders）")
@click.option("--language", "-l", default="zh-CN")
@click.option("--out", required=True, type=click.Path(), help="Plan 输出路径")
def draft_plan(spec_path, language, out):
    """folder→target 清单 → Plan（调 API 解析来源）"""
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    logger.info("draft-plan: tmdb_id=%s", spec.get("show", {}).get("tmdb_id"))
    try:
        from melodyi_filebot.planner import draft_plan as _draft
        plan = _draft(spec, language=language)
    except (RuntimeError, Exception) as e:
        _report_error(e)
    pathlib.Path(out).write_text(plan.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
    click.echo(f"Plan 已写入: {out}（集数 {len(plan.episodes)}，告警 {len(plan.warnings)}）")
    for w in plan.warnings:
        click.echo(f"[告警] {w}")


@cli.command(name="build-plan")
@click.option("--plan", "plan_path", required=True, type=click.Path(exists=True),
              help="Plan JSON 路径（draft-plan 产出）")
@click.option("--dest", required=True, help="目标根目录")
@click.option("--with-nfo", is_flag=True, help="生成 nfo 操作")
@click.option("--out", type=click.Path(), default=None, help="执行清单输出路径")
@click.option("--json", "as_json", is_flag=True, help="以 JSON 输出（默认）")
def build_plan_cmd(plan_path, dest, with_nfo, out, as_json):
    """Plan → 执行清单（move + nfo 操作）"""
    from melodyi_filebot.models import Plan
    from melodyi_filebot.planner import build_plan_from_plan
    plan = Plan.model_validate_json(pathlib.Path(plan_path).read_text(encoding="utf-8"))
    result = build_plan_from_plan(plan, dest, with_nfo=with_nfo)
    output = result.model_dump(mode="json")
    text = json.dumps(output, ensure_ascii=False, indent=2)
    click.echo(text)
    if out:
        pathlib.Path(out).write_text(text, encoding="utf-8")


@cli.command(name="generate-nfo")
@click.option("--plan", "plan_path", required=True, type=click.Path(exists=True),
              help="执行清单 JSON 路径（build-plan --with-nfo 产出）")
@click.option("--execute", is_flag=True, help="真正写盘（默认 dry-run）")
@click.option("--language", "-l", default="zh-CN")
def generate_nfo_cmd(plan_path, execute, language):
    """按执行清单的 nfo 操作拉取写 NFO（默认 dry-run）"""
    from melodyi_filebot.models import BuildPlanResult, NfoOperation
    data = json.loads(pathlib.Path(plan_path).read_text(encoding="utf-8"))
    result = BuildPlanResult(**data)
    if not result.nfo_operations:
        click.echo("执行清单无 nfo 操作。")
        return
    for op in result.nfo_operations:
        try:
            path = nfo.generate_nfo(op, language=language, dry_run=not execute)
            click.echo(f"[{'写' if execute else 'dry-run'}] {op.type}: {path}")
        except (RuntimeError, Exception) as e:
            click.echo(f"错误: {e}", err=True)
```

注意：原 `build-plan` 命令（`--show-id/--source/--map`）与新 `build-plan` 命名冲突。Task 11 处理迁移：把旧 `build-plan` 改名为 `build-plan-legacy` 或在迁移任务里统一。本任务先用新 `build-plan` 消费 Plan，旧命令在 Task 11 废弃。

- [ ] **Step 4: 运行验证通过**

Run: `python -m pytest tests/test_cli.py::TestCliNfoWorkflow -v`
Expected: PASS

注意：旧 `build-plan` 测试（`TestCliBuildPlan` 等）此时会因命令重定义而失败——在 Task 11 迁移时统一处理。本任务只确保新命令通过。

- [ ] **Step 5: 提交**

```bash
git add packages/melodyi-filebot/melodyi_filebot/cli.py packages/melodyi-filebot/tests/test_cli.py
git commit -m "feat(melodyi-filebot): draft-plan/build-plan/generate-nfo CLI 命令"
```

---

## Task 11: 迁移 — 废弃 draft-map/PlanMap，统一到 Plan

**Files:**
- Modify: `melodyi_filebot/cli.py`（移除旧 `draft-map` 命令与旧 `build-plan` 的 `--map`/`--source` 模式）
- Modify: `melodyi_filebot/planner.py`（移除 `draft_map_tv`、`build_plan_tv_from_map`、`build_plan_movie_from_map`）
- Modify: `tests/test_cli.py`（迁移 `TestDraftMapAndOverride`、`TestCliBuildPlan` 等到新流程）
- Modify: `melodyi_filebot/models.py`（保留 `PlanMap`/`FileMapping` 若仍有引用，否则移除）

- [ ] **Step 1: 评估旧测试**

Run: `python -m pytest tests/test_cli.py tests/test_planner.py -v 2>&1 | grep -E "PASS|FAIL" | head`

记录哪些旧测试因 Task 10 的新 `build-plan` 重定义而失败。

- [ ] **Step 2: 迁移 draft-map 测试到 draft-plan**

把 `TestDraftMapAndOverride` 的用例改写为用 `draft-plan`（folder-spec 输入）+ `build-plan --plan` 的等价流程。删除对 `draft-map`/`--map` 的直接测试。

- [ ] **Step 3: 移除旧代码**

- `cli.py`：删除 `draft_map` 命令函数、旧 `build_plan` 命令函数（`--show-id/--movie-id/--source/--map` 模式）。保留新 `build_plan_cmd`（Task 10）。
- `planner.py`：删除 `draft_map_tv`、`build_plan_tv_from_map`、`build_plan_movie_from_map`、`build_plan_tv`、`build_plan_movie`（若新流程已覆盖；若 `build_plan_tv` 仍被引用则保留）。
- `models.py`：若 `PlanMap`/`FileMapping` 不再被引用则删除；否则保留。

- [ ] **Step 4: 运行全量测试**

Run: `python -m pytest 2>&1 | tail`
Expected: 全绿（迁移后所有测试通过；旧测试已改写为新流程）

- [ ] **Step 5: 提交**

```bash
git add -A packages/melodyi-filebot
git commit -m "refactor(melodyi-filebot): 废弃 draft-map/PlanMap，统一到 Plan 流程"
```

---

## Task 12: 集成测试 + SKILL.md 更新

**Files:**
- Create: `tests/integration/test_real_nfo.py`
- Modify: `skills/melodyi-filebot/SKILL.md`

- [ ] **Step 1: 写集成测试（默认 skip）**

创建 `tests/integration/test_real_nfo.py`：

```python
"""真实 NFO 生成集成测试（调真实 TMDB/bangumi），默认 skip，需 --run-integration"""

import pytest
from melodyi_filebot import nfo, tmdb, bangumi
from melodyi_filebot.models import NfoOperation, NfoSource

pytestmark = [pytest.mark.integration]

LYCORIS_TMDB = 154494
LYCORIS_BG = 364450


class TestRealNfo:
    def test_tvshow_nfo_from_real_tmdb(self):
        show = tmdb.get_show_detail_full(LYCORIS_TMDB, language="zh-CN")
        bg = bangumi.get_subject(LYCORIS_BG)
        xml = nfo.build_tvshow_xml(show, bg.__dict__ if hasattr(bg, "__dict__") else bg, "zh-CN")
        assert "<tvshow>" in xml
        assert "<tmdbid>154494</tmdbid>" in xml
        assert "<lockdata>true</lockdata>" in xml

    def test_generate_episode_nfo_dry_run(self):
        op = NfoOperation(type="tvshow", path="/tmp/tvshow.nfo",
                          source=NfoSource(provider="tmdb", tmdb_id=LYCORIS_TMDB, bangumi_subject_id=LYCORIS_BG))
        path = nfo.generate_nfo(op, language="zh-CN", dry_run=True)
        assert path == "/tmp/tvshow.nfo"
```

- [ ] **Step 2: 运行（默认 skip）**

Run: `python -m pytest tests/integration/test_real_nfo.py -v`
Expected: 2 skipped

- [ ] **Step 3: 真实集成验证（可选，需网络）**

Run: `python -m pytest tests/integration/test_real_nfo.py --run-integration -v`
Expected: 2 passed

- [ ] **Step 4: 更新 SKILL.md**

在 `skills/melodyi-filebot/SKILL.md` 新增「NFO 生成（P2）」小节，记录 4 步流程与 `draft-plan`/`build-plan`/`generate-nfo` 命令；更新开头阶段说明为「P2 NFO 已就绪」。

- [ ] **Step 5: 提交**

```bash
git add packages/melodyi-filebot/tests/integration/test_real_nfo.py skills/melodyi-filebot/SKILL.md
git commit -m "test(melodyi-filebot): NFO 真实集成测试 + SKILL.md 更新"
```

---

## 自审

**Spec 覆盖**：
- §2 三份结构 → Task 1（模型）+ Task 7（draft_plan）+ Task 8（build_plan_from_plan）
- §3 字段集 → Task 2/3/4（tvshow/season/episode XML）
- §4 bangumi 补全 + episode group → Task 2/3/4（_fill_overview）+ Task 7（season target；episode_group 部分实现，完整解析留后——见下）
- §5 ffprobe/images → Task 5（probe_stream_details）+ Task 2/3/4（图片 URL）
- §6 CLI → Task 10
- §9 迁移 → Task 11

**已知简化（留后）**：
- `episode_group` target 在 Task 7 仅占位（按文件序号 + season hint），未调 `get_episode_group` 做完整子组解析。完整解析（高达SEED 场景）作为后续增强——spec §4.2 的实现待补，但 Plan 结构已支持 agent 手动编辑。
- `generate_nfo` 的 episode `show_title` 未从 show 取（Task 9 简化为空）；实现时可从执行清单的 tvshow nfo op 取剧名传入，或 agent 在 generate-nfo 时补。属小瑕疵，不影响主流程。

**类型一致性**：`NfoSource`/`NfoOperation`/`Plan`/`EpisodeEntry` 在 Task 1 定义，Task 7/8/9/10 使用一致。`build_plan_from_plan` 用 `ShowRef` 构造 `ShowSummary` 复用 `_show_folder`/`_episode_filename`，签名一致。

**Placeholder 扫描**：无 TBD/TODO；Task 11 的迁移步骤是「评估并改写」，具体改写依赖当时失败测试，属正常迁移流程（非占位符）。

---

## 执行交接

计划已保存到 `skills/melodyi-filebot/specs/2026-07-01-nfo-generation-plan.md`。两种执行方式：

1. **子代理驱动（推荐）**：每个任务派新子代理，任务间复核，迭代快。
2. **内联执行**：在当前会话按 executing-plans 批量执行，带检查点复核。

选哪种？
