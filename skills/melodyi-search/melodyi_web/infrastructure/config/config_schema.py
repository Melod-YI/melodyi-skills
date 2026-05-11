"""全局配置模型"""

from typing import List
from pydantic import BaseModel, Field
from melodyi_web.domain.models.provider_config import ProviderConfig


class DatabaseConfig(BaseModel):
    """数据库配置"""

    database_path: str = Field(
        default="./data/compare.db",
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

    providers: List[ProviderConfig] = Field(..., description="提供商配置数组")
    mode: ModeConfig = Field(default_factory=ModeConfig, description="运行模式")
    fallback: FallbackConfig = Field(default_factory=FallbackConfig, description="回退配置")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="数据库配置")

    def get_provider_names(self) -> List[str]:
        """获取所有提供商名称列表"""
        return [p.name for p in self.providers]

    def get_provider_by_name(self, name: str) -> ProviderConfig | None:
        """根据名称获取提供商配置"""
        for p in self.providers:
            if p.name == name:
                return p
        return None