"""
配置管理模块

职责:
  - CLI 参数解析（--headed, --output）
  - 环境变量校验（HUAWEI_USERNAME, HUAWEI_PASSWORD）
  - 路径规范化
  - 构建统一的运行时配置
"""

import argparse
import os
import tempfile
from dataclasses import dataclass
from typing import List, Optional

HUAWEI_CLOUD_URL = "https://cloud.huawei.com/home#/home"
OUTPUT_FILENAME = "reverse-geocode-response.json"


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


def validate_env() -> List[str]:
    """校验必需的环境变量，返回缺失变量描述列表"""
    missing = []
    if not os.environ.get("HUAWEI_USERNAME"):
        missing.append("  - HUAWEI_USERNAME（手机号/邮箱/账号名）")
    if not os.environ.get("HUAWEI_PASSWORD"):
        missing.append("  - HUAWEI_PASSWORD（密码）")
    return missing


def build_config(argv: Optional[List[str]] = None) -> Config:
    """从 CLI 参数和环境变量构建运行时配置"""
    args = parse_args(argv)

    output_dir = args.output if args.output else get_default_output_dir()
    output_file = f"{output_dir}/{OUTPUT_FILENAME}"

    return Config(
        headed=args.headed,
        verbose=args.verbose,
        output_dir=output_dir,
        output_file=output_file,
        username=os.environ["HUAWEI_USERNAME"],
        password=os.environ["HUAWEI_PASSWORD"],
    )
