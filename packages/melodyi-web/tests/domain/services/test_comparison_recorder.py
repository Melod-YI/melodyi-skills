"""ComparisonRecorder 单元测试"""

import pytest
import tempfile
import os
from datetime import datetime
from melodyi_web.domain.services.comparison_recorder import ComparisonRecorder, generate_session_id
from melodyi_web.infrastructure.database.database_manager import DatabaseManager
from melodyi_web.infrastructure.config.config_schema import DatabaseConfig
from melodyi_web.providers.search.base_provider import ProviderSearchRequest, ProviderSearchResult, SearchResultItem


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


class TestWriteSession:
    """write_session() 方法测试 (COMP-03)"""

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

    def test_write_session_success(self, recorder, temp_db):
        """Test 1: write_session() 成功写入 comparison_sessions 表"""
        session_id = recorder.generate_session_id()
        request = ProviderSearchRequest(
            query="test query",
            max_results=10,
            time_range=None,
            include_domains=None,
            exclude_domains=None,
            language="zh"
        )

        recorder.write_session(session_id, request)

        # 验证写入
        conn = temp_db.get_connection()
        result = conn.execute(
            "SELECT session_id, query, params FROM comparison_sessions WHERE session_id=?",
            (session_id,)
        ).fetchone()
        conn.close()

        assert result is not None
        assert result[0] == session_id
        assert result[1] == "test query"

    def test_write_session_with_params(self, recorder, temp_db):
        """Test 2: write_session() 正确序列化 params (COMP-03)"""
        session_id = recorder.generate_session_id()
        request = ProviderSearchRequest(
            query="test query with params",
            max_results=20,
            time_range=None,
            include_domains=["example.com", "test.org"],
            exclude_domains=["spam.com"],
            language="en"
        )

        recorder.write_session(session_id, request)

        # 验证 params JSON
        import json
        conn = temp_db.get_connection()
        result = conn.execute(
            "SELECT params FROM comparison_sessions WHERE session_id=?",
            (session_id,)
        ).fetchone()
        conn.close()

        params_dict = json.loads(result[0])
        assert params_dict["max_results"] == 20
        assert params_dict["include_domains"] == ["example.com", "test.org"]
        assert params_dict["exclude_domains"] == ["spam.com"]
        assert params_dict["language"] == "en"


class TestWriteProviderResult:
    """write_provider_result() 方法测试 (COMP-05)"""

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

    @pytest.fixture
    def sample_session(self, recorder, temp_db):
        """创建 sample session"""
        session_id = recorder.generate_session_id()
        request = ProviderSearchRequest(query="test", max_results=10)
        recorder.write_session(session_id, request)
        return session_id

    def test_write_provider_result_success(self, recorder, temp_db, sample_session):
        """Test 1: write_provider_result() 成功写入 provider_results 表"""
        result = ProviderSearchResult(
            provider="test_provider",
            results=[],
            response_time_ms=150,
            error=None
        )

        recorder.write_provider_result(sample_session, result)

        # 验证写入
        conn = temp_db.get_connection()
        row = conn.execute(
            "SELECT session_id, provider, response_time_ms, results_count, status FROM provider_results WHERE session_id=?",
            (sample_session,)
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == sample_session
        assert row[1] == "test_provider"
        assert row[2] == 150
        assert row[3] == 0  # results_count
        assert row[4] == "success"

    def test_write_provider_result_with_error(self, recorder, temp_db, sample_session):
        """Test 2: write_provider_result() 正确记录错误"""
        result = ProviderSearchResult(
            provider="error_provider",
            results=[],
            response_time_ms=200,
            error="Connection timeout"
        )

        recorder.write_provider_result(sample_session, result)

        # 验证错误信息
        conn = temp_db.get_connection()
        row = conn.execute(
            "SELECT status, error_message FROM provider_results WHERE session_id=? AND provider=?",
            (sample_session, "error_provider")
        ).fetchone()
        conn.close()

        assert row[0] == "error"
        assert row[1] == "Connection timeout"

    def test_write_provider_result_with_results_count(self, recorder, temp_db, sample_session):
        """Test 3: write_provider_result() 正确记录 results_count"""
        items = [
            SearchResultItem(title="result 1", url="https://example.com/1", description="desc 1"),
            SearchResultItem(title="result 2", url="https://example.com/2", description="desc 2"),
            SearchResultItem(title="result 3", url="https://example.com/3", description="desc 3"),
        ]
        result = ProviderSearchResult(
            provider="success_provider",
            results=items,
            response_time_ms=300,
            error=None
        )

        recorder.write_provider_result(sample_session, result)

        # 验证 results_count
        conn = temp_db.get_connection()
        row = conn.execute(
            "SELECT results_count FROM provider_results WHERE session_id=? AND provider=?",
            (sample_session, "success_provider")
        ).fetchone()
        conn.close()

        assert row[0] == 3


class TestWriteSearchResults:
    """write_search_results() 方法测试 (COMP-01, COMP-04)"""

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

    @pytest.fixture
    def sample_session(self, recorder, temp_db):
        """创建 sample session"""
        session_id = recorder.generate_session_id()
        request = ProviderSearchRequest(query="test", max_results=10)
        recorder.write_session(session_id, request)
        return session_id

    def test_write_search_results_success(self, recorder, temp_db, sample_session):
        """Test 1: write_search_results() 成功写入 search_results 表"""
        items = [
            SearchResultItem(title="result 1", url="https://example.com/1", description="desc 1"),
        ]

        recorder.write_search_results(sample_session, "test_provider", items)

        # 验证写入
        conn = temp_db.get_connection()
        row = conn.execute(
            "SELECT session_id, provider, title, url, description FROM search_results WHERE session_id=?",
            (sample_session,)
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == sample_session
        assert row[1] == "test_provider"
        assert row[2] == "result 1"
        assert row[3] == "https://example.com/1"
        assert row[4] == "desc 1"

    def test_write_search_results_rank_correct(self, recorder, temp_db, sample_session):
        """Test 2: write_search_results() 正确生成 rank (COMP-04)"""
        items = [
            SearchResultItem(title="result 1", url="https://example.com/1", description="desc 1"),
            SearchResultItem(title="result 2", url="https://example.com/2", description="desc 2"),
            SearchResultItem(title="result 3", url="https://example.com/3", description="desc 3"),
        ]

        recorder.write_search_results(sample_session, "rank_provider", items)

        # 验证 rank
        conn = temp_db.get_connection()
        rows = conn.execute(
            "SELECT rank, title FROM search_results WHERE session_id=? ORDER BY rank",
            (sample_session,)
        ).fetchall()
        conn.close()

        assert len(rows) == 3
        assert rows[0][0] == 1  # rank=1
        assert rows[1][0] == 2  # rank=2
        assert rows[2][0] == 3  # rank=3

    def test_write_search_results_full_data(self, recorder, temp_db, sample_session):
        """Test 3: write_search_results() 记录完整结果数据 (COMP-01)"""
        items = [
            SearchResultItem(
                title="Full Data Test",
                url="https://fulldata.example.com/article",
                description="Complete description with details",
                published_date=datetime(2026, 5, 9, 10, 30, 0),
                source_domain="fulldata.example.com"
            ),
        ]

        recorder.write_search_results(sample_session, "full_provider", items)

        # 验证完整数据
        conn = temp_db.get_connection()
        row = conn.execute(
            "SELECT title, url, description, published_date, source_domain FROM search_results WHERE session_id=?",
            (sample_session,)
        ).fetchone()
        conn.close()

        assert row[0] == "Full Data Test"
        assert row[1] == "https://fulldata.example.com/article"
        assert row[2] == "Complete description with details"
        assert row[3] == "2026-05-09T10:30:00"  # ISO 8601 格式
        assert row[4] == "fulldata.example.com"


class TestPersistenceFailureHandling:
    """持久化失败处理测试 (D-04)"""

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

    def test_write_session_no_exception_on_invalid_session_id(self, recorder):
        """Test 4: 持久化失败时记录 ERROR 日志，不抛出异常 (D-04)"""
        # 使用无效 session_id (违反主键约束)
        session_id = recorder.generate_session_id()
        request = ProviderSearchRequest(query="test", max_results=10)

        # 第一次写入成功
        recorder.write_session(session_id, request)

        # 第二次写入相同 session_id (违反主键约束)
        # 应记录 ERROR 日志但不抛出异常
        recorder.write_session(session_id, request)

        # 验证没有抛出异常，测试继续执行
        assert True