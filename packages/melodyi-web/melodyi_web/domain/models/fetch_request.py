"""统一抓取请求模型"""

from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator


class FetchRequest(BaseModel):
    """统一抓取请求，暴露给 Agent/CLI"""

    url: str = Field(..., min_length=1, description="目标 URL，必填")
    preferred_provider: Optional[str] = Field(
        default=None,
        description="指定使用某个供应商"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """验证 URL 格式"""
        if not v:
            raise ValueError("url 不能为空")
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"无效的 URL: {v}")
        return v