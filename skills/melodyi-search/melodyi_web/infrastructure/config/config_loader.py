"""配置加载器，支持 .env 和 yaml"""

import os
import re
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv
from melodyi_web.infrastructure.config.config_schema import Config


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


def load_config(config_path: Optional[str] = None) -> Config:
    """加载配置文件"""
    # 1. 先加载 .env 到环境变量
    load_dotenv()

    # 2. 确定配置文件路径
    if config_path is None:
        config_path = Path(__file__).parent / "default_config.yaml"
    else:
        config_path = Path(config_path)

    # 3. 加载 yaml
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)

    # 4. 解析环境变量
    config_dict = _resolve_config_env_vars(config_dict)

    # 5. 创建 Config 对象
    return Config(**config_dict)