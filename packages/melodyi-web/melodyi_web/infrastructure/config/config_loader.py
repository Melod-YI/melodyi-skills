"""配置加载器

配置查找优先级：
1. CLI --config 参数指定的路径
2. 用户目录 ~/.melodyi-web/config.yaml
3. 内置默认配置（不依赖外部文件）
"""

import os
import re
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv

from melodyi_web.infrastructure.config.config_schema import (
    Config,
    ModeConfig,
    FallbackConfig,
    DatabaseConfig,
)
from melodyi_web.domain.models.provider_config import ProviderConfig
from melodyi_web.domain.models.fetch_provider_config import FetchProviderConfig


# 用户配置目录
USER_CONFIG_DIR = Path.home() / ".melodyi-web"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.yaml"


def resolve_env_var(value: str) -> str:
    """解析环境变量引用 ${VAR_NAME}"""
    if not isinstance(value, str):
        return value

    pattern = r'\$\{([^}]+)\}'
    match = re.search(pattern, value)
    if match:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value:
            return value.replace(f"${{{var_name}}}", env_value)
    return value


def _resolve_config_env_vars(config_dict: dict) -> dict:
    """递归解析配置中的所有环境变量"""
    if isinstance(config_dict, dict):
        return {k: _resolve_config_env_vars(v) for k, v in config_dict.items()}
    elif isinstance(config_dict, list):
        return [_resolve_config_env_vars(item) for item in config_dict]
    elif isinstance(config_dict, str):
        return resolve_env_var(config_dict)
    else:
        return config_dict


def _get_builtin_default_config() -> Config:
    """获取内置默认配置

    不依赖外部文件，直接返回默认配置对象。
    Fetch 默认供应商：jina, markdown-new（无需 API Key）
    """
    return Config(
        search_providers=[],  # Search 供应商需用户配置 API Key
        fetch_providers=[
            FetchProviderConfig(name="jina", timeout_ms=15000),
            FetchProviderConfig(name="markdown-new", timeout_ms=15000),
        ],
        mode=ModeConfig(comparison=False, log_dir=str(USER_CONFIG_DIR / "logs")),
        fallback=FallbackConfig(retry_count=2, retry_delay_ms=1000),
        database=DatabaseConfig(database_path=str(USER_CONFIG_DIR / "data" / "compare.db")),
    )


def load_config(config_path: Optional[str] = None) -> Config:
    """加载配置文件

    查找优先级：
    1. config_path（CLI --config 参数）
    2. ~/.melodyi-web/config.yaml（用户配置）
    3. 内置默认配置

    Args:
        config_path: CLI 指定的配置文件路径

    Returns:
        Config 配置对象
    """
    # 1. 先加载 .env 到环境变量（查找当前目录和用户目录）
    load_dotenv()  # 当前目录
    load_dotenv(USER_CONFIG_DIR / ".env")  # 用户目录

    # 2. 确定配置文件路径
    yaml_path: Optional[Path] = None

    if config_path:
        yaml_path = Path(config_path)
    elif USER_CONFIG_FILE.exists():
        yaml_path = USER_CONFIG_FILE

    # 3. 加载 yaml 或使用内置默认
    if yaml_path:
        if not yaml_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {yaml_path}")

        with open(yaml_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f) or {}

        # 解析环境变量
        config_dict = _resolve_config_env_vars(config_dict)

        # 处理空值（YAML 中全部注释时字段为 None）
        # 兼容旧字段名 providers → search_providers
        if config_dict.get("search_providers") is None:
            if config_dict.get("providers") is None:
                config_dict["search_providers"] = []
            else:
                config_dict["search_providers"] = config_dict["providers"]
        if config_dict.get("fetch_providers") is None:
            config_dict["fetch_providers"] = None  # 保持 None，使用默认

        return Config(**config_dict)
    else:
        # 无配置文件，使用内置默认
        return _get_builtin_default_config()