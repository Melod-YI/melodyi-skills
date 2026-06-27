"""全局配置模型"""

from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from melodyi_web.domain.models.provider_config import ProviderConfig
from melodyi_web.domain.models.fetch_provider_config import FetchProviderConfig


# 数据库默认路径：与其他 melodyi skill 一致，落在 ~/.melodyi-skills/melodyi-web/data/
# 用绝对路径而非相对路径，避免 config.yaml 缺少 database 段时把 db 创建到 CWD。
DEFAULT_DATABASE_PATH = str(
    Path.home() / ".melodyi-skills" / "melodyi-web" / "data" / "compare.db"
)


class DatabaseConfig(BaseModel):
    """数据库配置"""

    database_path: str = Field(
        default=DEFAULT_DATABASE_PATH,
        description="SQLite 数据库文件路径"
    )


class ModeConfig(BaseModel):
    """运行模式配置"""

    comparison: bool = Field(default=False, description="是否开启比对模式")
    log_dir: str = Field(default="./logs", description="日志目录")


class FallbackConfig(BaseModel):
    """回退配置"""

    retry_count: int = Field(default=2, ge=0, description="重试次数")
    retry_delay_ms: int = Field(default=1000, ge=0, description="重试间隔")


class Config(BaseModel):
    """全局配置"""

    search_providers: List[ProviderConfig] = Field(
        default_factory=list,
        description="搜索供应商配置数组"
    )
    fetch_providers: Optional[List[FetchProviderConfig]] = Field(
        default=None,
        description="抓取供应商配置数组"
    )
    mode: ModeConfig = Field(default_factory=ModeConfig, description="运行模式")
    fallback: FallbackConfig = Field(default_factory=FallbackConfig, description="回退配置")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="数据库配置")

    # 兼容旧配置文件中的 providers 字段
    providers: Optional[List[ProviderConfig]] = Field(
        default=None,
        description="搜索供应商配置（已废弃，请使用 search_providers）"
    )

    @model_validator(mode="after")
    def _migrate_providers(self):
        """处理兼容性：如果使用旧字段 providers，迁移到 search_providers"""
        if self.providers and not self.search_providers:
            # Pydantic V2 需要用这种方式修改字段
            object.__setattr__(self, 'search_providers', self.providers)
        return self

    def get_search_provider_names(self) -> List[str]:
        """获取所有搜索供应商名称列表"""
        return [p.name for p in self.search_providers]

    def get_search_provider_by_name(self, name: str) -> Optional[ProviderConfig]:
        """根据名称获取搜索供应商配置"""
        for p in self.search_providers:
            if p.name == name:
                return p
        return None

    def get_fetch_provider_names(self) -> List[str]:
        """获取所有抓取供应商名称列表"""
        if self.fetch_providers is None:
            return []
        return [p.name for p in self.fetch_providers]

    def get_fetch_provider_by_name(self, name: str) -> Optional[FetchProviderConfig]:
        """根据名称获取抓取供应商配置"""
        if self.fetch_providers is None:
            return None
        for p in self.fetch_providers:
            if p.name == name:
                return p
        return None

    # 兼容旧方法名
    def get_provider_names(self) -> List[str]:
        """获取搜索供应商名称列表（兼容旧接口）"""
        return self.get_search_provider_names()

    def get_provider_by_name(self, name: str) -> Optional[ProviderConfig]:
        """根据名称获取搜索供应商配置（兼容旧接口）"""
        return self.get_search_provider_by_name(name)