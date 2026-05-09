"""对比数据记录服务 - ComparisonRecorder"""

import json
import logging
import random
from datetime import datetime
from typing import List, Optional

from melodyi_search.infrastructure.database.database_manager import DatabaseManager
from melodyi_search.providers.base_provider import (
    ProviderSearchRequest,
    ProviderSearchResult,
    SearchResultItem,
)


logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    """生成 Session ID (D-03)

    格式: YYYYMMDD-HHMMSS-XXXX
    - 时间戳前缀便于历史查询和日志追溯
    - 4 位十六进制随机数防止冲突

    Returns:
        str: 格式化的 session_id
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    random_suffix = ''.join(random.choices('0123456789abcdef', k=4))
    return f"{timestamp}-{random_suffix}"


class ComparisonRecorder:
    """对比数据记录服务

    负责:
    - Session ID 生成 (D-03)
    - 数据写入编排 (D-02)
    - 错误处理 (D-04)

    决策参考:
    - D-02: 每个供应商完成后立即写入数据库 (单条 autocommit)
    - D-03: Session ID 格式 YYYYMMDD-HHMMSS-XXXX
    - D-04: 持久化失败时记录 ERROR 日志，不抛出异常
    """

    def __init__(self, database_manager: DatabaseManager):
        """初始化 ComparisonRecorder

        Args:
            database_manager: 数据库管理器实例
        """
        self._db = database_manager
        logger.debug("ComparisonRecorder initialized")

    def generate_session_id(self) -> str:
        """生成 Session ID (D-03)

        格式: YYYYMMDD-HHMMSS-XXXX
        - 时间戳前缀便于历史查询和日志追溯
        - 4 位十六进制随机数防止冲突

        Returns:
            str: 格式化的 session_id
        """
        return generate_session_id()

    def write_session(self, session_id: str, request: ProviderSearchRequest) -> None:
        """写入 session 元数据

        D-02: 单条 autocommit
        D-04: 失败时日志记录继续执行

        Args:
            session_id: 会话 ID
            request: 搜索请求参数
        """
        conn = None
        try:
            params_json = json.dumps({
                "max_results": request.max_results,
                "time_range": request.time_range.range_type if request.time_range else None,
                "include_domains": request.include_domains,
                "exclude_domains": request.exclude_domains,
                "language": request.language
            }, ensure_ascii=False)

            conn = self._db.get_connection()
            logger.debug(f"Connection opened for write_session: {session_id}")
            conn.execute(
                """INSERT INTO comparison_sessions
                   (session_id, query, params, timestamp)
                   VALUES (?, ?, ?, ?)""",
                (session_id, request.query, params_json, datetime.now().timestamp())
            )
            conn.commit()
            logger.info(f"Session written: {session_id}")
        except Exception as e:
            logger.error(f"Failed to write session {session_id}: {e}")
            # D-04: 不抛出异常，继续执行
        finally:
            if conn:
                conn.close()
                logger.debug(f"Connection closed for write_session: {session_id}")

    def write_provider_result(self, session_id: str, result: ProviderSearchResult) -> None:
        """写入供应商结果

        D-02: 单条 autocommit
        D-04: 失败时日志记录继续执行

        记录: response_time_ms, results_count, error_type, error_message, status

        Args:
            session_id: 会话 ID
            result: 供应商执行结果
        """
        conn = None
        try:
            status = "success" if result.error is None else "error"
            error_type = None  # 可扩展为具体错误类型
            error_message = result.error

            conn = self._db.get_connection()
            logger.debug(f"Connection opened for write_provider_result: {session_id}/{result.provider}")
            conn.execute(
                """INSERT INTO provider_results
                   (session_id, provider, response_time_ms, results_count,
                    error_type, error_message, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, result.provider, result.response_time_ms,
                 len(result.results), error_type, error_message, status)
            )
            conn.commit()
            logger.info(f"Provider result written: {session_id}/{result.provider}")
        except Exception as e:
            logger.error(f"Failed to write provider result {session_id}/{result.provider}: {e}")
            # D-04: 不抛出异常，继续执行
        finally:
            if conn:
                conn.close()
                logger.debug(f"Connection closed for write_provider_result: {session_id}/{result.provider}")

    def write_search_results(self, session_id: str, provider: str, results: List[SearchResultItem]) -> None:
        """写入搜索结果详情

        COMP-01: 记录完整搜索结果 (title, url, description, published_date)
        COMP-04: 记录排序位置 rank 字段
        D-04: 失败时日志记录继续执行

        Args:
            session_id: 会话 ID
            provider: 供应商名称
            results: 搜索结果列表
        """
        conn = None
        try:
            conn = self._db.get_connection()
            logger.debug(f"Connection opened for write_search_results: {session_id}/{provider}")
            for rank, item in enumerate(results, start=1):
                conn.execute(
                    """INSERT INTO search_results
                       (session_id, provider, rank, title, url, description,
                        published_date, source_domain)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (session_id, provider, rank, item.title, item.url,
                     item.description,
                     item.published_date.isoformat() if item.published_date else None,
                     item.source_domain)
                )
            conn.commit()
            logger.info(f"Search results written: {session_id}/{provider} ({len(results)} items)")
        except Exception as e:
            logger.error(f"Failed to write search results {session_id}/{provider}: {e}")
            # D-04: 不抛出异常，继续执行
        finally:
            if conn:
                conn.close()
                logger.debug(f"Connection closed for write_search_results: {session_id}/{provider}")