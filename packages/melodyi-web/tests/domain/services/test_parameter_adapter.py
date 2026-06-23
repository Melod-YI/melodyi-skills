"""ParameterAdapter 单元测试"""

import pytest
from unittest.mock import Mock
from melodyi_web.domain.models.search_request import UnifiedSearchRequest, TimeRange
from melodyi_web.domain.services.parameter_adapter import ParameterAdapter
from melodyi_web.providers.search.base_provider import BaseProvider


class TestParameterAdapter:
    """ParameterAdapter 测试类"""

    def _create_mock_provider(self, max_results_limit: int = 50) -> Mock:
        """创建模拟提供商

        Args:
            max_results_limit: 最大结果数限制

        Returns:
            Mock 提供商实例
        """
        provider = Mock(spec=BaseProvider)
        provider.get_max_results_limit.return_value = max_results_limit
        return provider

    def test_basic_parameter_passing(self):
        """测试基本参数传递"""
        # Arrange
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=10,
        )
        provider = self._create_mock_provider(max_results_limit=50)

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.query == "test query"
        assert result.max_results == 10
        assert result.time_range is None
        assert result.include_domains is None
        assert result.exclude_domains is None
        assert result.language is None
        assert result.native_params is None
        assert result.modified_query is None

    def test_max_results_within_limit(self):
        """测试 max_results 在限制范围内"""
        # Arrange
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=30,
        )
        provider = self._create_mock_provider(max_results_limit=50)

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.max_results == 30

    def test_max_results_exceeds_limit(self):
        """测试 max_results 超过限制时被截断"""
        # Arrange
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=100,
        )
        provider = self._create_mock_provider(max_results_limit=50)

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.max_results == 50

    def test_max_results_exactly_at_limit(self):
        """测试 max_results 正好等于限制"""
        # Arrange
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=50,
        )
        provider = self._create_mock_provider(max_results_limit=50)

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.max_results == 50

    def test_max_results_with_small_provider_limit(self):
        """测试提供商限制较小的情况"""
        # Arrange
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=10,
        )
        provider = self._create_mock_provider(max_results_limit=5)

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.max_results == 5

    def test_time_range_passing(self):
        """测试时间范围传递"""
        # Arrange
        time_range = TimeRange(range_type="week")
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=10,
            time_range=time_range,
        )
        provider = self._create_mock_provider()

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.time_range is not None
        assert result.time_range.range_type == "week"
        assert result.time_range.start_date is None
        assert result.time_range.end_date is None

    def test_time_range_with_exact_dates(self):
        """测试带精确日期的时间范围传递"""
        # Arrange
        from datetime import datetime
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        time_range = TimeRange(start_date=start, end_date=end)
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=10,
            time_range=time_range,
        )
        provider = self._create_mock_provider()

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.time_range is not None
        assert result.time_range.start_date == start
        assert result.time_range.end_date == end
        assert result.time_range.range_type is None

    def test_include_domains_passing(self):
        """测试包含域名传递"""
        # Arrange
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=10,
            include_domains=["example.com", "test.org"],
        )
        provider = self._create_mock_provider()

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.include_domains == ["example.com", "test.org"]

    def test_exclude_domains_passing(self):
        """测试排除域名传递"""
        # Arrange
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=10,
            exclude_domains=["spam.com", "ads.net"],
        )
        provider = self._create_mock_provider()

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.exclude_domains == ["spam.com", "ads.net"]

    def test_both_domain_filters_passing(self):
        """测试同时传递包含和排除域名"""
        # Arrange
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=10,
            include_domains=["good.com"],
            exclude_domains=["bad.com"],
        )
        provider = self._create_mock_provider()

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.include_domains == ["good.com"]
        assert result.exclude_domains == ["bad.com"]

    def test_language_passing(self):
        """测试语言参数传递"""
        # Arrange
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=10,
            language="zh-CN",
        )
        provider = self._create_mock_provider()

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.language == "zh-CN"

    def test_all_parameters_together(self):
        """测试所有参数同时传递"""
        # Arrange
        from datetime import datetime
        time_range = TimeRange(range_type="month")
        unified = UnifiedSearchRequest(
            query="comprehensive test",
            max_results=25,
            time_range=time_range,
            include_domains=["news.com"],
            exclude_domains=["spam.org"],
            language="en-US",
        )
        provider = self._create_mock_provider(max_results_limit=30)

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.query == "comprehensive test"
        assert result.max_results == 25  # 未超过限制
        assert result.time_range.range_type == "month"
        assert result.include_domains == ["news.com"]
        assert result.exclude_domains == ["spam.org"]
        assert result.language == "en-US"
        assert result.native_params is None
        assert result.modified_query is None

    def test_all_parameters_with_limit_clamping(self):
        """测试所有参数传递并限制 max_results"""
        # Arrange
        time_range = TimeRange(range_type="day")
        unified = UnifiedSearchRequest(
            query="limited test",
            max_results=100,
            time_range=time_range,
            include_domains=["source1.com"],
            exclude_domains=["source2.org"],
            language="ja",
        )
        provider = self._create_mock_provider(max_results_limit=20)

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.query == "limited test"
        assert result.max_results == 20  # 被限制到提供商上限
        assert result.time_range.range_type == "day"
        assert result.include_domains == ["source1.com"]
        assert result.exclude_domains == ["source2.org"]
        assert result.language == "ja"

    def test_default_max_results(self):
        """测试默认 max_results 值"""
        # Arrange
        unified = UnifiedSearchRequest(query="test query")  # max_results 默认为 10
        provider = self._create_mock_provider(max_results_limit=50)

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.max_results == 10

    def test_empty_domain_lists(self):
        """测试空域名列表"""
        # Arrange
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=10,
            include_domains=[],
            exclude_domains=[],
        )
        provider = self._create_mock_provider()

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.include_domains == []
        assert result.exclude_domains == []

    def test_empty_time_range(self):
        """测试空时间范围"""
        # Arrange
        time_range = TimeRange()  # 所有字段都为 None
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=10,
            time_range=time_range,
        )
        provider = self._create_mock_provider()

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        assert result.time_range is not None
        assert result.time_range.is_empty() is True

    def test_preferred_provider_not_passed(self):
        """测试 preferred_provider 参数不传递给 ProviderSearchRequest"""
        # Arrange
        unified = UnifiedSearchRequest(
            query="test query",
            max_results=10,
            preferred_provider="tavily",
        )
        provider = self._create_mock_provider()

        # Act
        result = ParameterAdapter.adapt(unified, provider)

        # Assert
        # preferred_provider 是编排层参数，不应传递给提供商请求
        assert not hasattr(result, "preferred_provider")