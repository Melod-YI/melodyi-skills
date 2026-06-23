# melodyi-filebot P0 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 melodyi-filebot 的 P0：基于 TMDB 数据完成剧集/电影的批量重命名与目录整理（不刮削），dry-run 默认，可回滚。

**Architecture:** SKILL.md（agent 编排）+ Python CLI（领域命令）。P0 命令：`search`、`fetch-summary`、`build-plan`、`execute-plan`、`undo`。进上下文的只有摘要与计划，完整 TMDB 元数据不进上下文。文件操作走终端命令，事务日志保证可逆。

**Tech Stack:** Python ≥3.10、Click、Pydantic v2、httpx（tmdbsimple 依赖）、tmdbsimple（TMDB SDK）、pytest。

**参考文档：** `skills/melodyi-filebot/specs/2026-06-23-melodyi-filebot-design.md`

---

## 文件结构

```
skills/melodyi-filebot/
├── SKILL.md                         # Claude 运行时指令
├── pyproject.toml                   # hatchling 打包，entry point: melodyi-filebot
├── .env.example                     # TMDB_API_KEY 示例
├── melodyi_filebot/
│   ├── __init__.py                  # __version__
│   ├── __main__.py                  # python -m 入口
│   ├── config.py                    # 读取 TMDB_API_KEY（env / ~/.melodyi-filebot/config.yaml）
│   ├── models.py                    # Pydantic 模型：Candidate/Show/Season/Episode/Plan 等
│   ├── tmdb.py                      # tmdbsimple 封装：search / get_show_summary / get_season_episodes
│   ├── summarize.py                 # 原始 tmdb dict → 摘要模型（overview_available/length 逻辑）
│   ├── planner.py                   # 文件名 S/E 解析 + build_plan
│   ├── fsops.py                     # 目录扫描 / execute_plan / 事务日志 / undo
│   └── cli.py                       # Click 入口
├── docs/
│   └── search-heuristics.md         # 知识沉淀文档（含 Lycoris 案例）
└── tests/
    ├── __init__.py
    ├── conftest.py                  # fixtures：tmdb 响应快照、临时媒体目录
    ├── test_config.py
    ├── test_models.py
    ├── test_summarize.py
    ├── test_tmdb.py
    ├── test_planner.py
    ├── test_fsops.py
    └── test_cli.py
```

**职责边界：**
- `config.py`：唯一读取凭证的地方
- `tmdb.py`：唯一调用网络的地方；返回原始 dict
- `summarize.py`：唯一把原始 dict 压成摘要的地方（overview 不外泄）
- `planner.py`：文件名解析 + 计划构建，纯函数易测
- `fsops.py`：唯一触碰文件系统的地方
- `cli.py`：编排上述模块，薄层

---

## Task 1: 项目脚手架与配置读取

**Files:**
- Create: `skills/melodyi-filebot/pyproject.toml`
- Create: `skills/melodyi-filebot/.env.example`
- Create: `skills/melodyi-filebot/melodyi_filebot/__init__.py`
- Create: `skills/melodyi-filebot/melodyi_filebot/__main__.py`
- Create: `skills/melodyi-filebot/melodyi_filebot/config.py`
- Create: `skills/melodyi-filebot/tests/__init__.py`
- Create: `skills/melodyi-filebot/tests/conftest.py`
- Create: `skills/melodyi-filebot/tests/test_config.py`

- [ ] **Step 1: 写 pyproject.toml**

```toml
[project]
name = "melodyi-filebot"
version = "0.1.0"
description = "基于 TMDB 的影视批量重命名与目录整理工具"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "pydantic>=2.0",
    "httpx>=0.25",
    "tmdbsimple>=2.7",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]

[project.scripts]
melodyi-filebot = "melodyi_filebot.cli:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["melodyi_filebot"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 写 .env.example**

```
# TMDB API Key, 从 https://www.themoviedb.org/settings/api 获取
TMDB_API_KEY=your_tmdb_api_key_here
```

- [ ] **Step 3: 写 __init__.py**

```python
"""melodyi-filebot: 基于 TMDB 的影视批量重命名与目录整理工具"""

__version__ = "0.1.0"
```

- [ ] **Step 4: 写 __main__.py**

```python
"""支持 python -m melodyi_filebot 调用"""

from melodyi_filebot.cli import cli

if __name__ == "__main__":
    cli()
```

- [ ] **Step 5: 写 config.py**

```python
"""配置读取

优先级：环境变量 TMDB_API_KEY > ~/.melodyi-filebot/config.yaml 中的 tmdb_api_key
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

CONFIG_PATH = Path.home() / ".melodyi-filebot" / "config.yaml"


def load_tmdb_api_key() -> Optional[str]:
    """读取 TMDB API Key

    Returns:
        API Key 字符串，未配置时返回 None
    """
    env_key = os.environ.get("TMDB_API_KEY")
    if env_key:
        return env_key.strip()

    if CONFIG_PATH.exists():
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        key = data.get("tmdb_api_key")
        if key:
            return str(key).strip()

    return None
```

- [ ] **Step 6: 写 tests/__init__.py（空）**

```python
"""melodyi-filebot 测试包"""
```

- [ ] **Step 7: 写 tests/conftest.py**

```python
"""pytest 公共 fixtures"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def tmdb_show_detail() -> dict:
    """TV.info 响应快照（莉可丽丝，简化）"""
    return {
        "id": 46260,
        "name": "莉可丽丝",
        "original_name": "リコリス・リコイル",
        "first_air_date": "2022-07-02",
        "overview": "一名少女的故事。" * 20,
        "seasons": [
            {
                "season_number": 0,
                "name": "Specials",
                "episode_count": 6,
                "air_date": "2022-09-28",
                "overview": "特别篇",
            },
            {
                "season_number": 1,
                "name": "Season 1",
                "episode_count": 13,
                "air_date": "2022-07-02",
                "overview": "正篇",
            },
        ],
        "episode_groups": {"results": []},
    }


@pytest.fixture
def media_root(tmp_path: Path) -> Path:
    """临时媒体目录，含一个剧集文件夹与若干视频文件"""
    show_dir = tmp_path / "[组] 莉可丽丝 Lycoris Recoil S01"
    show_dir.mkdir()
    (show_dir / "莉可丽丝 S01E01.mkv").write_bytes(b"x")
    (show_dir / "莉可丽丝 S01E02.mkv").write_bytes(b"x")
    return tmp_path
```

- [ ] **Step 8: 写 tests/test_config.py**

```python
"""config 读取测试"""

import os
from unittest.mock import patch

from melodyi_filebot import config


class TestLoadTmdbApiKey:
    """load_tmdb_api_key 测试"""

    def test_from_env(self):
        """环境变量优先"""
        with patch.dict(os.environ, {"TMDB_API_KEY": "env_key_123"}):
            assert config.load_tmdb_api_key() == "env_key_123"

    def test_env_strips_whitespace(self):
        """环境变量去除空白"""
        with patch.dict(os.environ, {"TMDB_API_KEY": "  key  "}):
            assert config.load_tmdb_api_key() == "key"

    def test_env_overrides_config_file(self, tmp_path, monkeypatch):
        """环境变量优先于配置文件"""
        cfg = tmp_path / "config.yaml"
        cfg.write_text("tmdb_api_key: file_key\n", encoding="utf-8")
        monkeypatch.setattr(config, "CONFIG_PATH", cfg)
        with patch.dict(os.environ, {"TMDB_API_KEY": "env_key"}, clear=False):
            assert config.load_tmdb_api_key() == "env_key"

    def test_from_config_file(self, tmp_path, monkeypatch):
        """配置文件兜底"""
        cfg = tmp_path / "config.yaml"
        cfg.write_text("tmdb_api_key: file_key\n", encoding="utf-8")
        monkeypatch.setattr(config, "CONFIG_PATH", cfg)
        with patch.dict(os.environ, {}, clear=True):
            assert config.load_tmdb_api_key() == "file_key"

    def test_returns_none_when_missing(self, tmp_path, monkeypatch):
        """未配置返回 None"""
        monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "nope.yaml")
        with patch.dict(os.environ, {}, clear=True):
            assert config.load_tmdb_api_key() is None
```

- [ ] **Step 9: 安装并运行测试，验证失败**

Run: `cd skills/melodyi-filebot && pip install -e ".[dev]" && pytest tests/test_config.py -v`
Expected: PASS（config 无外部依赖，应直接通过；若 import 失败则 FAIL）

- [ ] **Step 10: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/pyproject.toml skills/melodyi-filebot/.env.example skills/melodyi-filebot/melodyi_filebot/ skills/melodyi-filebot/tests/
git commit -m "feat(melodyi-filebot): 初始化项目脚手架与配置读取"
```

---

## Task 2: 数据模型

**Files:**
- Create: `skills/melodyi-filebot/melodyi_filebot/models.py`
- Create: `skills/melodyi-filebot/tests/test_models.py`

- [ ] **Step 1: 写 test_models.py**

```python
"""数据模型测试"""

import pytest
from melodyi_filebot.models import (
    CandidateSummary,
    EpisodeBrief,
    EpisodeGroupBrief,
    PlanOperation,
    SeasonSummary,
    ShowSummary,
)


class TestModels:
    """Pydantic 模型基础测试"""

    def test_candidate_summary(self):
        c = CandidateSummary(
            tmdb_id=46260,
            title="莉可丽丝",
            original_title="リコリス・リコイル",
            year=2022,
            overview_length=100,
            media_type="tv",
        )
        assert c.tmdb_id == 46260
        assert c.media_type == "tv"

    def test_show_summary(self):
        s = ShowSummary(
            tmdb_id=46260,
            title="莉可丽丝",
            original_title="リコリス・リコイル",
            year=2022,
            total_seasons=2,
            total_episodes=19,
            overview_available=True,
            overview_length=100,
            seasons=[
                SeasonSummary(
                    season_number=0,
                    name="Specials",
                    episode_count=6,
                    overview_available=True,
                )
            ],
            episode_groups=[],
        )
        assert s.total_seasons == 2
        assert s.seasons[0].season_number == 0

    def test_overview_available_false_when_short(self):
        """overview 长度 <10 视为不可用"""
        s = ShowSummary(
            tmdb_id=1,
            title="t",
            original_title="t",
            year=2020,
            total_seasons=1,
            total_episodes=1,
            overview_available=False,
            overview_length=5,
            seasons=[],
            episode_groups=[],
        )
        assert s.overview_available is False

    def test_episode_brief(self):
        e = EpisodeBrief(episode_number=1, name="第一集", overview_length=120)
        assert e.episode_number == 1
        assert e.overview_available is True

    def test_plan_operation_move(self):
        op = PlanOperation(
            type="move",
            source="/a/x.mkv",
            path="/b/x.mkv",
        )
        assert op.type == "move"

    def test_plan_operation_mkdir(self):
        op = PlanOperation(type="mkdir", path="/b")
        assert op.source is None

    def test_episode_group_brief(self):
        g = EpisodeGroupBrief(id="abc", name="HD Remaster", type=1)
        assert g.id == "abc"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_models.py -v`
Expected: FAIL（`ModuleNotFoundError: melodyi_filebot.models`）

- [ ] **Step 3: 写 models.py**

```python
"""数据模型

进上下文的摘要模型。注意：不包含完整 overview，仅含 overview_available/length 标记。
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CandidateSummary(BaseModel):
    """搜索候选摘要"""

    tmdb_id: int
    title: str
    original_title: str
    year: Optional[int] = None
    overview_length: int = 0
    media_type: str  # "tv" | "movie"


class SeasonSummary(BaseModel):
    """季摘要"""

    season_number: int
    name: str
    episode_count: int
    first_air_date: Optional[str] = None
    last_air_date: Optional[str] = None
    overview_available: bool = False


class EpisodeBrief(BaseModel):
    """集摘要（懒加载）"""

    episode_number: int
    name: str
    air_date: Optional[str] = None
    overview_length: int = 0

    @property
    def overview_available(self) -> bool:
        return self.overview_length >= 10


class EpisodeGroupBrief(BaseModel):
    """剧集组摘要（非标场景1）"""

    id: str
    name: str
    type: int


class ShowSummary(BaseModel):
    """剧摘要"""

    tmdb_id: int
    title: str
    original_title: str
    year: Optional[int] = None
    total_seasons: int = 0
    total_episodes: int = 0
    overview_available: bool = False
    overview_length: int = 0
    seasons: List[SeasonSummary] = Field(default_factory=list)
    episode_groups: List[EpisodeGroupBrief] = Field(default_factory=list)


class PlanOperation(BaseModel):
    """计划中的单步操作"""

    type: str  # "mkdir" | "move"
    path: str
    source: Optional[str] = None


class BuildPlanResult(BaseModel):
    """build-plan 结果"""

    operations: List[PlanOperation]
    spec_applied: str = "standard"
    warnings: List[str] = Field(default_factory=list)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/melodyi_filebot/models.py skills/melodyi-filebot/tests/test_models.py
git commit -m "feat(melodyi-filebot): 添加数据模型"
```

---

## Task 3: 摘要压缩

**Files:**
- Create: `skills/melodyi-filebot/melodyi_filebot/summarize.py`
- Create: `skills/melodyi-filebot/tests/test_summarize.py`

- [ ] **Step 1: 写 test_summarize.py**

```python
"""摘要压缩测试"""

import pytest
from melodyi_filebot import summarize
from melodyi_filebot.models import ShowSummary


class TestSummarize:
    """summarize 模块测试"""

    def test_show_summary_from_detail(self, tmdb_show_detail):
        s = summarize.show_summary_from_detail(tmdb_show_detail)
        assert s.tmdb_id == 46260
        assert s.title == "莉可丽丝"
        assert s.original_title == "リコリス・リコイル"
        assert s.year == 2022
        assert s.overview_available is True
        assert len(s.seasons) == 2
        assert s.seasons[0].season_number == 0
        assert s.seasons[0].episode_count == 6
        assert s.total_episodes == 19  # 6 + 13

    def test_overview_unavailable_when_short(self):
        detail = {
            "id": 1,
            "name": "t",
            "original_name": "t",
            "first_air_date": "2020-01-01",
            "overview": "短",  # 长度 1
            "seasons": [],
            "episode_groups": {"results": []},
        }
        s = summarize.show_summary_from_detail(detail)
        assert s.overview_available is False
        assert s.overview_length == 1

    def test_overview_unavailable_when_empty(self):
        detail = {
            "id": 1,
            "name": "t",
            "original_name": "t",
            "first_air_date": None,
            "overview": "",
            "seasons": [],
            "episode_groups": {"results": []},
        }
        s = summarize.show_summary_from_detail(detail)
        assert s.overview_available is False

    def test_episode_groups_extracted(self):
        detail = {
            "id": 1,
            "name": "t",
            "original_name": "t",
            "first_air_date": "2020-01-01",
            "overview": "x" * 50,
            "seasons": [],
            "episode_groups": {
                "results": [
                    {"id": "abc", "name": "HD Remaster", "type": 1}
                ]
            },
        }
        s = summarize.show_summary_from_detail(detail)
        assert len(s.episode_groups) == 1
        assert s.episode_groups[0].id == "abc"

    def test_candidates_from_search(self):
        search_resp = {
            "results": [
                {
                    "id": 46260,
                    "name": "莉可丽丝",
                    "original_name": "リコリス・リコイル",
                    "first_air_date": "2022-07-02",
                    "overview": "x" * 50,
                    "media_type": "tv",
                }
            ]
        }
        cands = summarize.candidates_from_search(search_resp, media_type="tv")
        assert len(cands) == 1
        assert cands[0].tmdb_id == 46260
        assert cands[0].year == 2022

    def test_candidates_empty(self):
        assert summarize.candidates_from_search({"results": []}, "tv") == []

    def test_year_from_release_date(self):
        assert summarize._year_from_date("2022-07-02") == 2022
        assert summarize._year_from_date(None) is None
        assert summarize._year_from_date("") is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_summarize.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 写 summarize.py**

```python
"""摘要压缩

把 TMDB 原始 dict 压缩成进上下文的摘要模型。
关键：不外泄完整 overview，仅计算 overview_available/length。
overview 长度 <10 视为不可用（触发 Bangumi 补全的阈值，P1+ 使用）。
"""

from __future__ import annotations

from typing import List, Optional

from melodyi_filebot.models import (
    CandidateSummary,
    EpisodeGroupBrief,
    SeasonSummary,
    ShowSummary,
)

OVERVIEW_MIN_LENGTH = 10


def _year_from_date(date_str: Optional[str]) -> Optional[int]:
    """从 YYYY-MM-DD 提取年份"""
    if not date_str or len(date_str) < 4:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return None


def _overview_len(overview: Optional[str]) -> int:
    return len(overview or "")


def _overview_available(overview: Optional[str]) -> bool:
    return _overview_len(overview) >= OVERVIEW_MIN_LENGTH


def show_summary_from_detail(detail: dict) -> ShowSummary:
    """TV.info 响应 → ShowSummary

    Args:
        detail: TMDB TV.info 原始响应（含 seasons、episode_groups）

    Returns:
        ShowSummary 摘要
    """
    seasons_raw = detail.get("seasons", []) or []
    seasons = [
        SeasonSummary(
            season_number=s.get("season_number", 0),
            name=s.get("name", "") or "",
            episode_count=s.get("episode_count", 0) or 0,
            first_air_date=s.get("air_date"),
            last_air_date=s.get("air_date"),
            overview_available=_overview_available(s.get("overview")),
        )
        for s in seasons_raw
    ]
    groups_raw = (detail.get("episode_groups") or {}).get("results", []) or []
    episode_groups = [
        EpisodeGroupBrief(
            id=str(g["id"]),
            name=g.get("name", "") or "",
            type=g.get("type", 0) or 0,
        )
        for g in groups_raw
    ]
    overview = detail.get("overview")
    return ShowSummary(
        tmdb_id=detail.get("id"),
        title=detail.get("name", "") or "",
        original_title=detail.get("original_name", "") or "",
        year=_year_from_date(detail.get("first_air_date")),
        total_seasons=len(seasons),
        total_episodes=sum(s.episode_count for s in seasons),
        overview_available=_overview_available(overview),
        overview_length=_overview_len(overview),
        seasons=seasons,
        episode_groups=episode_groups,
    )


def candidates_from_search(search_resp: dict, media_type: str) -> List[CandidateSummary]:
    """search 响应 → 候选摘要列表

    Args:
        search_resp: TMDB search 响应
        media_type: "tv" | "movie"

    Returns:
        候选摘要列表
    """
    results = search_resp.get("results", []) or []
    date_field = "first_air_date" if media_type == "tv" else "release_date"
    name_field = "name" if media_type == "tv" else "title"
    orig_field = "original_name" if media_type == "tv" else "original_title"
    candidates = []
    for r in results:
        candidates.append(
            CandidateSummary(
                tmdb_id=r.get("id"),
                title=r.get(name_field, "") or "",
                original_title=r.get(orig_field, "") or "",
                year=_year_from_date(r.get(date_field)),
                overview_length=_overview_len(r.get("overview")),
                media_type=media_type,
            )
        )
    return candidates
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_summarize.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/melodyi_filebot/summarize.py skills/melodyi-filebot/tests/test_summarize.py
git commit -m "feat(melodyi-filebot): 添加摘要压缩（不外泄完整 overview）"
```

---

## Task 4: TMDB 搜索封装

**Files:**
- Create: `skills/melodyi-filebot/melodyi_filebot/tmdb.py`
- Create: `skills/melodyi-filebot/tests/test_tmdb.py`（本任务覆盖 search 部分）

- [ ] **Step 1: 写 test_tmdb.py（搜索部分）**

```python
"""TMDB 封装测试（mock 网络调用）"""

from unittest.mock import patch, MagicMock

import pytest

from melodyi_filebot import tmdb


@pytest.fixture(autouse=True)
def _set_key(monkeypatch):
    """所有测试注入 API key"""
    monkeypatch.setattr(tmdb, "_api_key", "test_key")


class TestSearch:
    """search 测试"""

    def test_search_tv_returns_candidates(self):
        mock_search = MagicMock()
        mock_search.tv.return_value = {
            "results": [
                {
                    "id": 46260,
                    "name": "莉可丽丝",
                    "original_name": "リコリス・リコイル",
                    "first_air_date": "2022-07-02",
                    "overview": "x" * 50,
                    "media_type": "tv",
                }
            ]
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.Search", return_value=mock_search):
            cands = tmdb.search("莉可丽丝", media_type="tv", language="zh-CN")
        assert len(cands) == 1
        assert cands[0].tmdb_id == 46260
        mock_search.tv.assert_called_once_with(query="莉可丽丝", language="zh-CN")

    def test_search_movie(self):
        mock_search = MagicMock()
        mock_search.movie.return_value = {"results": []}
        with patch("melodyi_filebot.tmdb.tmdbsimple.Search", return_value=mock_search):
            cands = tmdb.search("某电影", media_type="movie", language="zh-CN")
        assert cands == []
        mock_search.movie.assert_called_once_with(query="某电影", language="zh-CN")

    def test_search_multi(self):
        mock_search = MagicMock()
        mock_search.multi.return_value = {
            "results": [
                {"id": 1, "name": "A", "original_name": "A", "media_type": "tv",
                 "first_air_date": "2020-01-01", "overview": "x" * 50},
                {"id": 2, "title": "B", "original_title": "B", "media_type": "movie",
                 "release_date": "2021-01-01", "overview": "x" * 50},
            ]
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.Search", return_value=mock_search):
            cands = tmdb.search("x", media_type="multi", language="zh-CN")
        assert len(cands) == 2

    def test_search_raises_without_key(self, monkeypatch):
        monkeypatch.setattr(tmdb, "_api_key", None)
        with pytest.raises(RuntimeError, match="TMDB_API_KEY"):
            tmdb.search("x", media_type="tv")
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_tmdb.py::TestSearch -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 写 tmdb.py（search 部分，get_show_summary 先留桩）**

```python
"""TMDB 调用封装

初期通过 import tmdbsimple 调用 TMDB API。后续若用到的 API 很少，可考虑自实现。
所有方法返回原始 dict 或摘要模型，完整 overview 不外泄给 agent。
"""

from __future__ import annotations

import logging
from typing import List, Optional

import tmdbsimple as tmdbsimple

from melodyi_filebot import config
from melodyi_filebot.models import CandidateSummary, ShowSummary, EpisodeBrief
from melodyi_filebot import summarize

logger = logging.getLogger(__name__)

_api_key: Optional[str] = None


def _ensure_key() -> str:
    """确保 API key 已加载并设置到 tmdbsimple

    Returns:
        API key

    Raises:
        RuntimeError: 未配置 API key
    """
    global _api_key
    if _api_key is None:
        _api_key = config.load_tmdb_api_key()
    if not _api_key:
        raise RuntimeError(
            "未配置 TMDB_API_KEY。请设置环境变量或在 ~/.melodyi-filebot/config.yaml 中配置 tmdb_api_key。"
        )
    tmdbsimple.API_KEY = _api_key
    return _api_key


def search(
    query: str,
    media_type: str = "tv",
    language: str = "zh-CN",
    year: Optional[int] = None,
) -> List[CandidateSummary]:
    """关键字搜索 TMDB

    Args:
        query: 搜索关键字
        media_type: "tv" | "movie" | "multi"
        language: 语言（默认 zh-CN）
        year: 年份过滤（仅 tv/movie）

    Returns:
        候选摘要列表
    """
    _ensure_key()
    logger.info("TMDB 搜索开始: query=%r, type=%s, lang=%s", query, media_type, language)
    s = tmdbsimple.Search()
    kwargs = {"query": query, "language": language}
    if year is not None and media_type == "tv":
        kwargs["first_air_date_year"] = year
    elif year is not None and media_type == "movie":
        kwargs["year"] = year

    if media_type == "tv":
        resp = s.tv(**kwargs)
    elif media_type == "movie":
        resp = s.movie(**kwargs)
    elif media_type == "multi":
        resp = s.multi(**kwargs)
    else:
        raise ValueError(f"不支持的 media_type: {media_type}")

    cands = summarize.candidates_from_search(resp, media_type=media_type)
    logger.info("TMDB 搜索完成: 命中 %d 条", len(cands))
    return cands


def get_show_summary(tmdb_id: int, language: str = "zh-CN") -> ShowSummary:
    """获取剧摘要

    Args:
        tmdb_id: TMDB 剧 ID
        language: 语言

    Returns:
        ShowSummary 摘要
    """
    _ensure_key()
    logger.info("获取剧详情开始: id=%s, lang=%s", tmdb_id, language)
    tv = tmdbsimple.TV(id=tmdb_id)
    detail = tv.info(append_to_response="episode_groups", language=language)
    summary = summarize.show_summary_from_detail(detail)
    logger.info("获取剧详情完成: id=%s, 季数=%d", tmdb_id, summary.total_seasons)
    return summary


def get_season_episodes(
    tmdb_id: int, season_number: int, language: str = "zh-CN"
) -> List[EpisodeBrief]:
    """获取某季集摘要（懒加载用）

    Args:
        tmdb_id: TMDB 剧 ID
        season_number: 季号
        language: 语言

    Returns:
        集摘要列表
    """
    _ensure_key()
    logger.info("获取季集列表开始: id=%s, season=%s", tmdb_id, season_number)
    seasons = tmdbsimple.TV_Seasons(tv_id=tmdb_id, season_number=season_number)
    detail = seasons.info(language=language)
    eps = detail.get("episodes", []) or []
    briefs = [
        EpisodeBrief(
            episode_number=e.get("episode_number", 0),
            name=e.get("name", "") or "",
            air_date=e.get("air_date"),
            overview_length=len(e.get("overview") or ""),
        )
        for e in eps
    ]
    logger.info("获取季集列表完成: id=%s, season=%s, 集数=%d", tmdb_id, season_number, len(briefs))
    return briefs
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_tmdb.py::TestSearch -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/melodyi_filebot/tmdb.py skills/melodyi-filebot/tests/test_tmdb.py
git commit -m "feat(melodyi-filebot): 添加 TMDB 搜索与详情封装"
```

---

## Task 5: TMDB 详情与集列表测试

**Files:**
- Modify: `skills/melodyi-filebot/tests/test_tmdb.py`（追加详情与集列表测试）

- [ ] **Step 1: 追加 test_tmdb.py 的详情与集列表测试**

在 `tests/test_tmdb.py` 末尾追加：

```python
class TestShowSummary:
    """get_show_summary 测试"""

    def test_get_show_summary(self, tmdb_show_detail):
        mock_tv = MagicMock()
        mock_tv.info.return_value = tmdb_show_detail
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV", return_value=mock_tv):
            s = tmdb.get_show_summary(46260, language="zh-CN")
        assert s.tmdb_id == 46260
        assert s.total_seasons == 2
        assert s.total_episodes == 19
        mock_tv.info.assert_called_once()
        # 验证 append_to_response
        _, kwargs = mock_tv.info.call_args
        assert kwargs.get("append_to_response") == "episode_groups"

    def test_get_show_summary_uses_language(self, tmdb_show_detail):
        mock_tv = MagicMock()
        mock_tv.info.return_value = tmdb_show_detail
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV", return_value=mock_tv):
            tmdb.get_show_summary(46260, language="ja-JP")
        _, kwargs = mock_tv.info.call_args
        assert kwargs.get("language") == "ja-JP"


class TestSeasonEpisodes:
    """get_season_episodes 测试"""

    def test_get_season_episodes(self):
        mock_seasons = MagicMock()
        mock_seasons.info.return_value = {
            "episodes": [
                {"episode_number": 1, "name": "第一集", "air_date": "2022-07-02", "overview": "x" * 50},
                {"episode_number": 2, "name": "第二集", "air_date": "2022-07-09", "overview": "x" * 50},
            ]
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV_Seasons", return_value=mock_seasons):
            eps = tmdb.get_season_episodes(46260, 1, language="zh-CN")
        assert len(eps) == 2
        assert eps[0].episode_number == 1
        assert eps[0].overview_available is True

    def test_get_season_episodes_empty(self):
        mock_seasons = MagicMock()
        mock_seasons.info.return_value = {"episodes": []}
        with patch("melodyi_filebot.tmdb.tmdbsimple.TV_Seasons", return_value=mock_seasons):
            eps = tmdb.get_season_episodes(46260, 1)
        assert eps == []
```

- [ ] **Step 2: 运行测试验证通过（get_show_summary/get_season_episodes 已在 Task4 实现）**

Run: `pytest tests/test_tmdb.py -v`
Expected: PASS（TestShowSummary 与 TestSeasonEpisodes 应通过）

- [ ] **Step 3: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/tests/test_tmdb.py
git commit -m "test(melodyi-filebot): 补充 TMDB 详情与集列表测试"
```

---

## Task 6: 文件名 S/E 解析

**Files:**
- Create: `skills/melodyi-filebot/melodyi_filebot/planner.py`
- Create: `skills/melodyi-filebot/tests/test_planner.py`（本任务覆盖解析部分）

- [ ] **Step 1: 写 test_planner.py（解析部分）**

```python
"""planner 测试"""

import pytest

from melodyi_filebot.planner import ParsedFile, parse_filename


class TestParseFilename:
    """文件名 S/E 解析测试"""

    def test_standard_sxxexx(self):
        p = parse_filename("Gundam.Build.Fighters.2013.S01E01.2160p.WEB-DL.mp4")
        assert p.season == 1
        assert p.episode == 1
        assert p.episode_end is None
        assert p.part is None
        assert p.ext == ".mp4"

    def test_chinese_title_sxxexx(self):
        p = parse_filename("莉可丽丝 S01E01.mkv")
        assert p.season == 1
        assert p.episode == 1

    def test_multi_episode_range(self):
        p = parse_filename("Series A S01E01-E02.mkv")
        assert p.season == 1
        assert p.episode == 1
        assert p.episode_end == 2

    def test_part_split(self):
        p = parse_filename("Series A S01E01-part-1.mkv")
        assert p.season == 1
        assert p.episode == 1
        assert p.part == 1

    def test_part_split_dot(self):
        p = parse_filename("Series A S01E01.part2.mkv")
        assert p.season == 1
        assert p.episode == 1
        assert p.part == 2

    def test_bracket_episode_number(self):
        """方括号单集编号 [10]"""
        p = parse_filename("[VCB-Studio] Amagami SS+ Plus [10][Ma10p_1080p].mkv")
        assert p.season is None  # 无季信息
        assert p.episode == 10

    def test_returns_none_for_unknown(self):
        p = parse_filename("random video file.mp4")
        assert p.season is None
        assert p.episode is None

    def test_stem_extraction(self):
        p = parse_filename("Show S01E01.mkv")
        assert "Show" in p.stem
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_planner.py::TestParseFilename -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 写 planner.py（解析部分，build_plan 留到 Task7）**

```python
"""文件名解析与计划构建

解析常见 release 命名中的季/集信息，构建重命名与目录整理计划。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from melodyi_filebot.models import BuildPlanResult, PlanOperation, ShowSummary

logger = logging.getLogger(__name__)

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".ts", ".m4v", ".wmv", ".flv"}

# S01E01 或 S01E01E02
_SXXEXX = re.compile(r"[Ss](\d{1,2})\s?[Ee](\d{1,3})(?:\s?[-]?\s?[Ee](\d{1,3}))?")
# S01E01-E02 范围
_SXXEXX_RANGE = re.compile(r"[Ss](\d{1,2})\s?[Ee](\d{1,3})\s?-\s?[Ee](\d{1,3})")
# 单独 E01
_EXX = re.compile(r"(?<![A-Za-z0-9])[Ee](\d{1,3})(?![A-Za-z0-9])")
# part-N / partN / .partN.
_PART = re.compile(r"[._-]part[._-]?(\d{1,2})", re.IGNORECASE)
# 方括号单集编号 [10]
_BRACKET_EP = re.compile(r"\[(\d{1,3})\]")


class ParsedFile(BaseModel):
    """解析后的文件信息"""

    path: str
    stem: str
    ext: str
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_end: Optional[int] = None  # 多集范围终点
    part: Optional[int] = None  # 分段编号


def parse_filename(filename: str) -> ParsedFile:
    """从文件名解析季/集信息

    支持常见格式：
        - Series S01E01.mkv
        - Series S01E01-E02.mkv（范围）
        - Series S01E01-part-1.mkv（分段）
        - [Studio] Title [10].mkv（方括号集号）

    Args:
        filename: 文件名（含扩展名）

    Returns:
        ParsedFile，未识别字段为 None
    """
    p = Path(filename)
    stem = p.stem
    ext = p.suffix

    season: Optional[int] = None
    episode: Optional[int] = None
    episode_end: Optional[int] = None

    m_range = _SXXEXX_RANGE.search(stem)
    m_single = _SXXEXX.search(stem)
    if m_range:
        season = int(m_range.group(1))
        episode = int(m_range.group(2))
        episode_end = int(m_range.group(3))
    elif m_single:
        season = int(m_single.group(1))
        episode = int(m_single.group(2))
        if m_single.group(3):
            episode_end = int(m_single.group(3))
    else:
        # 方括号集号（无季）
        m_bracket = _BRACKET_EP.search(stem)
        if m_bracket:
            episode = int(m_bracket.group(1))
        else:
            m_exx = _EXX.search(stem)
            if m_exx:
                episode = int(m_exx.group(1))

    part_m = _PART.search(stem)
    part = int(part_m.group(1)) if part_m else None

    return ParsedFile(
        path=str(filename),
        stem=stem,
        ext=ext,
        season=season,
        episode=episode,
        episode_end=episode_end,
        part=part,
    )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_planner.py::TestParseFilename -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/melodyi_filebot/planner.py skills/melodyi-filebot/tests/test_planner.py
git commit -m "feat(melodyi-filebot): 添加文件名 S/E 解析"
```

---

## Task 7: 构建重命名计划（剧集）

**Files:**
- Modify: `skills/melodyi-filebot/melodyi_filebot/planner.py`（追加 build_plan_tv）
- Modify: `skills/melodyi-filebot/tests/test_planner.py`（追加 build_plan_tv 测试）

- [ ] **Step 1: 追加 test_planner.py 的 build_plan_tv 测试**

在 `tests/test_planner.py` 末尾追加：

```python
from melodyi_filebot.models import ShowSummary, SeasonSummary
from melodyi_filebot.planner import build_plan_tv


def _show_summary() -> ShowSummary:
    return ShowSummary(
        tmdb_id=46260,
        title="莉可丽丝",
        original_title="リコリス・リコイル",
        year=2022,
        total_seasons=1,
        total_episodes=13,
        overview_available=True,
        overview_length=100,
        seasons=[
            SeasonSummary(season_number=0, name="Specials", episode_count=6),
            SeasonSummary(season_number=1, name="Season 1", episode_count=13),
        ],
        episode_groups=[],
    )


class TestBuildPlanTv:
    """build_plan_tv 测试"""

    def test_standard_season1(self, tmp_path):
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        f1 = show_dir / "莉可丽丝 S01E01.mkv"
        f2 = show_dir / "莉可丽丝 S01E02.mkv"
        f1.write_bytes(b"x")
        f2.write_bytes(b"x")

        result = build_plan_tv(
            files=[str(f1), str(f2)],
            show=_show_summary(),
            dest_root=str(tmp_path / "dest"),
            language="zh-CN",
        )
        # 期望：mkdir 剧集目录 + mkdir Season 01 + 2 个 move
        assert any(op.type == "mkdir" and "[tmdbid-46260]" in op.path for op in result.operations)
        assert any(op.type == "mkdir" and op.path.endswith("Season 01") for op in result.operations)
        moves = [op for op in result.operations if op.type == "move"]
        assert len(moves) == 2
        assert all("S01E0" in op.path for op in moves)
        assert result.spec_applied == "standard"
        assert result.warnings == []

    def test_specials_season0(self, tmp_path):
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        f1 = show_dir / "特别篇 S00E01.mkv"
        f1.write_bytes(b"x")

        result = build_plan_tv(
            files=[str(f1)],
            show=_show_summary(),
            dest_root=str(tmp_path / "dest"),
            language="zh-CN",
        )
        assert any(op.type == "mkdir" and op.path.endswith("Season 00") for op in result.operations)
        moves = [op for op in result.operations if op.type == "move"]
        assert len(moves) == 1
        assert "S00E01" in moves[0].path

    def test_unparseable_file_warning(self, tmp_path):
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        f1 = show_dir / "random video.mkv"  # 无 S/E
        f1.write_bytes(b"x")

        result = build_plan_tv(
            files=[str(f1)],
            show=_show_summary(),
            dest_root=str(tmp_path / "dest"),
            language="zh-CN",
        )
        assert any("无法解析" in w for w in result.warnings)
        # 不可解析文件不产生 move
        assert all(op.type != "move" for op in result.operations)

    def test_invalid_char_sanitized(self, tmp_path):
        """标题含非法字符需清理"""
        show = ShowSummary(
            tmdb_id=1, title="剧:名", original_title="x", year=2020,
            total_seasons=1, total_episodes=1, seasons=[
                SeasonSummary(season_number=1, name="S1", episode_count=1)
            ],
        )
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        f1 = show_dir / "剧:名 S01E01.mkv"
        f1.write_bytes(b"x")
        result = build_plan_tv(
            files=[str(f1)], show=show, dest_root=str(tmp_path / "dest"), language="zh-CN"
        )
        mkdirs = [op.path for op in result.operations if op.type == "mkdir"]
        assert all(":" not in p for p in mkdirs)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_planner.py::TestBuildPlanTv -v`
Expected: FAIL（`build_plan_tv` 未定义）

- [ ] **Step 3: 在 planner.py 追加 build_plan_tv**

在 `planner.py` 末尾追加：

```python
_INVALID_CHARS = '<>:"/\\|?*'


def _sanitize(name: str) -> str:
    """清理 Jellyfin 不允许的文件名字符"""
    for ch in _INVALID_CHARS:
        name = name.replace(ch, "_")
    return name.strip().rstrip(".")


def _show_folder(show: ShowSummary) -> str:
    """剧文件夹名：剧名 (年) [tmdbid-xxx]"""
    year = f" ({show.year})" if show.year else ""
    return _sanitize(f"{show.title}{year} [tmdbid-{show.tmdb_id}]")


def _season_folder(season_number: int) -> str:
    """季文件夹名：Season 01（补零到 2 位）"""
    return f"Season {season_number:02d}"


def _episode_filename(
    show: ShowSummary, season: int, episode: int, episode_end: Optional[int], part: Optional[int], ext: str
) -> str:
    """集文件名：剧名 (年) S01E01[-E02][-part1].ext"""
    year = f" ({show.year})" if show.year else ""
    base = f"{_sanitize(show.title)}{year} S{season:02d}E{episode:02d}"
    if episode_end:
        base += f"-E{episode_end:02d}"
    if part:
        base += f"-part{part}"
    return base + ext


def build_plan_tv(
    files: List[str],
    show: ShowSummary,
    dest_root: str,
    language: str = "zh-CN",
) -> BuildPlanResult:
    """构建剧集重命名与目录整理计划（标准流程，P0 不含 NFO）

    Args:
        files: 源视频文件绝对路径列表
        show: TMDB 剧摘要
        dest_root: 目标媒体根目录
        language: 语言

    Returns:
        BuildPlanResult，含 mkdir/move 操作与警告
    """
    logger.info("构建剧集计划开始: show=%s, 文件数=%d", show.title, len(files))
    operations: List[PlanOperation] = []
    warnings: List[str] = []

    show_folder = _show_folder(show)
    show_dir = f"{dest_root}/{show_folder}"
    operations.append(PlanOperation(type="mkdir", path=show_dir))

    created_seasons: set = set()
    for f in files:
        parsed = parse_filename(f)
        if parsed.episode is None:
            warnings.append(f"无法解析集号，跳过: {f}")
            logger.warning("无法解析集号: %s", f)
            continue
        season = parsed.season if parsed.season is not None else 1
        season_dir = f"{show_dir}/{_season_folder(season)}"
        if season not in created_seasons:
            operations.append(PlanOperation(type="mkdir", path=season_dir))
            created_seasons.add(season)

        target_name = _episode_filename(
            show, season, parsed.episode, parsed.episode_end, parsed.part, parsed.ext
        )
        target = f"{season_dir}/{target_name}"
        operations.append(PlanOperation(type="move", source=f, path=target))

    logger.info(
        "构建剧集计划完成: show=%s, 操作数=%d, 警告数=%d",
        show.title, len(operations), len(warnings),
    )
    return BuildPlanResult(operations=operations, spec_applied="standard", warnings=warnings)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_planner.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/melodyi_filebot/planner.py skills/melodyi-filebot/tests/test_planner.py
git commit -m "feat(melodyi-filebot): 构建剧集重命名计划（标准流程）"
```

---

## Task 8: 构建重命名计划（电影）与扫描

**Files:**
- Modify: `skills/melodyi-filebot/melodyi_filebot/planner.py`（追加 build_plan_movie）
- Modify: `skills/melodyi-filebot/tests/test_planner.py`（追加电影测试）

- [ ] **Step 1: 追加电影测试**

在 `tests/test_planner.py` 末尾追加：

```python
from melodyi_filebot.models import CandidateSummary
from melodyi_filebot.planner import build_plan_movie


class TestBuildPlanMovie:
    """build_plan_movie 测试"""

    def test_standard_movie(self, tmp_path):
        src = tmp_path / "源"
        src.mkdir()
        f = src / "某电影.2020.1080p.mkv"
        f.write_bytes(b"x")
        cand = CandidateSummary(
            tmdb_id=123, title="某电影", original_title="Mov", year=2020,
            overview_length=50, media_type="movie",
        )
        result = build_plan_movie(
            files=[str(f)], movie=cand, dest_root=str(tmp_path / "dest")
        )
        mkdirs = [op.path for op in result.operations if op.type == "mkdir"]
        assert any("某电影 (2020) [tmdbid-123]" in p for p in mkdirs)
        moves = [op for op in result.operations if op.type == "move"]
        assert len(moves) == 1
        assert "某电影 (2020).mkv" in moves[0].path
```

- [ ] **Step 2: 运行验证失败**

Run: `pytest tests/test_planner.py::TestBuildPlanMovie -v`
Expected: FAIL（`build_plan_movie` 未定义）

- [ ] **Step 3: 在 planner.py 追加 build_plan_movie**

在 `planner.py` 末尾追加：

```python
def build_plan_movie(
    files: List[str], movie: CandidateSummary, dest_root: str
) -> BuildPlanResult:
    """构建电影重命名计划（P0 不含 NFO）

    Args:
        files: 源视频文件路径列表（取第一个为正片，其余作 warning）
        movie: TMDB 电影候选摘要
        dest_root: 目标媒体根目录

    Returns:
        BuildPlanResult
    """
    logger.info("构建电影计划开始: movie=%s, 文件数=%d", movie.title, len(files))
    operations: List[PlanOperation] = []
    warnings: List[str] = []

    year = f" ({movie.year})" if movie.year else ""
    folder = _sanitize(f"{movie.title}{year} [tmdbid-{movie.tmdb_id}]")
    movie_dir = f"{dest_root}/{folder}"
    operations.append(PlanOperation(type="mkdir", path=movie_dir))

    target_name = _sanitize(f"{movie.title}{year}") + (Path(files[0]).suffix if files else ".mkv")
    target = f"{movie_dir}/{target_name}"
    operations.append(PlanOperation(type="move", source=files[0], path=target))
    for extra in files[1:]:
        warnings.append(f"电影存在多个视频文件，已忽略: {extra}")
        logger.warning("电影多文件忽略: %s", extra)

    logger.info("构建电影计划完成: movie=%s", movie.title)
    return BuildPlanResult(operations=operations, spec_applied="standard", warnings=warnings)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_planner.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/melodyi_filebot/planner.py skills/melodyi-filebot/tests/test_planner.py
git commit -m "feat(melodyi-filebot): 构建电影重命名计划"
```

---

## Task 9: 目录扫描

**Files:**
- Create: `skills/melodyi-filebot/melodyi_filebot/fsops.py`
- Create: `skills/melodyi-filebot/tests/test_fsops.py`（本任务覆盖扫描）

- [ ] **Step 1: 写 test_fsops.py（扫描部分）**

```python
"""fsops 测试"""

from pathlib import Path

import pytest

from melodyi_filebot import fsops
from melodyi_filebot.planner import VIDEO_EXTS


class TestScan:
    """scan_video_files 测试"""

    def test_scan_finds_videos(self, tmp_path):
        (tmp_path / "a.mkv").write_bytes(b"x")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.mp4").write_bytes(b"x")
        (tmp_path / "c.txt").write_text("nope")
        files = fsops.scan_video_files(str(tmp_path))
        assert len(files) == 2
        assert all(Path(f).suffix in VIDEO_EXTS for f in files)

    def test_scan_recursive(self, tmp_path):
        (tmp_path / "s1").mkdir()
        (tmp_path / "s1" / "s2").mkdir()
        (tmp_path / "s1" / "s2" / "deep.mkv").write_bytes(b"x")
        files = fsops.scan_video_files(str(tmp_path))
        assert len(files) == 1

    def test_scan_empty(self, tmp_path):
        assert fsops.scan_video_files(str(tmp_path)) == []

    def test_scan_missing_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            fsops.scan_video_files(str(tmp_path / "nope"))
```

- [ ] **Step 2: 运行验证失败**

Run: `pytest tests/test_fsops.py::TestScan -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 写 fsops.py（扫描部分，execute/undo 留到 Task10/11）**

```python
"""文件系统操作

扫描、执行计划、事务日志、回滚。唯一触碰文件系统的模块。
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import List

from melodyi_filebot.models import BuildPlanResult, PlanOperation
from melodyi_filebot.planner import VIDEO_EXTS

logger = logging.getLogger(__name__)


def scan_video_files(root: str) -> List[str]:
    """递归扫描目录下的视频文件

    Args:
        root: 扫描根目录

    Returns:
        视频文件绝对路径列表

    Raises:
        FileNotFoundError: 目录不存在
    """
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"目录不存在: {root}")
    files = [
        str(p)
        for p in root_path.rglob("*")
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    ]
    logger.info("扫描完成: root=%s, 视频文件数=%d", root, len(files))
    return files
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_fsops.py::TestScan -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/melodyi_filebot/fsops.py skills/melodyi-filebot/tests/test_fsops.py
git commit -m "feat(melodyi-filebot): 添加目录扫描"
```

---

## Task 10: 执行计划与事务日志

**Files:**
- Modify: `skills/melodyi-filebot/melodyi_filebot/fsops.py`（追加 execute_plan + dry_run 校验）
- Modify: `skills/melodyi-filebot/tests/test_fsops.py`（追加 execute 测试）

- [ ] **Step 1: 追加 execute 测试**

在 `tests/test_fsops.py` 末尾追加：

```python
from melodyi_filebot.models import BuildPlanResult, PlanOperation


class TestExecutePlan:
    """execute_plan 测试"""

    def test_dry_run_no_changes(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        dest = tmp_path / "dest"
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="mkdir", path=str(dest / "Show")),
                PlanOperation(type="move", source=str(f), path=str(dest / "Show" / "a.mkv")),
            ]
        )
        snapshot = fsops.execute_plan(plan, dry_run=True)
        # dry-run 不应改动文件系统
        assert f.exists()
        assert not (dest / "Show").exists()
        assert snapshot is None

    def test_execute_moves_file(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        dest = tmp_path / "dest" / "Show"
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="mkdir", path=str(dest)),
                PlanOperation(type="move", source=str(f), path=str(dest / "a.mkv")),
            ]
        )
        snapshot = fsops.execute_plan(plan, dry_run=False)
        assert not f.exists()
        assert (dest / "a.mkv").exists()
        assert snapshot is not None
        assert len(snapshot["operations"]) == 2

    def test_execute_writes_snapshot_file(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        dest = tmp_path / "dest" / "Show"
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="mkdir", path=str(dest)),
                PlanOperation(type="move", source=str(f), path=str(dest / "a.mkv")),
            ]
        )
        snapshot = fsops.execute_plan(plan, dry_run=False, snapshot_path=str(tmp_path / "snap.json"))
        assert (tmp_path / "snap.json").exists()
        data = json.loads((tmp_path / "snap.json").read_text(encoding="utf-8"))
        assert "operations" in data

    def test_dry_run_detects_conflict(self, tmp_path):
        """目标已存在文件时 dry-run 报冲突"""
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        dest = tmp_path / "dest" / "Show"
        dest.mkdir(parents=True)
        (dest / "a.mkv").write_bytes(b"existing")
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="move", source=str(f), path=str(dest / "a.mkv")),
            ]
        )
        import pytest as _pytest
        with _pytest.raises(FileExistsError):
            fsops.execute_plan(plan, dry_run=True)

    def test_dry_run_detects_missing_source(self, tmp_path):
        dest = tmp_path / "dest" / "Show"
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="move", source=str(tmp_path / "ghost.mkv"), path=str(dest / "a.mkv")),
            ]
        )
        import pytest as _pytest
        with _pytest.raises(FileNotFoundError):
            fsops.execute_plan(plan, dry_run=True)
```

并在 `tests/test_fsops.py` 顶部补 import：

```python
import json
```

- [ ] **Step 2: 运行验证失败**

Run: `pytest tests/test_fsops.py::TestExecutePlan -v`
Expected: FAIL（`execute_plan` 未定义）

- [ ] **Step 3: 在 fsops.py 追加 dry_run 校验与 execute_plan**

在 `fsops.py` 末尾追加：

```python
def _validate(plan: BuildPlanResult) -> None:
    """dry-run 前置校验：源存在、目标无冲突

    Raises:
        FileNotFoundError: 源文件不存在
        FileExistsError: 目标已存在
    """
    move_targets: set = set()
    for op in plan.operations:
        if op.type == "move":
            if not Path(op.source).exists():
                raise FileNotFoundError(f"源文件不存在: {op.source}")
            if op.path in move_targets:
                raise FileExistsError(f"目标路径重复: {op.path}")
            move_targets.add(op.path)
            if Path(op.path).exists():
                raise FileExistsError(f"目标已存在: {op.path}")


def execute_plan(
    plan: BuildPlanResult,
    dry_run: bool = True,
    snapshot_path: str = None,
) -> dict:
    """执行计划

    Args:
        plan: 构建好的计划
        dry_run: True 只校验不执行；False 真正执行
        snapshot_path: 事务日志保存路径（dry_run=False 时写入）

    Returns:
        dry_run=True 返回 None；dry_run=False 返回 snapshot dict
    """
    _validate(plan)
    if dry_run:
        logger.info("dry-run 校验通过，未执行任何操作")
        return None

    logger.info("执行计划开始: 操作数=%d", len(plan.operations))
    log: List[dict] = []
    for op in plan.operations:
        if op.type == "mkdir":
            Path(op.path).mkdir(parents=True, exist_ok=True)
            log.append({"type": "mkdir", "path": op.path, "inverse": None})
            logger.info("创建目录: %s", op.path)
        elif op.type == "move":
            Path(op.path).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(op.source, op.path)
            log.append({"type": "move", "path": op.path, "source": op.source, "inverse": "move_back"})
            logger.info("移动文件: %s -> %s", op.source, op.path)

    snapshot = {"operations": list(reversed(log))}
    if snapshot_path:
        Path(snapshot_path).write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("事务日志已写入: %s", snapshot_path)
    logger.info("执行计划完成")
    return snapshot
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_fsops.py::TestExecutePlan -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/melodyi_filebot/fsops.py skills/melodyi-filebot/tests/test_fsops.py
git commit -m "feat(melodyi-filebot): 执行计划与事务日志"
```

---

## Task 11: 回滚

**Files:**
- Modify: `skills/melodyi-filebot/melodyi_filebot/fsops.py`（追加 undo）
- Modify: `skills/melodyi-filebot/tests/test_fsops.py`（追加 undo 测试）

- [ ] **Step 1: 追加 undo 测试**

在 `tests/test_fsops.py` 末尾追加：

```python
class TestUndo:
    """undo 测试"""

    def test_undo_restores_original(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        dest = tmp_path / "dest" / "Show"
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="mkdir", path=str(dest)),
                PlanOperation(type="move", source=str(f), path=str(dest / "a.mkv")),
            ]
        )
        snapshot = fsops.execute_plan(plan, dry_run=False, snapshot_path=str(tmp_path / "snap.json"))
        assert not f.exists()
        fsops.undo(snapshot)
        # 回滚后源文件恢复，目标目录被清理（move 逆操作）
        assert f.exists()
        assert not (dest / "a.mkv").exists()

    def test_undo_from_file(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        dest = tmp_path / "dest" / "Show"
        plan = BuildPlanResult(
            operations=[
                PlanOperation(type="mkdir", path=str(dest)),
                PlanOperation(type="move", source=str(f), path=str(dest / "a.mkv")),
            ]
        )
        snap_path = str(tmp_path / "snap.json")
        fsops.execute_plan(plan, dry_run=False, snapshot_path=snap_path)
        fsops.undo_from_file(snap_path)
        assert f.exists()
```

- [ ] **Step 2: 运行验证失败**

Run: `pytest tests/test_fsops.py::TestUndo -v`
Expected: FAIL（`undo`/`undo_from_file` 未定义）

- [ ] **Step 3: 在 fsops.py 追加 undo**

在 `fsops.py` 末尾追加：

```python
def undo(snapshot: dict) -> None:
    """按事务日志逆序回放逆操作

    Args:
        snapshot: execute_plan 返回的事务日志 dict
    """
    ops = snapshot.get("operations", [])
    logger.info("回滚开始: 逆操作数=%d", len(ops))
    for op in ops:
        if op["type"] == "move":
            # 逆操作：把目标移回源
            shutil.move(op["path"], op["source"])
            logger.info("回滚移动: %s -> %s", op["path"], op["source"])
        elif op["type"] == "mkdir":
            # 仅当目录为空时删除
            p = Path(op["path"])
            try:
                p.rmdir()
                logger.info("回滚删除目录: %s", op["path"])
            except OSError:
                logger.info("目录非空，保留: %s", op["path"])
    logger.info("回滚完成")


def undo_from_file(snapshot_path: str) -> None:
    """从事务日志文件回滚

    Args:
        snapshot_path: 事务日志文件路径
    """
    data = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    undo(data)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_fsops.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/melodyi_filebot/fsops.py skills/melodyi-filebot/tests/test_fsops.py
git commit -m "feat(melodyi-filebot): 事务日志回滚"
```

---

## Task 12: CLI（search / fetch-summary）

**Files:**
- Create: `skills/melodyi-filebot/melodyi_filebot/cli.py`
- Create: `skills/melodyi-filebot/tests/test_cli.py`（本任务覆盖 search/fetch-summary）

- [ ] **Step 1: 写 test_cli.py（search/fetch-summary 部分）**

```python
"""CLI 测试"""

import json
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from melodyi_filebot.cli import cli


class TestCliSearch:
    """search 子命令测试"""

    def test_search_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "query" in result.output

    def test_search_tv(self):
        from melodyi_filebot.models import CandidateSummary
        cands = [CandidateSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス",
            year=2022, overview_length=50, media_type="tv",
        )]
        with patch("melodyi_filebot.cli.tmdb.search", return_value=cands):
            runner = CliRunner()
            result = runner.invoke(cli, ["search", "莉可丽丝", "--type", "tv"])
        assert result.exit_code == 0
        assert "莉可丽丝" in result.output

    def test_search_no_results(self):
        with patch("melodyi_filebot.cli.tmdb.search", return_value=[]):
            runner = CliRunner()
            result = runner.invoke(cli, ["search", "不存在的剧"])
        assert result.exit_code == 0
        assert "未找到" in result.output or "0" in result.output


class TestCliFetchSummary:
    """fetch-summary 子命令测试"""

    def test_fetch_summary(self, tmdb_show_detail):
        from melodyi_filebot.models import ShowSummary, SeasonSummary
        s = ShowSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス",
            year=2022, total_seasons=2, total_episodes=19,
            overview_available=True, overview_length=100,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=13)],
            episode_groups=[],
        )
        with patch("melodyi_filebot.cli.tmdb.get_show_summary", return_value=s):
            runner = CliRunner()
            result = runner.invoke(cli, ["fetch-summary", "46260"])
        assert result.exit_code == 0
        assert "莉可丽丝" in result.output
        # 不应输出完整 overview 原文（摘要只含 length）
        assert "overview_length" in result.output or "19" in result.output

    def test_fetch_summary_episodes_flag(self, tmdb_show_detail):
        from melodyi_filebot.models import ShowSummary, SeasonSummary, EpisodeBrief
        s = ShowSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス",
            year=2022, total_seasons=1, total_episodes=2,
            overview_available=True, overview_length=100,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=2)],
            episode_groups=[],
        )
        eps = [EpisodeBrief(episode_number=1, name="第一集", overview_length=50)]
        with patch("melodyi_filebot.cli.tmdb.get_show_summary", return_value=s), \
             patch("melodyi_filebot.cli.tmdb.get_season_episodes", return_value=eps):
            runner = CliRunner()
            result = runner.invoke(cli, ["fetch-summary", "46260", "--episodes", "1"])
        assert result.exit_code == 0
        assert "第一集" in result.output
```

- [ ] **Step 2: 运行验证失败**

Run: `pytest tests/test_cli.py::TestCliSearch tests/test_cli.py::TestCliFetchSummary -v`
Expected: FAIL（`cli` 未定义）

- [ ] **Step 3: 写 cli.py（search/fetch-summary，其余命令 Task13 实现）**

```python
"""CLI 命令行入口

子命令：search / fetch-summary / build-plan / execute-plan / undo
"""

from __future__ import annotations

import json
import logging

import click

from melodyi_filebot import __version__, tmdb
from melodyi_filebot.planner import build_plan_tv, build_plan_movie
from melodyi_filebot import fsops

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="melodyi-filebot")
def cli():
    """melodyi-filebot: 基于 TMDB 的影视批量重命名与目录整理工具"""
    pass


@cli.command()
@click.argument("query")
@click.option("--type", "media_type", type=click.Choice(["tv", "movie", "multi"]), default="tv")
@click.option("--language", "-l", default="zh-CN", help="语言 (默认 zh-CN)")
@click.option("--year", type=int, default=None, help="年份过滤")
def search(query, media_type, language, year):
    """搜索 TMDB"""
    logger.info("search: query=%r type=%s", query, media_type)
    cands = tmdb.search(query, media_type=media_type, language=language, year=year)
    if not cands:
        click.echo("未找到匹配结果。")
        return
    for c in cands:
        click.echo(f"[{c.media_type}] tmdb_id={c.tmdb_id} | {c.title} ({c.year}) | "
                   f"original={c.original_title} | overview_len={c.overview_length}")


@cli.command(name="fetch-summary")
@click.argument("tmdb_id", type=int)
@click.option("--language", "-l", default="zh-CN")
@click.option("--episodes", type=int, default=None, help="展开某季的集列表")
def fetch_summary(tmdb_id, language, episodes):
    """获取剧摘要（不含完整 overview）"""
    logger.info("fetch-summary: id=%s", tmdb_id)
    s = tmdb.get_show_summary(tmdb_id, language=language)
    click.echo(f"tmdb_id={s.tmdb_id} | {s.title} ({s.year}) | original={s.original_title}")
    click.echo(f"季数={s.total_seasons} 总集数={s.total_episodes} "
               f"overview_available={s.overview_available} overview_length={s.overview_length}")
    for season in s.seasons:
        click.echo(f"  S{season.season_number:02d} {season.name} | 集数={season.episode_count} "
                   f"overview_available={season.overview_available}")
    if s.episode_groups:
        click.echo("剧集组:")
        for g in s.episode_groups:
            click.echo(f"  group_id={g.id} | {g.name} | type={g.type}")
    if episodes is not None:
        eps = tmdb.get_season_episodes(tmdb_id, episodes, language=language)
        click.echo(f"第 {episodes} 季集列表:")
        for e in eps:
            click.echo(f"  E{e.episode_number:02d} {e.name} | overview_len={e.overview_length}")


@cli.command(name="build-plan")
@click.option("--show-id", type=int, required=False, help="TMDB 剧 ID")
@click.option("--movie-id", type=int, required=False, help="TMDB 电影 ID")
@click.option("--source", required=True, help="源目录")
@click.option("--dest", required=True, help="目标根目录")
@click.option("--language", "-l", default="zh-CN")
@click.option("--out", type=click.Path(), default=None, help="计划输出文件路径")
def build_plan(show_id, movie_id, source, dest, language, out):
    """构建重命名与目录整理计划"""
    logger.info("build-plan: show_id=%s movie_id=%s", show_id, movie_id)
    if bool(show_id) == bool(movie_id):
        raise click.UsageError("必须且只能指定 --show-id 或 --movie-id 之一")
    files = fsops.scan_video_files(source)
    if show_id:
        show = tmdb.get_show_summary(show_id, language=language)
        result = build_plan_tv(files, show, dest, language=language)
    else:
        from melodyi_filebot.models import CandidateSummary
        movie = tmdb.get_movie_summary(movie_id, language=language)
        result = build_plan_movie(files, movie, dest)
    output = result.model_dump()
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))
    if out:
        import pathlib
        pathlib.Path(out).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


@cli.command(name="execute-plan")
@click.option("--plan", "plan_path", required=True, type=click.Path(exists=True))
@click.option("--execute", is_flag=True, help="真正执行（默认 dry-run）")
@click.option("--snapshot", type=click.Path(), default=None, help="事务日志保存路径")
def execute_plan_cmd(plan_path, execute, snapshot):
    """执行计划（默认 dry-run）"""
    import pathlib
    plan_data = json.loads(pathlib.Path(plan_path).read_text(encoding="utf-8"))
    from melodyi_filebot.models import BuildPlanResult
    plan = BuildPlanResult(**plan_data)
    snap = fsops.execute_plan(plan, dry_run=not execute, snapshot_path=snapshot if execute else None)
    if not execute:
        click.echo("dry-run 校验通过，未执行任何操作。加 --execute 真正执行。")
    else:
        click.echo("执行完成。")
        if snap and snapshot:
            click.echo(f"事务日志: {snapshot}")


@cli.command()
@click.argument("snapshot", type=click.Path(exists=True))
def undo(snapshot):
    """从事务日志回滚"""
    fsops.undo_from_file(snapshot)
    click.echo("回滚完成。")


if __name__ == "__main__":
    cli()
```

注意：`build-plan` 与 `execute-plan` 命令已在 cli.py 中定义（Task12 一次性写完），但 Task12 的测试只覆盖 search/fetch-summary。`tmdb.get_movie_summary` 需在 Task13 补充。

- [ ] **Step 4: 运行 search/fetch-summary 测试验证通过**

Run: `pytest tests/test_cli.py::TestCliSearch tests/test_cli.py::TestCliFetchSummary -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/melodyi_filebot/cli.py skills/melodyi-filebot/tests/test_cli.py
git commit -m "feat(melodyi-filebot): CLI 框架与 search/fetch-summary 命令"
```

---

## Task 13: CLI（build-plan / execute-plan / undo）与 get_movie_summary

**Files:**
- Modify: `skills/melodyi-filebot/melodyi_filebot/tmdb.py`（追加 get_movie_summary）
- Modify: `skills/melodyi-filebot/tests/test_tmdb.py`（追加 get_movie_summary 测试）
- Modify: `skills/melodyi-filebot/tests/test_cli.py`（追加 build-plan/execute-plan/undo 测试）

- [ ] **Step 1: 追加 get_movie_summary 测试**

在 `tests/test_tmdb.py` 末尾追加：

```python
from melodyi_filebot.models import CandidateSummary


class TestMovieSummary:
    """get_movie_summary 测试"""

    def test_get_movie_summary(self):
        mock_movie = MagicMock()
        mock_movie.info.return_value = {
            "id": 550,
            "title": "搏击俱乐部",
            "original_title": "Fight Club",
            "release_date": "1999-10-15",
            "overview": "x" * 50,
        }
        with patch("melodyi_filebot.tmdb.tmdbsimple.Movies", return_value=mock_movie):
            movie = tmdb.get_movie_summary(550, language="zh-CN")
        assert movie.tmdb_id == 550
        assert movie.title == "搏击俱乐部"
        assert movie.year == 1999
        assert movie.media_type == "movie"
```

- [ ] **Step 2: 运行验证失败**

Run: `pytest tests/test_tmdb.py::TestMovieSummary -v`
Expected: FAIL（`get_movie_summary` 未定义）

- [ ] **Step 3: 在 tmdb.py 追加 get_movie_summary**

在 `tmdb.py` 末尾追加：

```python
def get_movie_summary(tmdb_id: int, language: str = "zh-CN") -> CandidateSummary:
    """获取电影摘要

    Args:
        tmdb_id: TMDB 电影 ID
        language: 语言

    Returns:
        CandidateSummary（media_type="movie"）
    """
    _ensure_key()
    logger.info("获取电影详情开始: id=%s, lang=%s", tmdb_id, language)
    m = tmdbsimple.Movies(id=tmdb_id)
    detail = m.info(language=language)
    cands = summarize.candidates_from_search({"results": [detail]}, media_type="movie")
    movie = cands[0] if cands else CandidateSummary(
        tmdb_id=tmdb_id, title="", original_title="", media_type="movie"
    )
    logger.info("获取电影详情完成: id=%s", tmdb_id)
    return movie
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_tmdb.py::TestMovieSummary -v`
Expected: PASS

- [ ] **Step 5: 追加 CLI build-plan/execute-plan/undo 测试**

在 `tests/test_cli.py` 末尾追加：

```python
import json
from pathlib import Path


class TestCliBuildPlan:
    """build-plan 子命令测试"""

    def test_build_plan_tv(self, tmp_path, tmdb_show_detail):
        from melodyi_filebot.models import ShowSummary, SeasonSummary
        show_dir = tmp_path / "src"
        show_dir.mkdir()
        (show_dir / "莉可丽丝 S01E01.mkv").write_bytes(b"x")
        s = ShowSummary(
            tmdb_id=46260, title="莉可丽丝", original_title="リコリス",
            year=2022, total_seasons=1, total_episodes=13,
            seasons=[SeasonSummary(season_number=1, name="S1", episode_count=13)],
        )
        with patch("melodyi_filebot.cli.tmdb.get_show_summary", return_value=s):
            runner = CliRunner()
            plan_path = str(tmp_path / "plan.json")
            result = runner.invoke(cli, [
                "build-plan", "--show-id", "46260",
                "--source", str(show_dir), "--dest", str(tmp_path / "dest"),
                "--out", plan_path,
            ])
        assert result.exit_code == 0
        plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
        assert any(op["type"] == "move" for op in plan["operations"])


class TestCliExecuteAndUndo:
    """execute-plan 与 undo 测试"""

    def test_execute_and_undo(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        f = src / "a.mkv"
        f.write_bytes(b"x")
        plan_path = str(tmp_path / "plan.json")
        snap_path = str(tmp_path / "snap.json")
        plan = {
            "operations": [
                {"type": "mkdir", "path": str(tmp_path / "dest" / "Show")},
                {"type": "move", "source": str(f), "path": str(tmp_path / "dest" / "Show" / "a.mkv")},
            ],
            "spec_applied": "standard",
            "warnings": [],
        }
        Path(plan_path).write_text(json.dumps(plan), encoding="utf-8")

        runner = CliRunner()
        # dry-run
        r1 = runner.invoke(cli, ["execute-plan", "--plan", plan_path])
        assert r1.exit_code == 0
        assert "dry-run" in r1.output
        assert f.exists()
        # execute
        r2 = runner.invoke(cli, ["execute-plan", "--plan", plan_path, "--execute", "--snapshot", snap_path])
        assert r2.exit_code == 0
        assert not f.exists()
        assert (tmp_path / "dest" / "Show" / "a.mkv").exists()
        # undo
        r3 = runner.invoke(cli, ["undo", snap_path])
        assert r3.exit_code == 0
        assert f.exists()
```

- [ ] **Step 6: 运行测试验证通过**

Run: `pytest tests/test_cli.py -v`
Expected: PASS（全部）

- [ ] **Step 7: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/melodyi_filebot/tmdb.py skills/melodyi-filebot/tests/test_tmdb.py skills/melodyi-filebot/tests/test_cli.py
git commit -m "feat(melodyi-filebot): CLI build-plan/execute-plan/undo 与电影摘要"
```

---

## Task 14: 知识沉淀文档（含 Lycoris 案例）

**Files:**
- Create: `skills/melodyi-filebot/docs/search-heuristics.md`

> 注：`docs/` 在仓库 `.gitignore` 中，但此文档为 skill 运行时资源（随 skill 分发，非 git 跟踪必需）。放在 `docs/` 下符合设计约定；若需追踪可移至 `specs/` 或用 `-f`。本任务保持设计文档约定位置。

- [ ] **Step 1: 写 search-heuristics.md**

```markdown
# 搜索启发式与已知案例

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

## 非标场景（P3 验证，此处先记录特征）

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
- 处理方向：`S01E01-E02`、`S01E01-part1` 命名
```

- [ ] **Step 2: 提交（强制添加，因 docs/ 被 ignore）**

```bash
cd C:/workspace/melodyi-skills
git add -f skills/melodyi-filebot/docs/search-heuristics.md
git commit -m "docs(melodyi-filebot): 搜索启发式与已知案例（含 Lycoris）"
```

---

## Task 15: SKILL.md

**Files:**
- Create: `skills/melodyi-filebot/SKILL.md`

- [ ] **Step 1: 写 SKILL.md**

```markdown
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
```

- [ ] **Step 2: 提交**

```bash
cd C:/workspace/melodyi-skills
git add skills/melodyi-filebot/SKILL.md
git commit -m "docs(melodyi-filebot): 添加 SKILL.md"
```

---

## Task 16: 同步到 workspace 与集成验证

**Files:**
- 无新增（运行同步脚本与集成测试）

- [ ] **Step 1: 运行同步脚本**

Run: `cd C:/workspace/melodyi-skills && bash sync-skills.sh`
Expected: 无报错，`workspace/melodyi-filebot-workspace/.claude/skills/melodyi-filebot/` 生成

- [ ] **Step 2: 全量测试**

Run: `cd skills/melodyi-filebot && pytest -v`
Expected: 全部 PASS

- [ ] **Step 3: CLI 冒烟测试（需真实 TMDB_API_KEY）**

Run: `cd skills/melodyi-filebot && melodyi-filebot --help && melodyi-filebot search --help`
Expected: 输出帮助信息，无 import 错误

- [ ] **Step 4: 提交同步产物（若 sync 产物需纳入版本）**

```bash
cd C:/workspace/melodyi-skills
git status
# 若 workspace 有变更需追踪，按需 add；通常 workspace 为运行时产物，不提交
```

---

## 自审清单

**1. Spec 覆盖：**
- §1 架构与目录布局 → Task1（脚手架）+ 各模块 Task
- §2 关键字解析与搜索策略 → Task4（search）+ Task14（启发式文档）；Lycoris 回退在 Task4 search 多关键字 + Task6/7 S00 处理
- §3 数据流与摘要格式 → Task3（summarize）+ Task5（fetch-summary）
- §4 非标场景 agent 自由 → P0 不实现覆盖，Task14 记录特征；P3 处理
- §5 Jellyfin 目录规范 → Task7（_show_folder/_season_folder/_episode_filename）
- §6 dry-run + 确认 + 回滚 → Task10（dry-run+execute）+ Task11（undo）
- §7 测试策略 → 每个 Task 含 TDD 测试

**2. 占位符扫描：** 无 TBD/TODO；每个代码步骤含完整代码。

**3. 类型一致性：** `ShowSummary`/`CandidateSummary`/`PlanOperation`/`BuildPlanResult`/`ParsedFile`/`EpisodeBrief` 在各 Task 间签名一致；`build_plan_tv`/`build_plan_movie`/`execute_plan`/`undo`/`undo_from_file`/`scan_video_files`/`parse_filename` 命名统一。

**4. 已知待办（非 P0）：**
- `get_movie_summary`（Task13 实现，CLI 已引用）
- NFO 生成（P2，重新设计后实现）
- Bangumi 双源（P1）
- 非标场景覆盖（P3）
