"""统一搜索请求模型"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class TimeRange(BaseModel):
    """统一时间范围规范"""

    # 简单范围类型: day, week, month, year
    range_type: Optional[Literal["day", "week", "month", "year"]] = Field(
        default=None,
        description="时间范围类型：day、week、month、year"
    )

    # 精确日期范围
    start_date: Optional[datetime] = Field(
        default=None,
        description="起始日期（精确范围）"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="结束日期（精确范围）"
    )

    def is_empty(self) -> bool:
        """检查是否为空的时间范围"""
        return self.range_type is None and self.start_date is None and self.end_date is None


class UnifiedSearchRequest(BaseModel):
    """统一搜索请求，暴露给 Agent/CLI"""

    query: str = Field(..., min_length=1, description="搜索查询，必填")
    max_results: int = Field(default=10, ge=1, description="期望最大结果数")
    time_range: Optional[TimeRange] = Field(default=None, description="时间过滤")
    include_domains: Optional[List[str]] = Field(default=None, description="包含特定域名")
    exclude_domains: Optional[List[str]] = Field(default=None, description="排除特定域名")
    language: Optional[str] = Field(default=None, description="ISO 语言代码")
    preferred_provider: Optional[str] = Field(default=None, description="指定使用某个提供商")

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        """验证 query 不能为空"""
        if not v or not v.strip():
            raise ValueError("query 不能为空")
        return v.strip()