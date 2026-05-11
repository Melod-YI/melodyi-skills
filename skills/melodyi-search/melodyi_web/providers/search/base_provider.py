"""提供商抽象基类"""

from abc import ABC, abstractmethod
from typing import Optional, List
from pydantic import BaseModel, Field
from melodyi_web.domain.models.search_request import TimeRange
from melodyi_web.domain.models.search_result import SearchResultItem


class ProviderSearchRequest(BaseModel):
    """提供商原生请求"""

    query: str = Field(..., description="搜索查询")
    max_results: int = Field(default=10, ge=1, description="最大结果数")
    time_range: Optional[TimeRange] = Field(default=None, description="时间范围")
    include_domains: Optional[List[str]] = Field(default=None, description="包含域名")
    exclude_domains: Optional[List[str]] = Field(default=None, description="排除域名")
    language: Optional[str] = Field(default=None, description="语言")
    native_params: Optional[dict] = Field(default=None, description="提供商特定参数")
    modified_query: Optional[str] = Field(default=None, description="修改后的查询")


class ProviderSearchResult(BaseModel):
    """提供商原生结果"""

    provider: str = Field(..., description="提供商名称")
    results: List[SearchResultItem] = Field(default_factory=list, description="搜索结果")
    response_time_ms: int = Field(..., ge=0, description="响应时间")
    raw_response: Optional[dict] = Field(default=None, description="原始响应数据")
    error: Optional[str] = Field(default=None, description="错误信息")


class BaseProvider(ABC):
    """提供商抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """提供商标识符"""
        pass

    @abstractmethod
    def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        """执行搜索（同步版本）"""
        pass

    @abstractmethod
    def supports_time_filter(self) -> bool:
        """是否支持时间过滤"""
        pass

    @abstractmethod
    def supports_domain_filter(self) -> bool:
        """是否支持域名过滤"""
        pass

    @abstractmethod
    def get_max_results_limit(self) -> int:
        """最大结果数限制"""
        pass