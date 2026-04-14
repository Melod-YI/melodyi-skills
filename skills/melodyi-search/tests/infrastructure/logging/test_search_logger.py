"""搜索日志器测试"""

import pytest
import tempfile
import os
from datetime import datetime
from melodyi_search.infrastructure.logging.search_logger import SearchLogger


class TestSearchLogger:
    """SearchLogger 测试类"""

    def test_create_logger(self):
        """测试创建日志器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with SearchLogger(log_dir=tmpdir) as logger:
                assert logger is not None

    def test_log_search_request(self):
        """测试记录搜索请求"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with SearchLogger(log_dir=tmpdir) as logger:
                logger.log_search_request(
                    query="python tutorial",
                    max_results=10,
                    time_range="day"
                )
            # 检查日志文件存在（按日期命名）
            date_str = datetime.now().strftime('%Y-%m-%d')
            log_file = os.path.join(tmpdir, f"search_{date_str}.log")
            assert os.path.exists(log_file)

    def test_log_provider_result(self):
        """测试记录提供商结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with SearchLogger(log_dir=tmpdir) as logger:
                logger.log_provider_result(
                    provider="minimax-cn",
                    status="success",
                    time_ms=850,
                    results_count=8
                )

    def test_log_search_result(self):
        """测试记录完整结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with SearchLogger(log_dir=tmpdir) as logger:
                logger.log_search_result(
                    title="Test Result",
                    url="https://example.com",
                    description="test description"
                )

    def test_log_error(self):
        """测试记录错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with SearchLogger(log_dir=tmpdir) as logger:
                logger.log_error(
                    provider="brave",
                    error_type="RATE_LIMITED",
                    message="Too many requests",
                    guidance="请等待后重试"
                )