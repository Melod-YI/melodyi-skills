"""错误类型和指导测试"""

import pytest
from melodyi_search.domain.models.error import (
    ErrorType,
    ERROR_GUIDANCE,
    create_error_with_guidance
)


class TestErrorType:
    """ErrorType 枚举测试"""

    def test_all_error_types_exist(self):
        """测试所有错误类型存在"""
        expected_types = [
            "API_KEY_INVALID",
            "RATE_LIMITED",
            "QUOTA_EXCEEDED",
            "NETWORK_ERROR",
            "TIMEOUT",
            "INVALID_REQUEST",
            "DOMAIN_FILTER_UNSUPPORTED",
            "TIME_FILTER_UNSUPPORTED",
            "REGION_MISMATCH",
        ]
        for t in expected_types:
            assert hasattr(ErrorType, t)

    def test_error_type_values(self):
        """测试错误类型值"""
        assert ErrorType.API_KEY_INVALID.value == "API_KEY_INVALID"
        assert ErrorType.RATE_LIMITED.value == "RATE_LIMITED"


class TestErrorGuidance:
    """错误指导测试"""

    def test_api_key_invalid_guidance(self):
        """测试 API_KEY_INVALID 指导"""
        guidance = ERROR_GUIDANCE[ErrorType.API_KEY_INVALID]
        assert "API 密钥" in guidance
        assert "检查" in guidance

    def test_rate_limited_guidance(self):
        """测试 RATE_LIMITED 指导"""
        guidance = ERROR_GUIDANCE[ErrorType.RATE_LIMITED]
        assert "限流" in guidance
        assert "重试" in guidance or "切换" in guidance

    def test_create_error_with_guidance(self):
        """测试创建带指导的错误"""
        error = create_error_with_guidance(
            error_type=ErrorType.RATE_LIMITED,
            original_message="429 Too Many Requests"
        )
        assert error.error_type == "RATE_LIMITED"
        assert error.original_message == "429 Too Many Requests"
        assert "限流" in error.guidance