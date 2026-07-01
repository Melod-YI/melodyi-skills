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
    runtime: Optional[int] = None  # 时长（分钟），取自 TMDB runtime 字段
    season_number: Optional[int] = None  # 剧集组内集可跨季，需带季号；普通季集为 None

    @property
    def overview_available(self) -> bool:
        return self.overview_length >= 10


# TMDB 剧集组 type 枚举（共 7 种，取自 TMDB API 文档）
EPISODE_GROUP_TYPES = {
    1: "首播顺序",
    2: "绝对集号",
    3: "DVD",
    4: "数字版",
    5: "剧情篇章",
    6: "制作顺序",
    7: "TV",
}


class EpisodeGroupBrief(BaseModel):
    """剧集组摘要（非标场景1）"""

    id: str
    name: str
    type: int
    episode_count: int = 0

    @property
    def type_name(self) -> str:
        """type 数字 → 可读名称，未知值回退为数字字符串"""
        return EPISODE_GROUP_TYPES.get(self.type, str(self.type))


class EpisodeGroupSub(BaseModel):
    """剧集组内的子组（一组可含多个子组，如正片 + OVA）"""

    name: str
    episodes: List[EpisodeBrief] = Field(default_factory=list)


class EpisodeGroupDetail(BaseModel):
    """剧集组详情"""

    id: str
    name: str
    type: int
    episode_count: int = 0
    group_count: int = 0
    sub_groups: List[EpisodeGroupSub] = Field(default_factory=list)

    @property
    def type_name(self) -> str:
        return EPISODE_GROUP_TYPES.get(self.type, str(self.type))


class BangumiSubjectSummary(BaseModel):
    """Bangumi 条目摘要（搜索/详情共用）

    与 TMDB overview 不同：bangumi summary 是填充源的核心价值，故完整保留
    （下游 --with-bangumi 再决定如何压缩不进上下文）。
    """

    subject_id: int
    type: int = 0  # 2=动画
    name: str = ""  # 原文名
    name_cn: str = ""  # 中文名
    date: Optional[str] = None  # 放送日期 YYYY-MM-DD
    eps: int = 0  # 总集数
    platform: str = ""  # TV/WEB/...
    summary: str = ""  # 完整简介
    summary_length: int = 0

    @property
    def summary_available(self) -> bool:
        return self.summary_length >= 10


class BangumiEpisodeBrief(BaseModel):
    """Bangumi 集摘要"""

    episode_id: int
    type: int = 0  # 0=本篇 1=特别篇 2=OP 3=ED 4=预告 5=MAD 6=其他 7=非正片
    name: str = ""
    name_cn: str = ""
    sort: float = 0.0  # bangumi sort 可为小数（如 5.5）
    ep: Optional[int] = None
    airdate: Optional[str] = None
    duration: Optional[str] = None  # "00:24:00"
    desc: str = ""  # 集简介（对应 bangumi desc 字段）
    desc_length: int = 0

    @property
    def desc_available(self) -> bool:
        return self.desc_length >= 10


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
    """build-plan 结果（执行清单：move + nfo 操作）"""

    operations: List[PlanOperation]
    nfo_operations: List["NfoOperation"] = Field(default_factory=list)
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


class TreeNode(BaseModel):
    """路径分析树节点

    目录节点：children 非空，video_count 为自身及子树累计视频数；
    文件节点：is_video 标记，视频时 duration 为 "HH:MM:SS"。
    """

    name: str
    type: str  # "dir" | "file"
    path: str
    video_count: int = 0  # 目录：子树累计视频数
    is_video: bool = False  # 文件：是否视频
    duration_seconds: Optional[float] = None  # 文件视频时长（秒，原始值；展示时再格式化）
    children: Optional[List["TreeNode"]] = None  # 目录：子节点


class PathAnalysis(BaseModel):
    """analyze_path 结果

    正常情况：truncated=False，tree 为完整树（视频带时长）。
    命中告警（深度≥阈值 或 文件数超阈值）：truncated=True，tree=None，
    仅返回概要（by_ext / by_depth）。
    """

    root: str
    truncated: bool
    total_files: int = 0
    total_videos: int = 0
    total_dirs: int = 0
    max_depth: int = 0  # 最深目录层，根目录=1
    tree: Optional[TreeNode] = None
    warnings: List[str] = Field(default_factory=list)
    by_ext: Optional[dict] = None  # 截断时：扩展名 -> 文件数
    by_depth: Optional[dict] = None  # 截断时：目录层(str) -> 目录数


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


TreeNode.model_rebuild()
BuildPlanResult.model_rebuild()
