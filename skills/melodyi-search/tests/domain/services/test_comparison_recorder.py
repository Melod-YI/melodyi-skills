"""ComparisonRecorder 单元测试"""

import pytest
import tempfile
import os
from datetime import datetime
from melodyi_search.domain.services.comparison_recorder import ComparisonRecorder, generate_session_id
from melodyi_search.infrastructure.database.database_manager import DatabaseManager
from melodyi_search.infrastructure.config.config_schema import DatabaseConfig
from melodyi_search.providers.base_provider import ProviderSearchRequest, ProviderSearchResult, SearchResultItem


class TestComparisonRecorder:
    """ComparisonRecorder 单元测试"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        config = DatabaseConfig(database_path=db_path)
        manager = DatabaseManager(config)
        manager.init_database()
        yield manager
        os.unlink(db_path)

    @pytest.fixture
    def recorder(self, temp_db):
        """创建 recorder 实例"""
        return ComparisonRecorder(temp_db)

    def test_comparison_recorder_can_be_initialized(self, temp_db):
        """Test 1: ComparisonRecorder 类可被初始化"""
        recorder = ComparisonRecorder(temp_db)
        assert recorder is not None
        assert recorder._db == temp_db

    def test_generate_session_id_format(self, recorder):
        """Test 2: session_id 格式为 YYYYMMDD-HHMMSS-XXXX (D-03)"""
        session_id = recorder.generate_session_id()

        # 格式验证: YYYYMMDD-HHMMSS-XXXX
        assert session_id.count('-') == 2
        parts = session_id.split('-')

        # YYYYMMDD: 8位数字
        assert len(parts[0]) == 8
        assert parts[0].isdigit()

        # HHMMSS: 6位数字
        assert len(parts[1]) == 6
        assert parts[1].isdigit()

        # XXXX: 4位十六进制
        assert len(parts[2]) == 4
        assert all(c in '0123456789abcdef' for c in parts[2])

    def test_generate_session_id_includes_timestamp_prefix(self, recorder):
        """Test 3: session_id 包含时间戳前缀"""
        session_id = recorder.generate_session_id()

        # 时间戳前缀验证
        now = datetime.now()
        expected_prefix = now.strftime("%Y%m%d")
        actual_prefix = session_id.split('-')[0]

        assert actual_prefix == expected_prefix

    def test_generate_session_id_has_random_suffix(self, recorder):
        """验证 session_id 包含 4 位十六进制随机数"""
        # 生成多个 session_id 验证随机性
        session_ids = [recorder.generate_session_id() for _ in range(10)]
        suffixes = [sid.split('-')[2] for sid in session_ids]

        # 所有 suffix 都应是 4 位十六进制
        for suffix in suffixes:
            assert len(suffix) == 4
            assert all(c in '0123456789abcdef' for c in suffix)

        # 应有一定随机性（不太可能全部相同）
        assert len(set(suffixes)) > 1


class TestSessionIdFormat:
    """session_id 格式验证测试 (独立函数测试)"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        config = DatabaseConfig(database_path=db_path)
        manager = DatabaseManager(config)
        manager.init_database()
        yield manager
        os.unlink(db_path)

    @pytest.fixture
    def recorder(self, temp_db):
        """创建 recorder 实例"""
        return ComparisonRecorder(temp_db)

    def test_session_id_total_length(self, recorder):
        """验证 session_id 总长度"""
        session_id = recorder.generate_session_id()
        # YYYYMMDD-HHMMSS-XXXX = 8 + 1 + 6 + 1 + 4 = 20
        assert len(session_id) == 20