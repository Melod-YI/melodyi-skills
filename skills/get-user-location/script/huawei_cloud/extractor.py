"""
数据提取模块

职责:
  - 从拦截器捕获的原始数据中提取结构化信息
  - 验证响应有效性（returnCode == "0"）
  - 保存结果到 JSON 文件
"""

import copy
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 顶层需移除的无用字段
_UNUSED_TOP_KEYS = ("aois", "roads", "intersections", "returnDesc")

# addressComponent 中需移除的无用字段
_UNUSED_ADDRESS_COMPONENT_KEYS = ("streetNumber", "adminCode")

# pois 精简后保留的最大数量（按 distance 升序）
_MAX_POIS = 2


def extract_data(captured: Dict[str, Any]) -> Dict[str, Any]:
    """
    从拦截器捕获的原始数据中提取 JSON 响应体

    Args:
        captured: 单次 reverseGeocode 捕获数据（Interceptor.captures 中的一个元素）

    Returns:
        解析后的 JSON 数据字典

    Raises:
        RuntimeError: 未捕获到请求或响应体为空
    """
    if not captured:
        raise RuntimeError("未捕获到任何请求")

    body = captured.get("body")
    if not body:
        raise RuntimeError("捕获的响应体为空")

    logger.info("解析响应数据...")
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"响应体 JSON 解析失败: {e}") from e


def validate_response(data: Dict[str, Any]) -> Dict[str, str]:
    """
    验证响应数据有效性并提取关键信息

    Args:
        data: 解析后的 JSON 响应

    Returns:
        包含 return_code 和 address 的字典

    Raises:
        RuntimeError: returnCode 不为 "0"
    """
    return_code = str(data.get("returnCode", ""))

    if return_code != "0":
        logger.error("未捕获到有效数据, returnCode=%s", return_code)
        raise RuntimeError(f"未捕获到有效数据 (returnCode={return_code})")

    address = data.get("addressDescription", "")
    logger.info("数据验证通过, 用户当前地址: %s", address)

    return {
        "return_code": return_code,
        "address": address,
    }


def extract_request_location(captured: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    从捕获的 reverseGeocode 请求 payload 中提取查询经纬度

    payload 形如:
      {"location": {"latitude": ..., "longitude": ...}, "language": "zh-CN", ...}

    该经纬度为本次查询的输入点，是输出中最真实准确的定位坐标。

    Args:
        captured: 单次 reverseGeocode 捕获数据（含 request_body）

    Returns:
        {"latitude": float, "longitude": float}；payload 缺失或无 location 时返回 None
    """
    payload_raw = captured.get("request_body")
    if not payload_raw:
        logger.warning("未捕获到请求 payload，无法提取经纬度")
        return None

    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError as e:
        logger.warning("请求 payload JSON 解析失败: %s", e)
        return None

    location = payload.get("location")
    if not isinstance(location, dict):
        logger.warning("payload 中缺少 location 字段")
        return None

    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if latitude is None or longitude is None:
        logger.warning("payload location 中缺少经纬度")
        return None

    logger.info("从请求 payload 提取经纬度: %s, %s", latitude, longitude)
    return {"latitude": latitude, "longitude": longitude}


def analyze_captures(captures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    从多次 reverseGeocode 捕获中选出最终结果并检测入参不一致。

    - 取列表末尾（即时间最新的）作为最终捕获；
    - 对每次捕获提取请求 payload 中的 location 经纬度，若存在 ≥2 个互不相同的经纬度，
      则判定为入参不一致；
    - 经纬度缺失的捕获不参与不一致比较。

    Args:
        captures: Interceptor.captures，按到达顺序排列

    Returns:
        {"latest": dict, "count": int, "inconsistent": bool}

    Raises:
        RuntimeError: 捕获列表为空
    """
    if not captures:
        raise RuntimeError("未捕获到任何请求")

    latest = captures[-1]
    distinct_locations = set()
    for c in captures:
        loc = extract_request_location(c)
        if loc is not None:
            distinct_locations.add((loc["latitude"], loc["longitude"]))

    inconsistent = len(distinct_locations) > 1
    logger.info(
        "捕获分析: 共 %d 次，不同经纬度 %d 个，%s",
        len(captures),
        len(distinct_locations),
        "入参不一致" if inconsistent else "入参一致",
    )

    return {
        "latest": latest,
        "count": len(captures),
        "inconsistent": inconsistent,
    }


def simplify_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    精简 reverseGeocode 响应，移除无用字段并裁剪 pois

    精简规则:
      - 移除顶层 aois、roads、intersections、returnDesc
      - pois 按 distance 升序排序，仅保留至多 2 个（distance 最小者）
      - addressComponent 中移除 streetNumber、adminCode 及嵌套 city.cityId

    Args:
        data: 解析后的原始 JSON 响应

    Returns:
        精简后的数据字典（深拷贝，不修改入参）
    """
    simplified = copy.deepcopy(data)
    logger.info("精简响应数据...")

    # 1. 移除顶层无用字段
    for key in _UNUSED_TOP_KEYS:
        simplified.pop(key, None)

    # 2. 裁剪 pois：按 distance 升序取至多 _MAX_POIS 个
    pois = simplified.get("pois")
    if isinstance(pois, list):
        sorted_pois = sorted(
            pois,
            key=lambda p: p.get("distance", float("inf")),
        )
        simplified["pois"] = sorted_pois[:_MAX_POIS]
        logger.info("pois 裁剪: %d -> %d", len(pois), len(simplified["pois"]))

    # 3. 移除 addressComponent 中的无用字段（含嵌套 city.cityId）
    ac = simplified.get("addressComponent")
    if isinstance(ac, dict):
        for key in _UNUSED_ADDRESS_COMPONENT_KEYS:
            ac.pop(key, None)
        city = ac.get("city")
        if isinstance(city, dict):
            city.pop("cityId", None)

    return simplified


def save_result(data: Dict[str, Any], output_file: str) -> None:
    """
    将捕获的数据保存到 JSON 文件

    Args:
        data: 要保存的 JSON 数据
        output_file: 输出文件路径
    """
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("数据已保存到 %s", output_file)


def format_result(
    address: str,
    location: Optional[Dict[str, float]],
    output_file: Optional[str],
    warning: Optional[str] = None,
) -> str:
    """
    格式化最终标准输出文本。

    输出顺序：用户当前地址 → 纬度/经度（各有中英文标注，若有）→ 警告（若有）→ 详细数据文件路径（若指定 --output）。
    未捕获到经纬度时省略经纬度行；未指定 --output 时不输出文件路径行；
    未发生入参不一致时 warning 为 None，省略警告行。

    Args:
        address: 用户当前地址（addressDescription）
        location: 请求 payload 中提取的经纬度 {"latitude", "longitude"}，无则为 None
        output_file: --output 指定时的输出文件路径，未指定为 None
        warning: 多次调用且入参不一致时的警告文本，无则为 None

    Returns:
        多行标准输出文本
    """
    lines = [f"用户当前地址: {address}"]
    if location is not None:
        lines.append(f"纬度(latitude): {location['latitude']}")
        lines.append(f"经度(longitude): {location['longitude']}")
    if warning:
        lines.append(warning)
    if output_file:
        lines.append(
            f"详细数据已保存到 {output_file}（包含省市区行政区划、附近 POI 等信息）"
        )
    return "\n".join(lines)
