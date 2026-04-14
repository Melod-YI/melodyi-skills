"""统一搜索结果模型"""

from datetime import datetime
from typing import List, Optional
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


class SearchError(BaseModel):
    """带 Agent 补救指导的错误"""

    error_type: str = Field(..., description="错误类型分类")
    original_message: str = Field(default="", description="提供商原始错误")
    guidance: str = Field(default="", description="指导 Agent 行为的提示")


class UnifiedSearchResult(BaseModel):
    """统一搜索结果，暴露给 Agent/CLI"""

    provider: str = Field(..., description="响应的提供商")
    response_time_ms: int = Field(..., ge=0, description="响应时间(毫秒)")
    results: List[SearchResultItem] = Field(default_factory=list, description="搜索结果列表")
    comparison_log: Optional[dict] = Field(default=None, description="比对模式内部数据")
    error: Optional[SearchError] = Field(default=None, description="错误及指导")

    def is_success(self) -> bool:
        """检查是否成功"""
        return self.error is None

    def has_results(self) -> bool:
        """检查是否有结果"""
        return len(self.results) > 0