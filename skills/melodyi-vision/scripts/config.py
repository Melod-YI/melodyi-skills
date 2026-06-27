"""配置系统，优先级：CLI 参数 > 环境变量 > 配置文件 > 默认值。

配置文件查找不依赖执行位置（cwd），而是相对脚本自身位置与用户主目录：
1. CLI `--config <path>` 指定的路径
2. 用户目录 `~/.melodyi-skills/melodyi-vision/config.json`（用户私有配置，优先；与其他 melodyi skill 共用 ~/.melodyi-skills/ 根目录）
3. 脚本同目录的 `config.json`（项目自带示例，作为 fallback；相对 `__file__` 定位）
"""

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# 脚本所在目录：项目自带示例配置相对此定位，与执行位置无关
SCRIPT_DIR = Path(__file__).resolve().parent
# 用户主目录下的统一配置目录（与其他 melodyi skill 约定一致，共用 ~/.melodyi-skills/ 根目录）
USER_CONFIG_DIR = Path.home() / ".melodyi-skills" / "melodyi-vision"


@dataclass
class VisionConfig:
    api_key: str
    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    max_tokens: int = 1024
    provider: str = "openai"


def _config_search_paths(cli_path: Optional[str] = None) -> list:
    """返回配置文件候选路径（按优先级），均不依赖 cwd。

    Args:
        cli_path: CLI `--config` 指定的路径，给定后只查它

    Returns:
        候选 Path 列表
    """
    if cli_path:
        return [Path(cli_path)]
    # 不依赖 cwd：用户私有配置优先于项目自带示例
    return [
        USER_CONFIG_DIR / "config.json",
        SCRIPT_DIR / "config.json",
    ]


def _find_config_file(cli_path: Optional[str] = None) -> Optional[Path]:
    """按优先级查找首个存在的配置文件，找不到返回 None。"""
    for path in _config_search_paths(cli_path):
        if path.exists():
            return path
    return None


def _load_config_file(config_path: Optional[str] = None) -> dict:
    """Load config from file, return empty dict if not found."""
    path = _find_config_file(config_path)
    if path is None:
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _get_env_vars() -> dict:
    """Get config values from environment variables."""
    env_map = {
        "api_key": "VISION_API_KEY",
        "api_base": "VISION_API_BASE",
        "model": "VISION_MODEL",
        "max_tokens": "VISION_MAX_TOKENS",
        "provider": "VISION_PROVIDER",
    }
    result = {}
    for key, env_var in env_map.items():
        value = os.environ.get(env_var)
        if value is not None:
            if key == "max_tokens":
                result[key] = int(value)
            else:
                result[key] = value
    return result


def _apply_cli_overrides(values: dict, cli_overrides: Optional[dict] = None) -> dict:
    """Apply CLI overrides, ignoring None values."""
    if not cli_overrides:
        return values
    for key, value in cli_overrides.items():
        if value is not None:
            values[key] = value
    return values


def load_config(cli_overrides: Optional[dict] = None, config_path: Optional[str] = None) -> VisionConfig:
    """Load configuration with priority: CLI args > env vars > config file > defaults."""
    # Start with config file values
    values = _load_config_file(config_path)

    # Override with env vars
    env_values = _get_env_vars()
    values.update(env_values)

    # Override with CLI args
    values = _apply_cli_overrides(values, cli_overrides)

    # Check for required api_key
    if "api_key" not in values or not values["api_key"]:
        print("Error: API key is required. Set VISION_API_KEY environment variable or provide in config file.", file=sys.stderr)
        sys.exit(1)

    return VisionConfig(**values)
