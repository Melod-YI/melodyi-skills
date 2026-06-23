"""执行策略

实现两种搜索执行模式：
- 正常模式：串行执行提供商，成功即返回，失败则回退
- 比对模式：第一个提供商立即返回，其余后台执行
"""

import logging
import threading
from typing import List, Callable, Optional
from melodyi_web.domain.models.search_result import UnifiedSearchResult, SearchError
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder
from melodyi_web.providers.search.base_provider import BaseProvider, ProviderSearchRequest, ProviderSearchResult

logger = logging.getLogger(__name__)


class ExecutionStrategy:
    """执行策略

    提供两种执行模式：
    - 正常模式：按顺序串行执行提供商，成功则立即返回，失败则回退到下一个
    - 比对模式：第一个提供商正常执行返回，剩余提供商在后台线程执行并记录日志
    """

    def __init__(self):
        """初始化执行策略"""
        self._comparison_results: dict = {}
        self._comparison_lock = threading.Lock()

    def execute_normal(
        self,
        providers: List[BaseProvider],
        request: ProviderSearchRequest,
        on_provider_complete: Optional[Callable[[ProviderSearchResult], None]] = None
    ) -> UnifiedSearchResult:
        """正常模式执行

        按顺序串行执行提供商，成功则立即返回，失败则回退到下一个提供商。
        所有提供商都失败则返回错误结果。

        Args:
            providers: 提供商列表
            request: 统一的搜索请求
            on_provider_complete: 每个提供商完成后的回调（可选）

        Returns:
            统一的搜索结果
        """
        if not providers:
            return self._create_empty_error_result("NO_PROVIDERS", "没有可用的提供商")

        errors: List[tuple] = []  # [(provider_name, error_message), ...]

        for provider in providers:
            provider_name = provider.name
            logger.debug(f"[Normal] Trying provider: {provider_name}")

            try:
                result = provider.search(request)

                # 回调通知
                if on_provider_complete:
                    on_provider_complete(result)

                # 成功则立即返回
                if result.error is None:
                    logger.info(f"[Normal] Provider {provider_name} succeeded")
                    return self._convert_to_unified_result(result)

                # 有错误，记录并继续
                logger.warning(f"[Normal] Provider {provider_name} failed: {result.error}")
                errors.append((provider_name, result.error))

            except Exception as e:
                # 异常，记录并继续
                error_msg = str(e)
                logger.error(f"[Normal] Provider {provider_name} raised exception: {error_msg}")
                errors.append((provider_name, error_msg))

        # 所有提供商都失败
        return self._create_all_failed_result(errors)

    def execute_comparison(
        self,
        providers: List[BaseProvider],
        request: ProviderSearchRequest,
        recorder: ComparisonRecorder,
        on_provider_complete: Optional[Callable[[ProviderSearchResult], None]] = None
    ) -> UnifiedSearchResult:
        """比对模式执行

        第一个提供商正常执行并返回，剩余提供商在后台线程执行并记录日志。
        使用 threading.Thread(daemon=False) 实现后台执行，并等待线程完成。

        Args:
            providers: 提供商列表
            request: 统一的搜索请求
            recorder: 数据持久化服务 (COMP-02)
            on_provider_complete: 每个提供商完成后的回调（可选，后台执行时也会调用）

        Returns:
            第一个提供商的结果（含 session_id）

        决策参考:
        - D-01: daemon=False + thread.join(timeout=10)
        - D-02: 每个供应商完成后立即写入数据库
        - COMP-06: 返回包含 session_id 的结果
        """
        if not providers:
            return self._create_empty_error_result("NO_PROVIDERS", "没有可用的提供商")

        # D-03: 生成 session_id
        session_id = recorder.generate_session_id()

        # 写入 session 元数据
        recorder.write_session(session_id, request)
        logger.info(f"[Comparison] Session created: {session_id}")

        first_provider = providers[0]
        remaining_providers = providers[1:]

        # 执行第一个提供商
        logger.debug(f"[Comparison] Executing first provider: {first_provider.name}")
        first_result = first_provider.search(request)

        # D-02: 立即写入第一个供应商结果
        recorder.write_provider_result(session_id, first_result)
        recorder.write_search_results(session_id, first_provider.name, first_result.results)

        # 回调通知
        if on_provider_complete:
            on_provider_complete(first_result)

        # 清空比对结果，准备新一轮比对
        with self._comparison_lock:
            self._comparison_results.clear()
            self._comparison_results[first_provider.name] = {
                "status": "success" if first_result.error is None else "failed",
                "time_ms": first_result.response_time_ms,
                "results_count": len(first_result.results),
                "error": first_result.error
            }

        # 剩余提供商在后台线程执行
        background_thread = None
        if remaining_providers:
            # D-01: daemon=False 确保线程完成写入
            background_thread = threading.Thread(
                target=self._execute_background_providers,
                args=(remaining_providers, request, recorder, session_id, on_provider_complete),
                daemon=False
            )
            background_thread.start()
            logger.debug(f"[Comparison] Started background thread for {len(remaining_providers)} providers")

        # D-01: 等待后台线程完成 (timeout=10)
        if background_thread:
            background_thread.join(timeout=10)
            if background_thread.is_alive():
                logger.warning(f"[Comparison] Background thread still alive after 10s timeout, proceeding anyway")

        # 转换并返回第一个提供商的结果
        unified_result = self._convert_to_unified_result(first_result)

        # COMP-06: 添加 session_id
        unified_result.session_id = session_id

        # 附加比对日志信息
        with self._comparison_lock:
            unified_result.comparison_log = {
                "mode": "comparison",
                "first_provider": first_provider.name,
                "background_providers": [p.name for p in remaining_providers]
            }

        return unified_result

    def _execute_background_providers(
        self,
        providers: List[BaseProvider],
        request: ProviderSearchRequest,
        recorder: ComparisonRecorder,
        session_id: str,
        on_provider_complete: Optional[Callable[[ProviderSearchResult], None]] = None
    ) -> None:
        """后台执行剩余提供商

        Args:
            providers: 剩余提供商列表
            request: 统一的搜索请求
            recorder: 数据持久化服务
            session_id: 会话 ID
            on_provider_complete: 完成回调

        决策参考:
        - D-02: 每个供应商完成后立即写入数据库
        - D-04: 失败时日志记录继续执行
        """
        for provider in providers:
            provider_name = provider.name
            try:
                logger.debug(f"[Comparison] Background executing provider: {provider_name}")
                result = provider.search(request)

                # D-02: 立即写入数据库
                recorder.write_provider_result(session_id, result)
                recorder.write_search_results(session_id, provider_name, result.results)

                # 回调通知
                if on_provider_complete:
                    on_provider_complete(result)

                # 记录结果
                with self._comparison_lock:
                    self._comparison_results[provider_name] = {
                        "status": "success" if result.error is None else "failed",
                        "time_ms": result.response_time_ms,
                        "results_count": len(result.results),
                        "error": result.error
                    }

                if result.error:
                    logger.info(f"[Comparison] Background provider {provider_name} failed: {result.error}")
                else:
                    logger.info(
                        f"[Comparison] Background provider {provider_name} succeeded: "
                        f"{result.response_time_ms}ms, {len(result.results)} results"
                    )

            except Exception as e:
                error_msg = str(e)
                logger.error(f"[Comparison] Background provider {provider_name} raised exception: {error_msg}")
                # D-04: 继续执行下一个供应商
                with self._comparison_lock:
                    self._comparison_results[provider_name] = {
                        "status": "exception",
                        "time_ms": 0,
                        "results_count": 0,
                        "error": error_msg
                    }

    def _convert_to_unified_result(self, result: ProviderSearchResult) -> UnifiedSearchResult:
        """将提供商原生结果转换为统一结果

        Args:
            result: 提供商原生结果

        Returns:
            统一的搜索结果
        """
        error = None
        if result.error:
            error = SearchError(
                error_type="PROVIDER_ERROR",
                original_message=result.error,
                guidance="提供商返回错误，请检查错误信息或尝试其他提供商"
            )

        return UnifiedSearchResult(
            provider=result.provider,
            response_time_ms=result.response_time_ms,
            results=result.results,
            error=error
        )

    def _create_empty_error_result(self, error_type: str, message: str) -> UnifiedSearchResult:
        """创建空错误结果

        Args:
            error_type: 错误类型
            message: 错误消息

        Returns:
            统一的搜索结果（带错误）
        """
        return UnifiedSearchResult(
            provider="none",
            response_time_ms=0,
            results=[],
            error=SearchError(
                error_type=error_type,
                original_message=message,
                guidance=message
            )
        )

    def _create_all_failed_result(self, errors: List[tuple]) -> UnifiedSearchResult:
        """创建所有提供商失败的结果

        Args:
            errors: 错误列表 [(provider_name, error_message), ...]

        Returns:
            统一的搜索结果（带错误）
        """
        # 汇总所有错误
        error_details = "; ".join(f"{name}: {msg}" for name, msg in errors)

        return UnifiedSearchResult(
            provider="none",
            response_time_ms=0,
            results=[],
            error=SearchError(
                error_type="ALL_PROVIDERS_FAILED",
                original_message=error_details,
                guidance="所有提供商都失败了，请检查网络连接和API配置"
            )
        )

    def get_comparison_results(self) -> dict:
        """获取比对模式的结果汇总

        Returns:
            比对结果字典
        """
        with self._comparison_lock:
            return dict(self._comparison_results)