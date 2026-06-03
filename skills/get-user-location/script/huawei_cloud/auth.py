"""
登录认证模块

职责:
  - 导航至华为云空间首页
  - 在 iframe 中填写登录凭据（模拟人工操作的随机延迟）
  - 提交登录并验证登录状态
"""

import logging
import random

from playwright.async_api import Page

from .config import HUAWEI_CLOUD_URL

logger = logging.getLogger(__name__)


def _random_delay(min_ms: int, max_ms: int) -> int:
    """生成随机延迟毫秒数"""
    return random.randint(min_ms, max_ms)


async def navigate_to_home(page: Page) -> None:
    """打开华为云空间首页"""
    logger.info("正在打开浏览器...")
    await page.goto(HUAWEI_CLOUD_URL)
    logger.info("页面已加载: %s", HUAWEI_CLOUD_URL)


async def wait_for_iframe(page: Page) -> None:
    """等待登录 iframe 加载（随机 2~5 秒）"""
    delay = _random_delay(2000, 5000)
    logger.info("等待 iframe 加载 (%.1f 秒)...", delay / 1000)
    await page.wait_for_timeout(delay)


async def fill_login_form(page: Page, username: str, password: str) -> None:
    """
    填写登录表单并提交

    各步骤间加入随机等待，模拟人工操作节奏。
    """
    logger.info("正在登录...")

    # Playwright Python 使用 frame_locator 定位 iframe
    frame = page.frame_locator("#frameAddress")

    # 随机等待 1~3 秒
    await page.wait_for_timeout(_random_delay(1000, 3000))

    # 填写用户名
    username_input = frame.get_by_role("textbox", name="手机号/邮件地址/账号名")
    await username_input.click()
    await page.wait_for_timeout(_random_delay(300, 1000))
    await username_input.fill(username)
    logger.debug("用户名已填写")

    # 随机等待 0.5~2 秒
    await page.wait_for_timeout(_random_delay(500, 2000))

    # 填写密码
    password_input = frame.get_by_role("textbox", name="密码")
    await password_input.click()
    await page.wait_for_timeout(_random_delay(300, 1000))
    await password_input.fill(password)
    logger.debug("密码已填写")

    # 随机等待 0.5~1.5 秒
    await page.wait_for_timeout(_random_delay(500, 1500))

    # 点击登录按钮
    await frame.locator("span").filter(has_text="登录").nth(4).click()
    logger.info("登录已提交")


async def verify_login(page: Page) -> None:
    """
    验证登录状态

    通过检测 .warpHome.mobile 元素是否存在来判断登录是否成功。
    """
    logger.info("等待登录跳转...")
    await page.wait_for_timeout(5000)

    logger.info("验证登录状态...")
    count = await page.locator(".warpHome.mobile").count()

    if count == 0:
        logger.error("登录失败，未检测到服务图标")
        raise RuntimeError("登录失败，未检测到服务图标。请检查凭据或网络。")

    logger.info("登录成功")
