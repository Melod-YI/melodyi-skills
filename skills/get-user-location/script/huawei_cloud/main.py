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
from .config import build_config, validate_env
from .extractor import extract_data, save_result, validate_response
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
      7. 保存结果
    """
    # 1. 解析参数 & 校验环境变量（先于日志配置，需要 verbose 参数）
    missing = validate_env()
    if missing:
        print("✗ 未设置以下环境变量：", file=sys.stderr)
        for m in missing:
            print(m, file=sys.stderr)
        print("请在系统环境变量中配置后重新运行", file=sys.stderr)
        sys.exit(1)

    config = build_config(argv)
    setup_logging(config.verbose)

    logger.info("=== 华为云空间 - 查找设备定位数据提取 ===")
    logger.info("模式: %s", "有头浏览器" if config.headed else "无头浏览器")
    logger.info("输出: %s", config.output_file)

    # 确保输出目录存在
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
            context = await browser.new_context()
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

            # 7. 保存结果
            save_result(raw_data, config.output_file)

            # 输出最终结果
            print(f"用户当前地址: {result['address']}")
            print(f"完整数据已保存到 {config.output_file}")
            logger.info("浏览器已关闭")

            await context.close()
        finally:
            await browser.close()
            logger.info("浏览器已关闭")
