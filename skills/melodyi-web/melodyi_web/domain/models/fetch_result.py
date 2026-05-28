"""统一抓取结果模型"""

from typing import Optional
from pydantic import BaseModel, Field


class FetchError(BaseModel):
    """抓取错误"""

    error_type: str = Field(..., description="错误类型分类")
    original_message: str = Field(default="", description="供应商原始错误")
    guidance: str = Field(default="", description="指导 Agent 行为的提示")


class FetchResult(BaseModel):
    """统一抓取结果，暴露给 Agent/CLI"""

    provider: str = Field(..., description="响应的供应商")
    url: str = Field(..., description="抓取的 URL")
    title: Optional[str] = Field(default=None, description="页面标题")
    content: str = Field(default="", description="抓取内容（Markdown 或原始文本）")
    response_time_ms: int = Field(..., ge=0, description="响应时间(毫秒)")
    metadata: dict = Field(default_factory=dict, description="元数据")
    error: Optional[FetchError] = Field(default=None, description="错误信息")
    session_id: Optional[str] = Field(default=None, description="对比会话 ID")

    def is_success(self) -> bool:
        """检查是否成功"""
        return self.error is None

    def has_content(self) -> bool:
        """检查是否有内容"""
        return len(self.content) > 0