"""DatabaseManager 单元测试"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
from melodyi_web.infrastructure.database import DatabaseManager


class TestDatabaseManagerInit:
    """数据库管理器初始化测试"""

    def test_init_creates_database_directory(self, tmp_path):
        """验证初始化时创建数据目录"""
        # 使用临时目录
        db_path = tmp_path / "data" / "test.db"
        config = DatabaseConfig(database_path=str(db_path))

        # 目录不应存在
        assert not db_path.parent.exists()

        # 初始化管理器
        manager = DatabaseManager(config)

        # 目录应被创建
        assert db_path.parent.exists()

    def test_init_with_custom_path(self, tmp_path):
        """验证自定义路径配置"""
        custom_path = tmp_path / "custom" / "location" / "custom.db"
        config = DatabaseConfig(database_path=str(custom_path))
        manager = DatabaseManager(config)

        assert manager.database_path == custom_path


class TestDatabaseConnection:
    """数据库连接测试"""

    def test_get_connection_returns_valid_connection(self, tmp_path):
        """验证返回有效 sqlite3.Connection"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)

        conn = manager.get_connection()

        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_connection_foreign_keys_enabled(self, tmp_path):
        """验证外键约束启用"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)

        conn = manager.get_connection()
        result = conn.execute("PRAGMA foreign_keys").fetchone()
        conn.close()

        assert result[0] == 1  # 外键约束启用


class TestTableCreation:
    """表创建测试"""

    def test_init_database_creates_all_tables(self, tmp_path):
        """验证三张表创建 (DB-02, DB-03, DB-04)"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)

        manager.init_database()

        assert manager.table_exists("comparison_sessions")
        assert manager.table_exists("provider_results")
        assert manager.table_exists("search_results")

    def test_table_exists_returns_true_for_created_tables(self, tmp_path):
        """验证 table_exists 方法对已创建表返回 True"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)
        manager.init_database()

        assert manager.table_exists("comparison_sessions") is True
        assert manager.table_exists("provider_results") is True
        assert manager.table_exists("search_results") is True

    def test_table_exists_returns_false_for_nonexistent_tables(self, tmp_path):
        """验证 table_exists 方法对不存在表返回 False"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)
        manager.init_database()

        assert manager.table_exists("nonexistent_table") is False


class TestIndexCreation:
    """索引创建测试"""

    def test_init_database_creates_indexes(self, tmp_path):
        """验证索引创建"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)
        manager.init_database()

        conn = manager.get_connection()

        # 验证 comparison_sessions 索引
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_sessions_timestamp'"
        ).fetchone()
        assert result is not None

        # 验证 provider_results 索引
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_provider_results_session_id'"
        ).fetchone()
        assert result is not None

        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_provider_results_provider'"
        ).fetchone()
        assert result is not None

        # 验证 search_results 索引
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_search_results_session_id'"
        ).fetchone()
        assert result is not None

        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_search_results_provider'"
        ).fetchone()
        assert result is not None

        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_search_results_source_domain'"
        ).fetchone()
        assert result is not None

        conn.close()


class TestIdempotency:
    """幂等性测试"""

    def test_init_database_is_idempotent(self, tmp_path):
        """验证重复执行 init_database 不报错 (DB-05)"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)

        # 第一次初始化
        manager.init_database()

        # 第二次初始化 (不应报错)
        manager.init_database()

        # 第三次初始化
        manager.init_database()

        # 验证表仍然存在
        assert manager.table_exists("comparison_sessions")
        assert manager.table_exists("provider_results")
        assert manager.table_exists("search_results")

    def test_repeated_init_preserves_data(self, tmp_path):
        """验证重复初始化不丢失已有数据"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)

        # 初始化并插入测试数据
        manager.init_database()
        conn = manager.get_connection()
        conn.execute(
            "INSERT INTO comparison_sessions (session_id, query, params, timestamp) VALUES (?, ?, ?, ?)",
            ("test-session-1", "test query", "{}", 1700000000.0)
        )
        conn.commit()
        conn.close()

        # 重复初始化
        manager.init_database()

        # 验证数据仍然存在
        conn = manager.get_connection()
        result = conn.execute(
            "SELECT session_id FROM comparison_sessions WHERE session_id = ?",
            ("test-session-1",)
        ).fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "test-session-1"


class TestGetTableCount:
    """表计数测试"""

    def test_get_table_count_returns_correct_count(self, tmp_path):
        """验证 get_table_count 返回正确表数量"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)

        # 初始化前 (可能有 sqlite 内部表)
        manager.init_database()

        # 初始化后应有 3 张业务表
        count = manager.get_table_count()
        assert count >= 3


class TestTableSchema:
    """表结构验证测试"""

    def test_comparison_sessions_schema(self, tmp_path):
        """验证 comparison_sessions 表结构"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)
        manager.init_database()

        conn = manager.get_connection()
        result = conn.execute("PRAGMA table_info(comparison_sessions)").fetchall()
        conn.close()

        # 验证列存在
        column_names = [row[1] for row in result]
        assert "session_id" in column_names
        assert "query" in column_names
        assert "params" in column_names
        assert "timestamp" in column_names
        assert "created_at" in column_names

    def test_provider_results_schema(self, tmp_path):
        """验证 provider_results 表结构"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)
        manager.init_database()

        conn = manager.get_connection()
        result = conn.execute("PRAGMA table_info(provider_results)").fetchall()
        conn.close()

        column_names = [row[1] for row in result]
        assert "id" in column_names
        assert "session_id" in column_names
        assert "provider" in column_names
        assert "response_time_ms" in column_names
        assert "results_count" in column_names
        assert "error_type" in column_names
        assert "error_message" in column_names
        assert "status" in column_names
        assert "created_at" in column_names

    def test_search_results_schema(self, tmp_path):
        """验证 search_results 表结构"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)
        manager.init_database()

        conn = manager.get_connection()
        result = conn.execute("PRAGMA table_info(search_results)").fetchall()
        conn.close()

        column_names = [row[1] for row in result]
        assert "id" in column_names
        assert "session_id" in column_names
        assert "provider" in column_names
        assert "rank" in column_names
        assert "title" in column_names
        assert "url" in column_names
        assert "description" in column_names
        assert "published_date" in column_names
        assert "source_domain" in column_names
        assert "created_at" in column_names


class TestIndexCount:
    """索引计数测试"""

    def test_get_index_count_returns_correct_count(self, tmp_path):
        """验证 get_index_count 返回正确索引数量"""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(database_path=str(db_path))
        manager = DatabaseManager(config)
        manager.init_database()

        count = manager.get_index_count()
        assert count >= 6  # 至少 6 个业务索引