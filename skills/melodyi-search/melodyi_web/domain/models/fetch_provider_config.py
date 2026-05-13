"""Fetch 供应商配置模型"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


# Fetch 供应商名称
FETCH_PROVIDER_NAMES = Literal["jina-reader", "markdown-new", "tavily-extract", "exa-contents"]


class FetchProviderConfig(BaseModel):
    """Fetch 供应商配置"""

    name: FETCH_PROVIDER_NAMES = Field(..., description="供应商名称")
    api_key: Optional[str] = Field(default=None, description="API 密钥（jina/markdown.new 无需）")
    host: Optional[str] = Field(default=None, description="自定义服务地址")
    timeout_ms: int = Field(default=10000, ge=1000, description="超时时间(毫秒)")
    extra_params: Optional[dict] = Field(default=None, description="供应商特定参数")