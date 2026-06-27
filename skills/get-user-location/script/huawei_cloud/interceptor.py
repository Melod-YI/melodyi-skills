"""
网络请求拦截模块

职责:
  - 注册 reverseGeocode 请求拦截器
  - 捕获响应数据（URL、状态码、Headers、Body）
  - 捕获请求 payload（POST body，含查询经纬度）
  - 触发"查找设备"操作以产生目标请求
"""

import logging
from typing import Any, Dict, Optional

from playwright.async_api import Page, Response

logger = logging.getLogger(__name__)


class Interceptor:
    """网络请求拦截器，捕获 reverseGeocode 请求与响应"""

    def __init__(self):
        self.captured: Optional[Dict[str, Any]] = None

    async def _on_response(self, response: Response) -> None:
        """响应回调：当 URL 包含 reverseGeocode 时捕获请求 payload 与响应数据"""
        url = response.url
        if "reverseGeocode" not in url:
            return

        body = await response.text()
        # 请求 payload（POST body），含本次查询的经纬度，是最准确的定位点
        request_body = response.request.post_data

        self.captured = {
            "url": url,
            "status": response.status,
            "headers": response.headers,
            "body": body,
            "request_body": request_body,
        }

        logger.info("已捕获请求: %s (HTTP %d)", url, response.status)
        if request_body:
            logger.info("已捕获请求 payload")
        else:
            logger.warning("未捕获到请求 payload")

    async def register(self, page: Page) -> None:
        """注册 reverseGeocode 响应监听器"""
        logger.info("注册网络拦截器...")
        page.on("response", self._on_response)
        logger.info("拦截器已就绪")


async def click_find_device(page: Page) -> None:
    """点击"查找设备"图标"""
    logger.info("点击查找设备...")
    await page.locator(".warpHome.mobile .menuIcon").click()
    logger.info("已点击查找设备")


async def wait_for_data(page: Page) -> None:
    """等待页面跳转和请求触发"""
    logger.info("等待数据捕获...")
    await page.wait_for_timeout(5000)
