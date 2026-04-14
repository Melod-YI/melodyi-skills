"""TimeRange 模型测试"""

import pytest
from datetime import datetime, timedelta
from melodyi_search.domain.models.search_request import TimeRange


class TestTimeRange:
    """TimeRange 测试类"""

    def test_create_with_range_type_day(self):
        """测试使用 range_type='day' 创建"""
        time_range = TimeRange(range_type="day")
        assert time_range.range_type == "day"
        assert time_range.start_date is None
        assert time_range.end_date is None

    def test_create_with_range_type_week(self):
        """测试使用 range_type='week' 创建"""
        time_range = TimeRange(range_type="week")
        assert time_range.range_type == "week"

    def test_create_with_range_type_month(self):
        """测试使用 range_type='month' 创建"""
        time_range = TimeRange(range_type="month")
        assert time_range.range_type == "month"

    def test_create_with_range_type_year(self):
        """测试使用 range_type='year' 创建"""
        time_range = TimeRange(range_type="year")
        assert time_range.range_type == "year"

    def test_create_with_explicit_dates(self):
        """测试使用精确日期创建"""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)
        time_range = TimeRange(start_date=start, end_date=end)
        assert time_range.start_date == start
        assert time_range.end_date == end
        assert time_range.range_type is None

    def test_create_empty_time_range(self):
        """测试创建空的时间范围"""
        time_range = TimeRange()
        assert time_range.range_type is None
        assert time_range.start_date is None
        assert time_range.end_date is None

    def test_range_type_invalid_raises_error(self):
        """测试无效 range_type 抛出错误"""
        with pytest.raises(ValueError):
            TimeRange(range_type="invalid")

    def test_is_empty_method(self):
        """测试 is_empty() 方法"""
        # 空范围
        time_range = TimeRange()
        assert time_range.is_empty() is True

        # 有 range_type
        time_range = TimeRange(range_type="day")
        assert time_range.is_empty() is False

        # 有 start_date
        time_range = TimeRange(start_date=datetime(2026, 1, 1))
        assert time_range.is_empty() is False

        # 有 end_date
        time_range = TimeRange(end_date=datetime(2026, 12, 31))
        assert time_range.is_empty() is False

        # 同时有 range_type 和日期
        time_range = TimeRange(range_type="week", start_date=datetime(2026, 1, 1))
        assert time_range.is_empty() is False