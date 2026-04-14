"""统一搜索请求模型"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


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
    """统一搜索请求模型 - 占位符，将在任务5中实现"""

    pass