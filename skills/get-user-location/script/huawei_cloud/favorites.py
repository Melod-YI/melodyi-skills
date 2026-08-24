"""
收藏点模块

职责:
  - 加载用户收藏点配置 ~/.melodyi-skills/get-user-location/favorites.json
  - 基于经纬度计算球面距离（Haversine）
  - 在给定半径内匹配收藏点，按距离从近到远排序
  - 渲染命中收藏点的标准输出文本

收藏点功能目的:
  定位精度有限，反向地理编码得到的地址文本在经纬度小幅偏移时可能描述偏差较大；
  但经纬度本身偏差很小。收藏点通过比较经纬度距离，能更稳定地判断用户是否处于
  特定地点附近（例如家附近、公司附近），作为地址文本的补充。

收藏点文件格式（JSON 顶层数组，文件缺失或非法时静默返回空列表，不阻断主流程）:
  [
    {"name": "家", "latitude": 31.97951, "longitude": 118.76740},
    {"name": "公司", "latitude": 31.98500, "longitude": 118.77000}
  ]

大地标（景区等）支持同一 name 配多个采样经纬度：定位命中任意一点即视为在该
name 附近，输出按 name 归并、取最近距离。每个采样点可单独配置 radius_m
（经纬度组级，非 name 级）作为该点专属允许距离，缺省/非法时回退默认 200m：
  [
    {"name": "玄武湖", "latitude": 32.07100, "longitude": 118.79500},
    {"name": "玄武湖", "latitude": 32.06800, "longitude": 118.79200},
    {"name": "玄武湖", "latitude": 32.07300, "longitude": 118.79800, "radius_m": 300}
  ]
"""

import json
import logging
import math
from typing import Any, Dict, List, Optional

from .config import USER_CONFIG_DIR

logger = logging.getLogger(__name__)

# 用户目录下的收藏点文件（与其他 melodyi skill 共用 ~/.melodyi-skills/ 根目录）
USER_FAVORITES_FILE = USER_CONFIG_DIR / "favorites.json"

# 默认匹配半径（米）：定位精度有限，200m 内视为『在该收藏点附近』
DEFAULT_RADIUS_M = 200.0

# 地球半径（米）
_EARTH_RADIUS_M = 6_371_000.0


def load_favorites(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """读取收藏点文件，返回校验通过的收藏点列表。

    文件缺失、JSON 非法或顶层不是数组时返回空列表；
    每条记录需含 name(str)、latitude(number)、longitude(number)，非法条目被丢弃并记日志。

    Args:
        path: 收藏点文件路径，未指定时取 USER_FAVORITES_FILE

    Returns:
        校验通过的收藏点列表（每项含 name/latitude/longitude）
    """
    file_path = path if path else str(USER_FAVORITES_FILE)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("收藏点文件读取失败 (%s): %s", file_path, e)
        return []

    if not isinstance(data, list):
        logger.warning("收藏点文件顶层非数组，忽略: %s", file_path)
        return []

    favorites: List[Dict[str, Any]] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning("收藏点 #%d 非对象，已跳过", idx)
            continue
        name = item.get("name")
        latitude = item.get("latitude")
        longitude = item.get("longitude")
        if not isinstance(name, str) or not name:
            logger.warning("收藏点 #%d 缺少 name，已跳过", idx)
            continue
        if not isinstance(latitude, (int, float)) or isinstance(latitude, bool):
            logger.warning("收藏点 #%d latitude 非数值，已跳过", idx)
            continue
        if not isinstance(longitude, (int, float)) or isinstance(longitude, bool):
            logger.warning("收藏点 #%d longitude 非数值，已跳过", idx)
            continue
        # 可选 radius_m：该采样点专属允许距离（经纬度组级，非 name 级）。
        # 缺省/非法时置 None，匹配阶段回退 DEFAULT_RADIUS_M，保证默认值单一来源。
        radius_m = item.get("radius_m")
        if radius_m is not None and (
            not isinstance(radius_m, (int, float))
            or isinstance(radius_m, bool)
            or radius_m <= 0
        ):
            logger.warning(
                "收藏点 #%d radius_m 非法（需为正数），回退默认: %r", idx, radius_m
            )
            radius_m = None
        favorites.append(
            {
                "name": name,
                "latitude": latitude,
                "longitude": longitude,
                "radius_m": radius_m,
            }
        )

    logger.info("加载收藏点 %d 个", len(favorites))
    return favorites


def haversine_distance_m(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    """计算两经纬度之间的球面距离（Haversine 公式），单位米。

    Args:
        lat1, lng1: 起点纬度/经度（度）
        lat2, lng2: 终点纬度/经度（度）

    Returns:
        距离（米），同一坐标返回 0.0
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_M * c


def find_nearby_favorites(
    latitude: float,
    longitude: float,
    favorites: List[Dict[str, Any]],
    radius_m: float = DEFAULT_RADIUS_M,
) -> List[Dict[str, Any]]:
    """返回距给定坐标在各自允许半径内的收藏点，按距离从近到远排序。

    大地标（景区等）可在 favorites.json 中以同一 name 配多个采样经纬度，
    命中任意一点即视为在该 name 附近；同 name 多点命中时只保留最近者。
    每个采样点可单独配置 radius_m（经纬度组级，非 name 级），缺省时回退
    本函数的 radius_m 形参（默认 DEFAULT_RADIUS_M）。

    性能: 线性扫描 O(n)，单次 Haversine 约 1µs 量级，1000 个收藏点 < 1ms，
    远小于收藏点文件的磁盘读取耗时，无需空间索引。

    Args:
        latitude, longitude: 当前定位坐标（度）
        favorites: load_favorites 返回的收藏点列表
        radius_m: 匹配半径回退默认值（米），仅当收藏点未配置自身 radius_m 时生效

    Returns:
        命中收藏点列表（每个 name 至多一条，附加 distance_m 字段，按距离升序，
        latitude/longitude 为触发命中的最近采样点坐标）；无命中返回空列表。不修改入参。
    """
    # 按 name 归并：同 name 多点命中只保留 distance_m 最小者（并列取遍历序首个）。
    nearest_by_name: Dict[str, Dict[str, Any]] = {}
    for fav in favorites:
        rec_radius = fav.get("radius_m")
        effective_radius = rec_radius if rec_radius is not None else radius_m
        dist = haversine_distance_m(
            latitude, longitude, fav["latitude"], fav["longitude"]
        )
        if dist > effective_radius:
            continue
        name = fav["name"]
        existing = nearest_by_name.get(name)
        if existing is None or dist < existing["distance_m"]:
            nearest_by_name[name] = {
                "name": name,
                "latitude": fav["latitude"],
                "longitude": fav["longitude"],
                "distance_m": dist,
            }
    matches = list(nearest_by_name.values())
    matches.sort(key=lambda m: m["distance_m"])
    return matches


def format_nearby_favorites(matches: List[Dict[str, Any]]) -> Optional[str]:
    """渲染命中收藏点的多行标准输出文本。

    Args:
        matches: find_nearby_favorites 返回的命中列表

    Returns:
        多行文本（标题行 + 每个收藏点一行，距离四舍五入到整米）；
        无命中返回 None。
    """
    if not matches:
        return None
    lines = ["附近收藏点:"]
    for m in matches:
        lines.append(f"  - {m['name']} ({int(round(m['distance_m']))}m)")
    return "\n".join(lines)
