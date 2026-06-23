"""配置读取

优先级：环境变量 TMDB_API_KEY > ~/.melodyi-filebot/config.yaml 中的 tmdb_api_key
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import yaml

CONFIG_PATH = Path.home() / ".melodyi-filebot" / "config.yaml"

logger = logging.getLogger(__name__)


def load_tmdb_api_key() -> Optional[str]:
    """读取 TMDB API Key

    Returns:
        API Key 字符串，未配置时返回 None
    """
    env_key = os.environ.get("TMDB_API_KEY")
    if env_key:
        logger.info("TMDB API Key 来源: 环境变量 TMDB_API_KEY")
        return env_key.strip()

    if CONFIG_PATH.exists():
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        key = data.get("tmdb_api_key")
        if key:
            logger.info("TMDB API Key 来源: 配置文件 %s", CONFIG_PATH)
            return str(key).strip()

    logger.info("TMDB API Key 未配置")
    return None
