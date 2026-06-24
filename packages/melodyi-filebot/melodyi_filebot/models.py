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


class FileMapping(BaseModel):
    """单个文件到 TMDB 条目（季/集）的显式映射

    用于 override：agent/用户显式指定每个文件对应哪一季哪一集，
    而非依赖文件名自动解析。
    """

    file: str
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_end: Optional[int] = None  # 多集范围终点（一文件对应多集）
    part: Optional[int] = None  # 分段编号


class PlanMap(BaseModel):
    """文件→TMDB 条目的显式映射（override 用）

    由 draft-map 生成初版，agent/用户编辑后交给 build-plan --map 执行。
    """

    media_type: str  # "tv" | "movie"
    tmdb_id: int
    language: str = "zh-CN"
    mappings: List[FileMapping] = Field(default_factory=list)
