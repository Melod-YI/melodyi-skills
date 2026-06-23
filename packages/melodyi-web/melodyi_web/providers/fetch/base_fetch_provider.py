"""Fetch 供应商抽象基类"""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field


class ProviderFetchRequest(BaseModel):
    """供应商原生请求"""

    url: str = Field(..., description="目标 URL")
    native_params: Optional[dict] = Field(default=None, description="供应商特定参数")


class ProviderFetchResult(BaseModel):
    """供应商原生结果"""

    provider: str = Field(..., description="供应商名称")
    url: str = Field(..., description="抓取的 URL")
    title: Optional[str] = Field(default=None, description="页面标题")
    content: str = Field(default="", description="抓取内容")
    response_time_ms: int = Field(..., ge=0, description="响应时间")
    raw_response: Optional[dict] = Field(default=None, description="原始响应数据")
    metadata: dict = Field(default_factory=dict, description="元数据")
    error: Optional[str] = Field(default=None, description="错误信息")


class BaseFetchProvider(ABC):
    """Fetch 供应商抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """供应商标识符"""
        pass

    @abstractmethod
    def fetch(self, request: ProviderFetchRequest) -> ProviderFetchResult:
        """执行抓取"""
        pass

    @abstractmethod
    def supports_js_render(self) -> bool:
        """是否支持 JS 渲染"""
        pass

    @abstractmethod
    def get_output_format(self) -> str:
        """输出格式：markdown 或 raw"""
        pass