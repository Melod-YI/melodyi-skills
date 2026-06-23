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
