"""
网络请求拦截模块

职责:
  - 注册 reverseGeocode 请求拦截器
  - 按到达顺序收集每次响应数据（URL、状态码、Headers、Body）与请求 payload（含查询经纬度）
  - 触发"查找设备"操作以产生目标请求
  - 静默期等待：收集短时间内可能发生的多次同一接口调用
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Page, Response

logger = logging.getLogger(__name__)


class Interceptor:
    """网络请求拦截器，按到达顺序收集所有 reverseGeocode 请求与响应"""

    def __init__(self):
        # 按到达顺序追加；列表末尾即时间最新的调用
        self.captures: List[Dict[str, Any]] = []

    async def _on_response(self, response: Response) -> None:
        """响应回调：当 URL 包含 reverseGeocode 时捕获请求 payload 与响应数据"""
        url = response.url
        if "reverseGeocode" not in url:
            return

        body = await response.text()
        # 请求 payload（POST body），含本次查询的经纬度，是最准确的定位点
        request_body = response.request.post_data

        self.captures.append(
            {
                "url": url,
                "status": response.status,
                "headers": response.headers,
                "body": body,
                "request_body": request_body,
            }
        )

        idx = len(self.captures)
        logger.info("已捕获第 %d 次 reverseGeocode 请求: %s (HTTP %d)", idx, url, response.status)
        if request_body:
            logger.info("  已捕获请求 payload")
        else:
            logger.warning("  第 %d 次请求未捕获到 payload", idx)

        # verbose（-v）下输出每次请求的时间、入参经纬度、返回地址描述（无论是否一致）
        self._log_request_detail(idx, request_body, body)

    def _log_request_detail(
        self, idx: int, request_body: Optional[str], body: str
    ) -> None:
        """记录单次请求的入参经纬度与返回地址描述（INFO 级别，仅 -v 可见）"""
        ts = time.strftime("%H:%M:%S")
        lat, lng = self._peek_location(request_body)
        addr = self._peek_address(body)
        logger.info(
            "  [%s] 第%d次: 纬度(latitude)=%s, 经度(longitude)=%s | 地址=%s",
            ts,
            idx,
            lat,
            lng,
            addr,
        )

    @staticmethod
    def _peek_location(request_body: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
        """从请求 payload 中取出经纬度（仅供日志展示，不参与核心逻辑）"""
        if not request_body:
            return None, None
        try:
            payload = json.loads(request_body)
        except json.JSONDecodeError:
            return None, None
        loc = payload.get("location")
        if not isinstance(loc, dict):
            return None, None
        return loc.get("latitude"), loc.get("longitude")

    @staticmethod
    def _peek_address(body: str) -> str:
        """从响应体中取出 addressDescription（仅供日志展示）"""
        if not body:
            return ""
        try:
            return str(json.loads(body).get("addressDescription", ""))
        except json.JSONDecodeError:
            return ""

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


async def wait_for_data(
    page: Page,
    interceptor: Interceptor,
    quiet_seconds: float = 3.0,
    max_wait_after_first: float = 15.0,
    first_timeout: float = 30.0,
) -> None:
    """
    等待 reverseGeocode 请求触发并收集短时间内可能发生的多次调用。

    采用静默期策略:
      1. 轮询等待首次捕获（first_timeout 秒内未出现则放弃，交由后续报错）；
      2. 首次捕获后，每 500ms 轮询；若捕获数增长则重置静默计时；
         连续 quiet_seconds 秒无新调用 -> 结束；
      3. 首次捕获后累计 max_wait_after_first 秒仍不静默 -> 强制结束（防止持续轮询）。

    Args:
        page: Playwright 页面
        interceptor: 已注册的拦截器，从中读取已收集的 captures
        quiet_seconds: 静默阈值，无新调用达该时长即结束
        max_wait_after_first: 首次捕获后的最长等待上限
        first_timeout: 等待首次捕获的超时
    """
    logger.info(
        "等待数据捕获（静默期策略: 首次后静默 %.1fs / 上限 %.1fs / 首次超时 %.1fs）",
        quiet_seconds,
        max_wait_after_first,
        first_timeout,
    )
    poll_ms = 500
    start = time.monotonic()

    # 阶段1: 等待首次捕获
    while not interceptor.captures:
        if time.monotonic() - start > first_timeout:
            logger.warning("等待首次捕获超时（%.1fs），未捕获到任何请求", first_timeout)
            return
        await page.wait_for_timeout(poll_ms)

    first_capture_at = time.monotonic()
    quiet_start = first_capture_at
    last_count = len(interceptor.captures)
    logger.info("首次捕获完成，进入静默期等待（累计 %d 次）", last_count)

    # 阶段2: 静默期 + 上限兜底
    while True:
        await page.wait_for_timeout(poll_ms)
        now = time.monotonic()
        count = len(interceptor.captures)
        if count != last_count:
            last_count = count
            quiet_start = now
            logger.info("检测到新调用（累计 %d 次），重置静默计时", count)
            continue
        if now - quiet_start >= quiet_seconds:
            logger.info("静默 %.1fs 无新调用，收集结束（共 %d 次）", quiet_seconds, count)
            return
        if now - first_capture_at >= max_wait_after_first:
            logger.info(
                "达到首次捕获后上限 %.1fs，强制结束（共 %d 次）",
                max_wait_after_first,
                count,
            )
            return
