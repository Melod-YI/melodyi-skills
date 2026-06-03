"""
浏览器管理模块

职责:
  - 启动 Chromium 浏览器实例
  - 管理浏览器生命周期（配合 context manager 自动清理）
"""

import logging

from playwright.async_api import Browser, Playwright

logger = logging.getLogger(__name__)


async def launch_browser(playwright: Playwright, headed: bool = False) -> Browser:
    """
    启动 Chromium 浏览器

    Args:
        playwright: Playwright 实例
        headed: 是否显示浏览器窗口

    Returns:
        Browser 实例
    """
    logger.info("正在启动浏览器 [headed=%s]...", headed)

    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ]

    if not headed:
        # 使用新版无头模式，避免被网站检测
        args.append("--headless=new")
        browser = await playwright.chromium.launch(headless=False, args=args)
    else:
        browser = await playwright.chromium.launch(headless=False, args=args)

    logger.info("浏览器启动成功")
    return browser
