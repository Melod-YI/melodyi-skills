"""配置系统，优先级：CLI 参数 > 环境变量 > 配置文件 > 默认值。

配置文件查找不依赖执行位置（cwd），而是相对脚本自身位置与用户主目录：
1. CLI `--config <path>` 指定的路径
2. 用户目录 `~/.melodyi-skills/melodyi-vision/config.json`（用户私有配置，优先；与其他 melodyi skill 共用 ~/.melodyi-skills/ 根目录）
3. 脚本同目录的 `config.json`（项目自带示例，作为 fallback；相对 `__file__` 定位）

支持两种配置形态：
1. 多供应商（推荐）：顶层 `providers`（name→profile 映射）+ `active_provider`（选择哪个 profile）。
   每个 profile 含 api_key/api_base/model，可选 max_tokens/stream 覆盖顶层默认。
   切换供应商 = 改 `active_provider` 一个字段。
2. 扁平（向后兼容）：顶层直接放 api_key/api_base/model 等，无 providers 段。
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
    # 是否使用流式调用（SSE），默认开启；可经配置/环境变量/CLI 关闭以走一次性返回
    stream: bool = True
    # 是否校验 SSL 证书（默认校验）；仅在内网自签名证书、自托管网关等场景下关闭
    verify_ssl: bool = True
    # HTTP 代理地址（如 http://127.0.0.1:7890），API 调用与图片下载均走该代理；
    # 全局共享不 per-profile，无专用环境变量；None 表示未配置（走 urllib 默认行为）
    proxy: Optional[str] = None
    # 当前生效的供应商 profile 名（多供应商配置时由 active_provider 解析得到，便于排障/日志）
    active_provider: Optional[str] = None


def _parse_bool(value) -> bool:
    """将字符串或已是布尔的值解析为布尔，支持 true/false/1/0/yes/no/on/off（不区分大小写）。"""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "on")


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
        "stream": "VISION_STREAM",
        "verify_ssl": "VISION_VERIFY_SSL",
        "active_provider": "VISION_ACTIVE_PROVIDER",
    }
    result = {}
    for key, env_var in env_map.items():
        value = os.environ.get(env_var)
        if value is not None:
            if key == "max_tokens":
                result[key] = int(value)
            elif key in ("stream", "verify_ssl"):
                result[key] = _parse_bool(value)
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
    """Load configuration with priority: CLI args > env vars > config file > defaults.

    支持多供应商配置：顶层 ``providers``（name→profile）+ ``active_provider`` 选择
    profile；profile 字段覆盖顶层默认，``max_tokens``/``stream`` 可 per-profile 覆盖。
    无 ``providers`` 段时回退扁平结构（向后兼容）。
    """
    # Start with config file values
    values = _load_config_file(config_path)

    # Override with env vars
    env_values = _get_env_vars()
    values.update(env_values)

    # Override with CLI args
    values = _apply_cli_overrides(values, cli_overrides)

    # 配置文件/环境变量可能把 stream/verify_ssl 写成字符串，统一归一为布尔
    if "verify_ssl" in values:
        values["verify_ssl"] = _parse_bool(values["verify_ssl"])
    if "stream" in values:
        values["stream"] = _parse_bool(values["stream"])
    # proxy 统一 strip；空字符串/纯空白/未配置归一为 None
    # （与 verify_ssl 一样全局共享，不 per-profile）
    proxy_value = str(values.get("proxy") or "").strip()
    values["proxy"] = proxy_value or None

    # 解析多供应商 profile（若有）
    providers_map = values.pop("providers", None)
    if providers_map:
        active = values.get("active_provider")
        if not active:
            print(
                "Error: 'providers' 已配置但未指定 'active_provider'。"
                "请在配置中设置 active_provider 为 providers 里的某个 key。",
                file=sys.stderr,
            )
            sys.exit(1)
        profile = providers_map.get(active)
        if profile is None:
            available = ", ".join(sorted(providers_map.keys()))
            print(
                f"Error: active_provider '{active}' 不在 providers 中。可选: {available}",
                file=sys.stderr,
            )
            sys.exit(1)
        # profile 字段覆盖顶层（per-profile 优先）
        for key in ("api_key", "api_base", "model"):
            if profile.get(key) is not None:
                values[key] = profile[key]
        # max_tokens / stream 允许 per-profile 覆盖，缺省回退顶层默认
        if profile.get("max_tokens") is not None:
            values["max_tokens"] = profile["max_tokens"]
        if profile.get("stream") is not None:
            values["stream"] = _parse_bool(profile["stream"])

    # Check for required api_key
    if "api_key" not in values or not values["api_key"]:
        print("Error: API key is required. Set VISION_API_KEY environment variable or provide in config file.", file=sys.stderr)
        sys.exit(1)

    # 仅保留 VisionConfig 认识的字段，避免 providers 嵌套 dict 等被传入构造
    known = {
        "api_key", "api_base", "model", "max_tokens",
        "provider", "stream", "verify_ssl", "proxy", "active_provider",
    }
    kwargs = {k: v for k, v in values.items() if k in known}
    return VisionConfig(**kwargs)
