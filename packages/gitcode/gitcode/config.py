"""配置读取：token 优先级 环境变量 GITCODE_TOKEN > ~/.melodyi-skills/gitcode/config.json

与其他 melodyi skill 共用 ~/.melodyi-skills/ 根目录。token 是账号级凭据，
未来 submit/review/merge 等 skill 共用同一份配置，故目录名为 gitcode。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".melodyi-skills" / "gitcode"
CONFIG_PATH = CONFIG_DIR / "config.json"


def load_token(config_path: Optional[Path] = None) -> Optional[str]:
    """读取 GitCode token

    优先级：环境变量 GITCODE_TOKEN > 配置文件（config_path 或默认 CONFIG_PATH）
    中的 gitcode_token 字段。空字符串视作未设置。

    Returns:
        token 字符串，未配置时返回 None
    """
    env_token = os.environ.get("GITCODE_TOKEN")
    if env_token and env_token.strip():
        logger.info("token 来源: 环境变量 GITCODE_TOKEN")
        return env_token.strip()

    path = Path(config_path) if config_path else CONFIG_PATH
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("配置文件 %s 解析失败: %s", path, e)
            return None
        token = data.get("gitcode_token") if isinstance(data, dict) else None
        if token and str(token).strip():
            logger.info("token 来源: 配置文件 %s", path)
            return str(token).strip()

    logger.info("token 未配置")
    return None
