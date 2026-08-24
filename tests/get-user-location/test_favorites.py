"""huawei_cloud.favorites 收藏点加载、近邻匹配与格式化测试"""

import json

import pytest

from huawei_cloud import favorites


class TestHaversineDistance:
    """haversine_distance_m 测试"""

    def test_same_point_is_zero(self):
        assert favorites.haversine_distance_m(31.98, 118.76, 31.98, 118.76) == 0.0

    def test_one_degree_latitude_approx_111km(self):
        """纬度差 1 度约 111320m，允许 0.5% 误差（地球半径取整带来的偏差）。"""
        d = favorites.haversine_distance_m(31.0, 118.0, 32.0, 118.0)
        assert abs(d - 111320) < 600

    def test_small_latitude_delta_in_meters(self):
        """纬度差 0.001 度约 111m。"""
        d = favorites.haversine_distance_m(31.0, 118.0, 31.001, 118.0)
        assert abs(d - 111.3) < 1.0

    def test_symmetric(self):
        """距离与起终点顺序无关。"""
        d1 = favorites.haversine_distance_m(31.0, 118.0, 32.0, 119.0)
        d2 = favorites.haversine_distance_m(32.0, 119.0, 31.0, 118.0)
        assert d1 == d2

    def test_returns_float(self):
        assert isinstance(
            favorites.haversine_distance_m(31.0, 118.0, 31.0, 118.0), float
        )


class TestFindNearbyFavorites:
    """find_nearby_favorites 测试"""

    FAVS = [
        {"name": "家", "latitude": 31.0000, "longitude": 118.0000},
        {"name": "公司", "latitude": 31.0020, "longitude": 118.0000},  # 约 222m
        {"name": "远方", "latitude": 35.0, "longitude": 120.0},  # 很远
    ]

    def test_returns_only_within_radius(self):
        """半径 200m 内仅命中『家』。"""
        matches = favorites.find_nearby_favorites(31.0000, 118.0000, self.FAVS, 200.0)
        names = [m["name"] for m in matches]
        assert names == ["家"]

    def test_includes_distance_m(self):
        matches = favorites.find_nearby_favorites(31.0000, 118.0000, self.FAVS, 200.0)
        assert "distance_m" in matches[0]
        assert matches[0]["distance_m"] == pytest.approx(0.0, abs=1e-6)

    def test_multiple_matches_sorted_ascending(self):
        """多个命中按距离从近到远排序。"""
        favs = [
            {"name": "远点", "latitude": 31.0010, "longitude": 118.0},  # 约 111m
            {"name": "近点", "latitude": 31.0002, "longitude": 118.0},  # 约 22m
            {"name": "中点", "latitude": 31.0005, "longitude": 118.0},  # 约 55m
        ]
        matches = favorites.find_nearby_favorites(31.0, 118.0, favs, 200.0)
        names = [m["name"] for m in matches]
        assert names == ["近点", "中点", "远点"]
        # 距离单调递增
        dists = [m["distance_m"] for m in matches]
        assert dists == sorted(dists)

    def test_boundary_inclusive(self):
        """恰好等于半径的收藏点应命中（<=）。"""
        # 0.001 度纬度 ≈ 111.3m，半径设 112 时命中
        favs = [{"name": "边界点", "latitude": 31.001, "longitude": 118.0}]
        matches = favorites.find_nearby_favorites(31.0, 118.0, favs, 112.0)
        assert [m["name"] for m in matches] == ["边界点"]

    def test_empty_favorites_returns_empty(self):
        assert favorites.find_nearby_favorites(31.0, 118.0, [], 200.0) == []

    def test_default_radius_200m(self):
        """未指定半径时默认 200m。"""
        # 0.002 度纬度 ≈ 222m > 200，不命中
        favs = [{"name": "公司", "latitude": 31.002, "longitude": 118.0}]
        matches = favorites.find_nearby_favorites(31.0, 118.0, favs)
        assert matches == []

    def test_does_not_mutate_input(self):
        favs = [{"name": "家", "latitude": 31.0, "longitude": 118.0}]
        favorites.find_nearby_favorites(31.0, 118.0, favs, 200.0)
        assert favs == [{"name": "家", "latitude": 31.0, "longitude": 118.0}]

    # --- 同 name 多点归并（方案3） + per-record 半径（方案1） ---

    def test_same_name_multiple_coords_dedup_nearest(self):
        """同 name 多点命中只输出一条，距离取最近。"""
        favs = [
            {"name": "玄武湖", "latitude": 31.0010, "longitude": 118.0},  # ~111m
            {"name": "玄武湖", "latitude": 31.0002, "longitude": 118.0},  # ~22m
            {"name": "玄武湖", "latitude": 31.0005, "longitude": 118.0},  # ~55m
        ]
        matches = favorites.find_nearby_favorites(31.0, 118.0, favs, 200.0)
        assert [m["name"] for m in matches] == ["玄武湖"]
        assert matches[0]["distance_m"] == pytest.approx(22.3, abs=1.0)

    def test_same_name_only_some_hit(self):
        """同 name 多点，仅远的带大 radius_m 命中 → 仍输出该 name。"""
        favs = [
            {"name": "玄武湖", "latitude": 31.0020, "longitude": 118.0},  # ~222m，默认不中
            {"name": "玄武湖", "latitude": 31.0020, "longitude": 118.0, "radius_m": 300},
        ]
        matches = favorites.find_nearby_favorites(31.0, 118.0, favs, 200.0)
        assert [m["name"] for m in matches] == ["玄武湖"]
        assert matches[0]["distance_m"] == pytest.approx(222.6, abs=1.0)

    def test_per_record_radius_overrides_default(self):
        """点距 ~222m：默认 200 不中、per-record radius_m=300 命中。"""
        favs = [
            {"name": "大地标", "latitude": 31.002, "longitude": 118.0, "radius_m": 300}
        ]
        # 不传函数形参 → 回退 DEFAULT_RADIUS_M=200；但 per-record 300 优先
        matches = favorites.find_nearby_favorites(31.0, 118.0, favs)
        assert [m["name"] for m in matches] == ["大地标"]

    def test_per_record_radius_beats_func_param(self):
        """per-record radius_m 优先于函数 radius_m 形参。"""
        favs = [
            {"name": "大", "latitude": 31.002, "longitude": 118.0, "radius_m": 300}
        ]
        # 函数传 200（默认），per-record 300，距离 ~222 → 命中
        matches = favorites.find_nearby_favorites(31.0, 118.0, favs, 200.0)
        assert [m["name"] for m in matches] == ["大"]

    def test_func_param_fallback_when_record_none(self):
        """记录无 radius_m 时回退函数 radius_m 形参（而非硬编码默认）。"""
        favs = [
            {"name": "小", "latitude": 31.001, "longitude": 118.0}  # ~111m，无 per-record
        ]
        # 函数传 150 → 111 < 150 命中
        hits = favorites.find_nearby_favorites(31.0, 118.0, favs, 150.0)
        assert [m["name"] for m in hits] == ["小"]
        # 函数传 100 → 111 > 100 不中（证明回退到的是形参而非 DEFAULT_RADIUS_M）
        no_hits = favorites.find_nearby_favorites(31.0, 118.0, favs, 100.0)
        assert no_hits == []

    def test_dedup_keeps_nearest_coord(self):
        """归并后 latitude/longitude 是最近命中点的坐标。"""
        favs = [
            {"name": "x", "latitude": 31.0010, "longitude": 118.0},  # ~111m 远
            {"name": "x", "latitude": 31.0002, "longitude": 118.0},  # ~22m 近
        ]
        matches = favorites.find_nearby_favorites(31.0, 118.0, favs, 200.0)
        assert matches[0]["latitude"] == 31.0002
        assert matches[0]["longitude"] == 118.0

    def test_no_radius_m_key_in_output(self):
        """输出不暴露 radius_m，仅 name/latitude/longitude/distance_m。"""
        favs = [
            {"name": "x", "latitude": 31.0002, "longitude": 118.0, "radius_m": 300}
        ]
        matches = favorites.find_nearby_favorites(31.0, 118.0, favs, 200.0)
        assert set(matches[0].keys()) == {"name", "latitude", "longitude", "distance_m"}


class TestLoadFavorites:
    """load_favorites 测试"""

    def test_loads_valid_list(self, tmp_path):
        f = tmp_path / "favorites.json"
        f.write_text(
            json.dumps(
                [
                    {"name": "家", "latitude": 31.98, "longitude": 118.76},
                    {"name": "公司", "latitude": 31.99, "longitude": 118.77},
                ]
            ),
            encoding="utf-8",
        )
        favs = favorites.load_favorites(str(f))
        assert len(favs) == 2
        assert favs[0]["name"] == "家"

    def test_missing_file_returns_empty(self, tmp_path):
        assert favorites.load_favorites(str(tmp_path / "nope.json")) == []

    def test_invalid_json_returns_empty(self, tmp_path):
        f = tmp_path / "favorites.json"
        f.write_text("{not json", encoding="utf-8")
        assert favorites.load_favorites(str(f)) == []

    def test_non_list_returns_empty(self, tmp_path):
        f = tmp_path / "favorites.json"
        f.write_text(json.dumps({"name": "家"}), encoding="utf-8")
        assert favorites.load_favorites(str(f)) == []

    def test_drops_entries_missing_fields(self, tmp_path):
        """缺 name/latitude/longitude 之一的条目被丢弃。"""
        f = tmp_path / "favorites.json"
        f.write_text(
            json.dumps(
                [
                    {"name": "家", "latitude": 31.98, "longitude": 118.76},
                    {"name": "无经度", "latitude": 31.98},
                    {"latitude": 31.98, "longitude": 118.76},  # 无 name
                    {"name": "无纬度", "longitude": 118.76},
                ]
            ),
            encoding="utf-8",
        )
        favs = favorites.load_favorites(str(f))
        assert len(favs) == 1
        assert favs[0]["name"] == "家"

    def test_drops_entries_with_non_numeric_coords(self, tmp_path):
        f = tmp_path / "favorites.json"
        f.write_text(
            json.dumps(
                [
                    {"name": "坏点", "latitude": "abc", "longitude": 118.76},
                    {"name": "好点", "latitude": 31.98, "longitude": 118.76},
                ]
            ),
            encoding="utf-8",
        )
        favs = favorites.load_favorites(str(f))
        assert [f_["name"] for f_ in favs] == ["好点"]

    def test_accepts_int_coordinates(self, tmp_path):
        f = tmp_path / "favorites.json"
        f.write_text(
            json.dumps([{"name": "家", "latitude": 31, "longitude": 118}]),
            encoding="utf-8",
        )
        favs = favorites.load_favorites(str(f))
        assert len(favs) == 1
        assert favs[0]["latitude"] == 31

    # --- 可选 radius_m（方案1：per-record 半径，经纬度组级而非 name 级） ---

    def test_loads_per_record_radius(self, tmp_path):
        """正数 radius_m 透传进内存对象。"""
        f = tmp_path / "favorites.json"
        f.write_text(
            json.dumps(
                [{"name": "玄武湖", "latitude": 32.07, "longitude": 118.79, "radius_m": 300}]
            ),
            encoding="utf-8",
        )
        favs = favorites.load_favorites(str(f))
        assert favs[0]["radius_m"] == 300

    def test_radius_m_none_when_absent(self, tmp_path):
        """未配置 radius_m 时内存对象该字段为 None（表示匹配阶段回退默认）。"""
        f = tmp_path / "favorites.json"
        f.write_text(
            json.dumps([{"name": "家", "latitude": 31.98, "longitude": 118.76}]),
            encoding="utf-8",
        )
        favs = favorites.load_favorites(str(f))
        assert favs[0]["radius_m"] is None

    def test_invalid_radius_m_falls_back(self, tmp_path):
        """radius_m 非法（字符串/bool/0/负数）时记录保留、radius_m 回退 None。"""
        f = tmp_path / "favorites.json"
        f.write_text(
            json.dumps(
                [
                    {"name": "a", "latitude": 31.0, "longitude": 118.0, "radius_m": "big"},
                    {"name": "b", "latitude": 31.0, "longitude": 118.0, "radius_m": True},
                    {"name": "c", "latitude": 31.0, "longitude": 118.0, "radius_m": 0},
                    {"name": "d", "latitude": 31.0, "longitude": 118.0, "radius_m": -5},
                ]
            ),
            encoding="utf-8",
        )
        favs = favorites.load_favorites(str(f))
        assert len(favs) == 4
        assert all(fav["radius_m"] is None for fav in favs)

    def test_default_path_when_none(self, monkeypatch, tmp_path):
        """未传路径时读取 USER_FAVORITES_FILE。"""
        f = tmp_path / "favorites.json"
        f.write_text(
            json.dumps([{"name": "家", "latitude": 31.0, "longitude": 118.0}]),
            encoding="utf-8",
        )
        monkeypatch.setattr(favorites, "USER_FAVORITES_FILE", f)
        favs = favorites.load_favorites()
        assert favs[0]["name"] == "家"


class TestFormatNearbyFavorites:
    """format_nearby_favorites 测试"""

    def test_none_when_empty(self):
        assert favorites.format_nearby_favorites([]) is None

    def test_renders_header_and_lines(self):
        matches = [
            {"name": "家", "latitude": 31.0, "longitude": 118.0, "distance_m": 85.4},
            {"name": "公司", "latitude": 31.1, "longitude": 118.1, "distance_m": 120.6},
        ]
        text = favorites.format_nearby_favorites(matches)
        assert text == (
            "附近收藏点:\n"
            "  - 家 (85m)\n"
            "  - 公司 (121m)"
        )

    def test_rounds_distance_to_integer(self):
        matches = [
            {"name": "点", "latitude": 0, "longitude": 0, "distance_m": 0.4},
        ]
        text = favorites.format_nearby_favorites(matches)
        assert "  - 点 (0m)" in text

    def test_single_match(self):
        matches = [
            {"name": "家", "latitude": 31.0, "longitude": 118.0, "distance_m": 50.0},
        ]
        text = favorites.format_nearby_favorites(matches)
        assert text == "附近收藏点:\n  - 家 (50m)"
