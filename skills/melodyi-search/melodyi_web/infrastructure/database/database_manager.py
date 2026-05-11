"""数据库管理器 - SQLite 连接和表管理"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig


class DatabaseManager:
    """SQLite 数据库管理器

    负责:
    - 数据库文件创建和连接管理 (D-02: 每次操作新建连接)
    - 表结构初始化 (D-01: lazy initialization)
    - 索引创建
    """

    def __init__(self, config: DatabaseConfig):
        """初始化数据库管理器

        Args:
            config: 数据库配置，包含 database_path
        """
        self.config = config
        self.database_path = Path(config.database_path)
        self._logger = logging.getLogger("melodyi_web.database")

        # 确保数据目录存在
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._logger.debug(f"Database directory ensured: {self.database_path.parent}")

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接

        D-02: 每次操作新建连接，SQLite 轻量级场景无需连接池

        Returns:
            sqlite3.Connection: 数据库连接对象
        """
        conn = sqlite3.connect(str(self.database_path))
        # 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")
        self._logger.debug(f"Database connection opened: {self.database_path}")
        return conn

    def init_database(self) -> None:
        """初始化数据库 - 创建表结构和索引

        D-01: Lazy initialization，幂等操作，可重复执行
        D-05: 表命名使用 snake_case

        核心操作:
        - 创建 comparison_sessions 表 (会话元数据)
        - 创建 provider_results 表 (供应商执行结果)
        - 创建 search_results 表 (搜索结果详情)
        - 创建索引优化查询性能

        日志记录:
        - INFO: 初始化开始、完成
        - DEBUG: 表创建、索引创建
        - ERROR: 初始化失败
        """
        self._logger.info(f"Initializing database at {self.database_path}")

        conn = self.get_connection()
        try:
            self._create_tables(conn)
            self._create_indexes(conn)
            self._logger.info("Database initialization completed successfully")
        except Exception as e:
            self._logger.error(f"Database initialization failed: {e}")
            raise
        finally:
            conn.close()
            self._logger.debug("Database connection closed after initialization")

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """创建表结构

        表设计 (DB-02, DB-03, DB-04):
        - comparison_sessions: 对比执行会话，记录查询和参数
        - provider_results: 供应商执行结果，记录响应时间和错误
        - search_results: 搜索结果详情，记录标题、URL、摘要

        Args:
            conn: 数据库连接对象
        """
        # comparison_sessions 表 (DB-02)
        # 存储每次对比执行的元数据
        self._logger.debug("Creating table: comparison_sessions")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comparison_sessions (
                session_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                params TEXT NOT NULL,  -- JSON 格式存储请求参数
                timestamp REAL NOT NULL,  -- Unix timestamp
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # provider_results 表 (DB-03)
        # 存储每个供应商的执行结果和元数据
        self._logger.debug("Creating table: provider_results")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS provider_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                response_time_ms INTEGER NOT NULL,
                results_count INTEGER NOT NULL DEFAULT 0,
                error_type TEXT,  -- 可为空，成功时无错误类型
                error_message TEXT,  -- 可为空
                status TEXT NOT NULL,  -- 'success' 或 'error'
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (session_id) REFERENCES comparison_sessions(session_id)
            )
        """)

        # search_results 表 (DB-04)
        # 存储完整的搜索结果记录
        self._logger.debug("Creating table: search_results")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                rank INTEGER NOT NULL,  -- 排序位置
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                description TEXT,  -- 可为空
                published_date TEXT,  -- 可为空，ISO 8601 格式
                source_domain TEXT NOT NULL,  -- 从 URL 解析的域名
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (session_id) REFERENCES comparison_sessions(session_id)
            )
        """)

        conn.commit()
        self._logger.info("Tables created: comparison_sessions, provider_results, search_results")

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """创建索引

        索引设计 (优化查询性能):
        - comparison_sessions.timestamp: 时间范围查询
        - provider_results.session_id, provider: 会话和供应商筛选
        - search_results.session_id, provider, source_domain: 多维度查询

        Args:
            conn: 数据库连接对象
        """
        self._logger.debug("Creating indexes for comparison_sessions")
        # comparison_sessions 索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_timestamp
            ON comparison_sessions(timestamp)
        """)

        self._logger.debug("Creating indexes for provider_results")
        # provider_results 索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_provider_results_session_id
            ON provider_results(session_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_provider_results_provider
            ON provider_results(provider)
        """)

        self._logger.debug("Creating indexes for search_results")
        # search_results 索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_results_session_id
            ON search_results(session_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_results_provider
            ON search_results(provider)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_results_source_domain
            ON search_results(source_domain)
        """)

        conn.commit()
        self._logger.info("Indexes created: 6 indexes for query optimization")

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在

        Args:
            table_name: 表名称

        Returns:
            bool: 表是否存在
        """
        conn = self.get_connection()
        try:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            ).fetchone()
            exists = result is not None
            self._logger.debug(f"Table existence check: {table_name} -> {exists}")
            return exists
        finally:
            conn.close()

    def get_table_count(self) -> int:
        """获取已创建表数量

        Returns:
            int: 表数量（包含 sqlite 内部表）
        """
        conn = self.get_connection()
        try:
            result = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()
            count = result[0] if result else 0
            self._logger.debug(f"Table count: {count}")
            return count
        finally:
            conn.close()

    def get_index_count(self) -> int:
        """获取已创建索引数量

        Returns:
            int: 索引数量
        """
        conn = self.get_connection()
        try:
            result = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()
            count = result[0] if result else 0
            self._logger.debug(f"Index count: {count}")
            return count
        finally:
            conn.close()