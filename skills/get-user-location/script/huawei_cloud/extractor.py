"""
数据提取模块

职责:
  - 从拦截器捕获的原始数据中提取结构化信息
  - 验证响应有效性（returnCode == "0"）
  - 保存结果到 JSON 文件
"""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def extract_data(captured: Dict[str, Any]) -> Dict[str, Any]:
    """
    从拦截器捕获的原始数据中提取 JSON 响应体

    Args:
        captured: Interceptor.captured 原始数据

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
