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