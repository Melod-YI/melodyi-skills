"""配置读取与共享目录常量

优先级：环境变量 TMDB_API_KEY > ~/.melodyi-filebot/config.yaml 中的 tmdb_api_key

CONFIG_DIR 是本工具在用户目录下的统一数据目录，配置文件、事务日志等
都放在其下，多处复用。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import yaml

# 用户目录下的统一数据目录（配置、事务日志等）
CONFIG_DIR = Path.home() / ".melodyi-filebot"
CONFIG_PATH = CONFIG_DIR / "config.yaml"
# 事务日志（snapshot）默认存放子目录
SNAPSHOTS_DIR = CONFIG_DIR / "snapshots"

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
