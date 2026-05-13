"""Fetch 执行策略

实现两种抓取执行模式：
- 正常模式：串行执行供应商，成功即返回，失败则回退
- 比对模式：第一个供应商立即返回，其余后台执行（Task 11 后实现）
"""

import logging
import threading
from typing import List, Callable, Optional

from melodyi_web.domain.models.fetch_result import FetchResult, FetchError
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
from melodyi_web.providers.fetch.base_fetch_provider import (
    BaseFetchProvider,
    ProviderFetchRequest,
    ProviderFetchResult,
)

logger = logging.getLogger(__name__)


class FetchExecutionStrategy:
    """Fetch 执行策略

    提供两种执行模式：
    - 正常模式：按顺序串行执行供应商，成功则立即返回，失败则回退到下一个
    - 比对模式：第一个供应商正常执行返回，剩余供应商在后台线程执行并记录日志
    """

    def __init__(self):
        """初始化执行策略"""
        self._comparison_results: dict = {}
        self._comparison_lock = threading.Lock()

    def execute_normal(
        self,
        providers: List[BaseFetchProvider],
        request: ProviderFetchRequest,
        on_provider_complete: Optional[Callable[[ProviderFetchResult], None]] = None
    ) -> FetchResult:
        """正常模式执行

        按顺序串行执行供应商，成功则立即返回，失败则回退到下一个供应商。
        所有供应商都失败则返回错误结果。

        Args:
            providers: 供应商列表
            request: 统一的抓取请求
            on_provider_complete: 每个供应商完成后的回调（可选）

        Returns:
            统一的抓取结果
        """
        if not providers:
            return self._create_empty_error_result("NO_PROVIDERS", "没有可用的供应商")

        errors: List[tuple] = []  # [(provider_name, error_message), ...]

        for provider in providers:
            provider_name = provider.name
            logger.debug(f"[FetchNormal] Trying provider: {provider_name}")

            try:
                result = provider.fetch(request)

                # 回调通知
                if on_provider_complete:
                    on_provider_complete(result)

                # 成功则立即返回
                if result.error is None:
                    logger.info(f"[FetchNormal] Provider {provider_name} succeeded")
                    return self._convert_to_unified_result(result)

                # 有错误，记录并继续
                logger.warning(f"[FetchNormal] Provider {provider_name} failed: {result.error}")
                errors.append((provider_name, result.error))

            except Exception as e:
                # 异常，记录并继续
                error_msg = str(e)
                logger.error(f"[FetchNormal] Provider {provider_name} raised exception: {error_msg}")
                errors.append((provider_name, error_msg))

        # 所有供应商都失败
        return self._create_all_failed_result(errors)

    def execute_comparison(
        self,
        providers: List[BaseFetchProvider],
        request: ProviderFetchRequest,
        recorder: ComparisonRecorder,
        on_provider_complete: Optional[Callable[[ProviderFetchResult], None]] = None
    ) -> FetchResult:
        """比对模式执行

        第一个供应商正常执行并返回，剩余供应商在后台线程执行并记录日志。
        使用 threading.Thread(daemon=False) 实现后台执行，并等待线程完成。

        注意：此方法需要 ComparisonRecorder 的 write_fetch_session 和
        write_fetch_provider_result 方法，这些方法将在 Task 11 中实现。

        Args:
            providers: 供应商列表
            request: 统一的抓取请求
            recorder: 数据持久化服务
            on_provider_complete: 每个供应商完成后的回调（可选，后台执行时也会调用）

        Returns:
            第一个供应商的结果（含 session_id）

        决策参考:
        - D-01: daemon=False + thread.join(timeout=10)
        - D-02: 每个供应商完成后立即写入数据库
        - COMP-06: 返回包含 session_id 的结果
        """
        # TODO: Task 11 后实现
        # 需要 ComparisonRecorder 的以下方法：
        # - write_fetch_session(session_id, request)
        # - write_fetch_provider_result(session_id, result)

        logger.warning("[FetchComparison] Comparison mode not yet implemented, using normal mode")
        result = self.execute_normal(providers, request, on_provider_complete)
        return result

    def _execute_background_providers(
        self,
        providers: List[BaseFetchProvider],
        request: ProviderFetchRequest,
        recorder: ComparisonRecorder,
        session_id: str,
        on_provider_complete: Optional[Callable[[ProviderFetchResult], None]] = None
    ) -> None:
        """后台执行剩余供应商

        Args:
            providers: 剩余供应商列表
            request: 统一的抓取请求
            recorder: 数据持久化服务
            session_id: 会话 ID
            on_provider_complete: 完成回调

        决策参考:
        - D-02: 每个供应商完成后立即写入数据库
        - D-04: 失败时日志记录继续执行
        """
        # TODO: Task 11 后实现
        for provider in providers:
            provider_name = provider.name
            try:
                logger.debug(f"[FetchComparison] Background executing provider: {provider_name}")
                result = provider.fetch(request)

                # D-02: 立即写入数据库
                # recorder.write_fetch_provider_result(session_id, result)

                # 回调通知
                if on_provider_complete:
                    on_provider_complete(result)

                # 记录结果
                with self._comparison_lock:
                    self._comparison_results[provider_name] = {
                        "status": "success" if result.error is None else "failed",
                        "time_ms": result.response_time_ms,
                        "content_length": len(result.content),
                        "error": result.error
                    }

                if result.error:
                    logger.info(f"[FetchComparison] Background provider {provider_name} failed: {result.error}")
                else:
                    logger.info(
                        f"[FetchComparison] Background provider {provider_name} succeeded: "
                        f"{result.response_time_ms}ms, {len(result.content)} chars"
                    )

            except Exception as e:
                error_msg = str(e)
                logger.error(f"[FetchComparison] Background provider {provider_name} raised exception: {error_msg}")
                # D-04: 继续执行下一个供应商
                with self._comparison_lock:
                    self._comparison_results[provider_name] = {
                        "status": "exception",
                        "time_ms": 0,
                        "content_length": 0,
                        "error": error_msg
                    }

    def _convert_to_unified_result(self, result: ProviderFetchResult) -> FetchResult:
        """将供应商原生结果转换为统一结果

        Args:
            result: 供应商原生结果

        Returns:
            统一的抓取结果
        """
        error = None
        if result.error:
            error = FetchError(
                error_type="PROVIDER_ERROR",
                original_message=result.error,
                guidance="供应商返回错误，请检查错误信息或尝试其他供应商"
            )

        return FetchResult(
            provider=result.provider,
            url=result.url,
            title=result.title,
            content=result.content,
            response_time_ms=result.response_time_ms,
            metadata=result.metadata,
            error=error
        )

    def _create_empty_error_result(self, error_type: str, message: str) -> FetchResult:
        """创建空错误结果

        Args:
            error_type: 错误类型
            message: 错误消息

        Returns:
            统一的抓取结果（带错误）
        """
        return FetchResult(
            provider="none",
            url="",  # 无法获取 URL
            content="",
            response_time_ms=0,
            error=FetchError(
                error_type=error_type,
                original_message=message,
                guidance=message
            )
        )

    def _create_all_failed_result(self, errors: List[tuple]) -> FetchResult:
        """创建所有供应商失败的结果

        Args:
            errors: 错误列表 [(provider_name, error_message), ...]

        Returns:
            统一的抓取结果（带错误）
        """
        # 汇总所有错误
        error_details = "; ".join(f"{name}: {msg}" for name, msg in errors)

        return FetchResult(
            provider="none",
            url="",  # 无法获取 URL
            content="",
            response_time_ms=0,
            error=FetchError(
                error_type="ALL_PROVIDERS_FAILED",
                original_message=error_details,
                guidance="所有供应商都失败了，请检查网络连接和API配置"
            )
        )

    def get_comparison_results(self) -> dict:
        """获取比对模式的结果汇总

        Returns:
            比对结果字典
        """
        with self._comparison_lock:
            return dict(self._comparison_results)