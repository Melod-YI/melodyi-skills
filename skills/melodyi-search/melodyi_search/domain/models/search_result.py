"""统一搜索结果模型"""

from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator, model_validator


class SearchResultItem(BaseModel):
    """单个搜索结果项"""

    title: str = Field(..., min_length=1, description="结果标题")
    url: str = Field(..., min_length=1, description="结果 URL")
    description: str = Field(default="", description="摘要/片段")
    published_date: Optional[datetime] = Field(default=None, description="发布日期")
    source_domain: str = Field(default="", description="来源域名")
    provider_extra: Optional[dict] = Field(default=None, description="提供商原始数据")

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

    @model_validator(mode="after")
    def extract_domain_if_empty(self) -> "SearchResultItem":
        """从 URL 提取域名（如果未提供）"""
        if not self.source_domain and self.url:
            parsed = urlparse(self.url)
            self.source_domain = parsed.netloc
        return self