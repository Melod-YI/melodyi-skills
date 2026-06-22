"""Configuration system with priority chain: CLI > env vars > config file > defaults."""

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class VisionConfig:
    api_key: str
    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    max_tokens: int = 1024
    provider: str = "openai"


def _find_config_file(cli_path: Optional[str] = None) -> Optional[Path]:
    """Find config file: CLI path > ./.image-understanding.json > ~/.config/image-understanding/config.json."""
    if cli_path:
        path = Path(cli_path)
        if path.exists():
            return path

    local_path = Path.cwd() / ".image-understanding.json"
    if local_path.exists():
        return local_path

    home_path = Path.home() / ".config" / "image-understanding" / "config.json"
    if home_path.exists():
        return home_path

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
