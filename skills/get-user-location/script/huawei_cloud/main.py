"""
主流程编排模块

职责:
  - 串联各模块完成完整流程
  - 统一日志配置
  - 异常处理与资源清理
"""

import logging
import os
import sys
from typing import List, Optional

from playwright.async_api import async_playwright

from .auth import fill_login_form, navigate_to_home, verify_login, wait_for_iframe
from .browser import launch_browser
from .config import build_config, parse_args, validate_credentials
from .extractor import (
    extract_data,
    extract_request_location,
    format_result,
    save_result,
    simplify_response,
    validate_response,
)
from .interceptor import Interceptor, click_find_device, wait_for_data

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """配置日志格式和级别"""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def run(argv: Optional[List[str]] = None) -> None:
    """
    主执行流程

    流程步骤:
      1. 解析参数 & 校验环境变量
      2. 启动浏览器
      3. 导航至华为云首页 & 登录
      4. 注册网络拦截器
      5. 点击"查找设备"触发请求
      6. 提取并验证数据
      7. 输出结果（指定 --output 时保存 JSON）
    """
    # 1. 解析参数 & 校验凭据（先于日志配置，需要 verbose 参数）
    args = parse_args(argv)
    missing = validate_credentials(args.config)
    if missing:
        print("✗ 未配置以下凭据：", file=sys.stderr)
        for m in missing:
            print(m, file=sys.stderr)
        print(
            "请通过环境变量 HUAWEI_USERNAME / HUAWEI_PASSWORD，"
            "或配置文件 ~/.melodyi-skills/get-user-location/config.json 配置后重新运行",
            file=sys.stderr,
        )
        sys.exit(1)

    config = build_config(args=args)
    setup_logging(config.verbose)

    logger.info("=== 华为云空间 - 查找设备定位数据提取 ===")
    logger.info("模式: %s", "有头浏览器" if config.headed else "无头浏览器")
    logger.info("输出: %s", config.output_file or "仅标准输出，不保存文件")

    # 确保输出目录存在（未指定 --output 时跳过，不保存文件）
    if config.output_dir:
        try:
            os.makedirs(config.output_dir, exist_ok=True)
        except OSError as e:
            print(f"✗ 无法创建输出目录: {config.output_dir} ({e})", file=sys.stderr)
            sys.exit(1)
        logger.info("输出目录: %s", config.output_dir)

    # 2~7. 启动浏览器并执行完整流程
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headed=config.headed)
        try:
            context = await browser.new_context(locale="zh-CN")
            page = await context.new_page()

            # 3. 导航 & 登录
            await navigate_to_home(page)
            await wait_for_iframe(page)
            await fill_login_form(page, config.username, config.password)
            await verify_login(page)

            # 4. 注册拦截器
            interceptor = Interceptor()
            await interceptor.register(page)

            # 5. 点击查找设备 & 等待数据
            await click_find_device(page)
            await wait_for_data(page)

            # 6. 提取 & 验证
            raw_data = extract_data(interceptor.captured)
            result = validate_response(raw_data)

            # 7. 精简并保存结果
            simplified = simplify_response(raw_data)
            # 注入请求 payload 中的查询经纬度（最真实准确的定位点）
            location = extract_request_location(interceptor.captured)
            if location is not None:
                simplified["location"] = location
            if config.output_file:
                save_result(simplified, config.output_file)

            # 输出最终结果
            print(format_result(result["address"], location, config.output_file))

            await context.close()
        finally:
            await browser.close()
            logger.info("浏览器已关闭")
