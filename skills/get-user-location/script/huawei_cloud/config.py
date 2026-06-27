"""
配置管理模块

职责:
  - CLI 参数解析（--headed, --output, --config）
  - 凭据读取：环境变量 HUAWEI_USERNAME/HUAWEI_PASSWORD 优先，回退到
    用户配置文件 ~/.melodyi-skills/get-user-location/config.json
  - 路径规范化
  - 构建统一的运行时配置

凭据优先级：环境变量 > 配置文件（与其他 melodyi skill 约定一致）。
配置文件格式（JSON，无需额外依赖）：
  {
    "huawei_username": "手机号/邮箱/账号名",
    "huawei_password": "密码"
  }
"""

import argparse
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

HUAWEI_CLOUD_URL = "https://cloud.huawei.com/home#/home"
OUTPUT_FILENAME = "reverse-geocode-response.json"

# 用户目录下的统一配置目录（与其他 melodyi skill 共用 ~/.melodyi-skills/ 根目录）
USER_CONFIG_DIR = Path.home() / ".melodyi-skills" / "get-user-location"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.json"


@dataclass
class Config:
    """运行时配置"""
    headed: bool
    verbose: bool
    output_dir: str
    output_file: str
    username: str
    password: str


def normalize_path(path: str) -> str:
    """路径规范化：Windows 反斜杠转正斜杠，去掉末尾斜杠"""
    return path.replace("\\", "/").rstrip("/")


def get_default_output_dir() -> str:
    """获取默认输出目录（系统临时目录）"""
    return normalize_path(tempfile.gettempdir())


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="华为云空间：一键完成 登录 → 拦截请求 → 点击查找设备 → 提取数据"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=False,
        help="使用有头模式（显示浏览器窗口）",
    )
    parser.add_argument(
        "--output",
        metavar="DIR",
        default=None,
        help="输出目录路径（默认使用系统临时目录）",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="配置文件路径（默认 ~/.melodyi-skills/get-user-location/config.json）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="显示详细日志输出",
    )
    args = parser.parse_args(argv)

    # 规范化输出路径
    if args.output is not None:
        args.output = normalize_path(args.output)

    return args


def load_config_file(config_path: Optional[str] = None) -> dict:
    """读取配置文件，返回字典；不存在或解析失败返回空 dict。

    优先级：CLI --config 指定路径 > 默认用户配置文件。
    """
    path = Path(config_path) if config_path else USER_CONFIG_FILE
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def resolve_credentials(config_path: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """解析华为账号凭据，优先级：环境变量 > 配置文件。

    Returns:
        (username, password)，未获取到的为 None
    """
    file_cfg = load_config_file(config_path)
    username = os.environ.get("HUAWEI_USERNAME") or file_cfg.get("huawei_username")
    password = os.environ.get("HUAWEI_PASSWORD") or file_cfg.get("huawei_password")
    return username, password


def validate_credentials(config_path: Optional[str] = None) -> List[str]:
    """校验凭据来源（环境变量或配置文件），返回缺失项描述列表"""
    missing = []
    username, password = resolve_credentials(config_path)
    if not username:
        missing.append("  - HUAWEI_USERNAME（手机号/邮箱/账号名）")
    if not password:
        missing.append("  - HUAWEI_PASSWORD（密码）")
    return missing


def build_config(
    argv: Optional[List[str]] = None,
    args: Optional[argparse.Namespace] = None,
) -> Config:
    """从 CLI 参数、环境变量与配置文件构建运行时配置

    凭据优先级：环境变量 > 配置文件（CLI --config 指定或默认用户配置）。
    """
    if args is None:
        args = parse_args(argv)

    output_dir = args.output if args.output else get_default_output_dir()
    output_file = f"{output_dir}/{OUTPUT_FILENAME}"

    username, password = resolve_credentials(args.config)
    if not username or not password:
        # 调用方应在 main.py 提前用 validate_credentials 校验并给出友好提示；
        # 此处兜底，避免凭据为 None 时后续流程报错。
        raise RuntimeError("缺少华为账号凭据：HUAWEI_USERNAME / HUAWEI_PASSWORD")

    return Config(
        headed=args.headed,
        verbose=args.verbose,
        output_dir=output_dir,
        output_file=output_file,
        username=username,
        password=password,
    )
