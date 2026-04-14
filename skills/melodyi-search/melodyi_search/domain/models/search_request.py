"""统一搜索请求模型"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, field_validator


class TimeRange(BaseModel):
    """统一时间范围规范"""

    # 简单范围类型: day, week, month, year
    range_type: Optional[Literal["day", "week", "month", "year"]] = None

    # 精确日期范围
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("range_type")
    @classmethod
    def validate_range_type(cls, v: Optional[str]) -> Optional[str]:
        """验证 range_type 只能是允许的值"""
        if v is not None and v not in ("day", "week", "month", "year"):
            raise ValueError(f"无效的 range_type: {v}，必须是 day/week/month/year")
        return v

    def is_empty(self) -> bool:
        """检查是否为空的时间范围"""
        return self.range_type is None and self.start_date is None and self.end_date is None


class UnifiedSearchRequest(BaseModel):
    """统一搜索请求模型 - 占位符，将在任务5中实现"""

    pass