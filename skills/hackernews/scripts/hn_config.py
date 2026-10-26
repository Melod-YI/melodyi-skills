"""hackernews 共用配置。

目前仅一项：HTTP 代理。配置文件 ~/.melodyi-skills/hackernews/config.json 顶层
``proxy`` 字段（用 JSON，避免为该 skill 引入 yaml 依赖）：

    {"proxy": "http://127.0.0.1:7890"}

未配置时不改变 requests 默认行为（可读 HTTP_PROXY/HTTPS_PROXY 环境变量）。
不设专用环境变量。模块不叫 config.py：避免与 melodyi-vision/scripts/config.py
等同名顶层模块在全量 pytest 时经 sys.path 相互遮蔽。
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 用户目录下的统一配置目录（与其他 melodyi skill 共用 ~/.melodyi-skills 根目录）
CONFIG_DIR = Path.home() / ".melodyi-skills" / "hackernews"
CONFIG_PATH = CONFIG_DIR / "config.json"


def load_proxy() -> Optional[str]:
    """读取代理配置；未配置/文件损坏/非对象返回 None。"""
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("配置文件 %s 解析失败: %s", CONFIG_PATH, e)
        return None
    if not isinstance(data, dict):
        return None
    proxy = data.get("proxy")
    if proxy and str(proxy).strip():
        logger.info("proxy 来源: 配置文件 %s", CONFIG_PATH)
        return str(proxy).strip()
    return None


def request_proxies() -> Optional[dict]:
    """返回传给 requests 的 proxies 参数：配置了代理则 http/https 映射，否则 None。

    None 等价于不传该参数（requests 默认行为，可读环境变量代理）；
    显式映射优先于环境变量（requests merge_setting 语义）。
    """
    proxy = load_proxy()
    if proxy:
        logger.info("HTTP 代理已启用: %s", proxy)
        return {"http": proxy, "https": proxy}
    logger.info("HTTP 代理未配置，使用 requests 默认行为")
    return None
