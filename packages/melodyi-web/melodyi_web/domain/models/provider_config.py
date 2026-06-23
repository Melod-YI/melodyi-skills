"""提供商配置模型"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


# 支持的提供商名称
PROVIDER_NAMES = Literal["minimax-cn", "tavily", "brave", "exa", "searxng", "firecrawl"]


class ProviderConfig(BaseModel):
    """单个提供商配置"""

    name: PROVIDER_NAMES = Field(..., description="提供商名称")
    api_key: Optional[str] = Field(default=None, description="API 密钥")
    host: Optional[str] = Field(default=None, description="自托管服务地址")
    timeout_ms: int = Field(default=10000, ge=1000, description="超时时间(毫秒)")
    max_results: int = Field(default=10, ge=1, description="最大结果数")
    extra_params: Optional[dict] = Field(default=None, description="提供商特定参数")

    def is_self_hosted(self) -> bool:
        """检查是否为自托管提供商"""
        return self.name in ("searxng", "firecrawl") and self.host is not None