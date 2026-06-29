"""huawei_cloud.extractor 数据提取与精简测试"""

import json
import sys
from pathlib import Path

import pytest

# 将 script/ 加入模块搜索路径，使其可直接 import huawei_cloud
SCRIPT_DIR = Path(__file__).resolve().parents[1] / "script"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from huawei_cloud import extractor

# 合成示例响应（结构同真实响应，但已脱敏，不含真实地址），作为精简逻辑的回归 fixture
SAMPLE_RESPONSE = Path(__file__).resolve().parent / "fixtures" / "reverse-geocode-sample.json"


@pytest.fixture
def sample_data():
    """加载示例响应"""
    return json.loads(SAMPLE_RESPONSE.read_text(encoding="utf-8"))


class TestExtractData:
    """extract_data 测试"""

    def test_parses_json_body(self):
        data = extractor.extract_data({"body": '{"returnCode": "0"}'})
        assert data["returnCode"] == "0"

    def test_empty_captured_raises(self):
        with pytest.raises(RuntimeError):
            extractor.extract_data({})

    def test_empty_body_raises(self):
        with pytest.raises(RuntimeError):
            extractor.extract_data({"body": ""})

    def test_invalid_json_raises(self):
        with pytest.raises(RuntimeError):
            extractor.extract_data({"body": "{not json"})


class TestValidateResponse:
    """validate_response 测试"""

    def test_returns_address_when_code_zero(self):
        result = extractor.validate_response(
            {"returnCode": "0", "addressDescription": "某地"}
        )
        assert result == {"return_code": "0", "address": "某地"}

    def test_raises_when_code_not_zero(self):
        with pytest.raises(RuntimeError):
            extractor.validate_response({"returnCode": "1"})


class TestSimplifyRemoveTopKeys:
    """顶层无用字段移除测试"""

    def test_removes_aois_roads_intersections_return_desc(self, sample_data):
        simplified = extractor.simplify_response(sample_data)
        for key in ("aois", "roads", "intersections", "returnDesc"):
            assert key not in simplified, f"{key} 应被移除"

    def test_preserves_top_level_useful_fields(self, sample_data):
        simplified = extractor.simplify_response(sample_data)
        assert simplified["returnCode"] == sample_data["returnCode"]
        assert simplified["addressDescription"] == sample_data["addressDescription"]
        assert "pois" in simplified
        assert "addressComponent" in simplified

    def test_does_not_mutate_input(self, sample_data):
        """精简不应修改原始数据"""
        extractor.simplify_response(sample_data)
        assert "aois" in sample_data
        assert "roads" in sample_data
        assert "intersections" in sample_data
        assert "returnDesc" in sample_data
        assert len(sample_data["pois"]) > 2
        assert "streetNumber" in sample_data["addressComponent"]


class TestSimplifyPois:
    """pois 裁剪测试"""

    def test_keeps_at_most_two_smallest_distance(self, sample_data):
        simplified = extractor.simplify_response(sample_data)
        pois = simplified["pois"]
        assert len(pois) == 2
        # 合成 fixture 中 distance 最小的两个分别为 0.0 与 12.3
        assert pois[0]["distance"] == 0.0
        assert pois[1]["distance"] == 12.3

    def test_pois_sorted_ascending(self, sample_data):
        simplified = extractor.simplify_response(sample_data)
        pois = simplified["pois"]
        assert pois[0]["distance"] <= pois[1]["distance"]

    def test_keeps_full_poi_objects(self, sample_data):
        """保留的 poi 保持原字段完整（仅数量裁剪，不删字段）"""
        simplified = extractor.simplify_response(sample_data)
        first = simplified["pois"][0]
        assert first["name"] == "测试园区A区"
        assert "location" in first
        assert "poiType" in first

    def test_fewer_than_max_keeps_all(self):
        data = {"pois": [{"distance": 10.0}, {"distance": 20.0}]}
        simplified = extractor.simplify_response(data)
        assert len(simplified["pois"]) == 2

    def test_single_poi_kept(self):
        data = {"pois": [{"distance": 5.0}]}
        simplified = extractor.simplify_response(data)
        assert len(simplified["pois"]) == 1

    def test_empty_pois_kept_empty(self):
        data = {"pois": []}
        simplified = extractor.simplify_response(data)
        assert simplified["pois"] == []

    def test_missing_pois_key_not_added(self):
        data = {"returnCode": "0"}
        simplified = extractor.simplify_response(data)
        assert "pois" not in simplified

    def test_missing_distance_treated_as_largest(self):
        """缺少 distance 字段的 poi 排在最后"""
        data = {"pois": [{"name": "a", "distance": 1.0}, {"name": "b"}, {"name": "c", "distance": 2.0}]}
        simplified = extractor.simplify_response(data)
        names = [p["name"] for p in simplified["pois"]]
        assert names == ["a", "c"]


class TestSimplifyAddressComponent:
    """addressComponent 字段精简测试"""

    def test_removes_street_number_and_admin_code(self, sample_data):
        simplified = extractor.simplify_response(sample_data)
        ac = simplified["addressComponent"]
        assert "streetNumber" not in ac
        assert "adminCode" not in ac

    def test_removes_city_id(self, sample_data):
        simplified = extractor.simplify_response(sample_data)
        city = simplified["addressComponent"]["city"]
        assert "cityId" not in city
        # 同级有用字段保留
        assert city["cityName"] == "示例市"
        assert city["cityCode"] == "010"

    def test_preserves_other_address_component_fields(self, sample_data):
        simplified = extractor.simplify_response(sample_data)
        ac = simplified["addressComponent"]
        assert ac["adminLevel1"] == "示例省"
        assert ac["adminLevel2"] == "示例市"
        assert ac["adminLevel3"] == "示例区"
        assert ac["adminLevel4"] == "示例街道"
        assert ac["countryCode"] == "CN"
        assert ac["countryName"] == "中国"

    def test_missing_address_component_handled(self):
        data = {"returnCode": "0"}
        simplified = extractor.simplify_response(data)
        assert "addressComponent" not in simplified

    def test_address_component_without_city_handled(self):
        data = {"addressComponent": {"adminLevel1": "X省"}}
        simplified = extractor.simplify_response(data)
        assert simplified["addressComponent"] == {"adminLevel1": "X省"}


class TestSimplifyIntegration:
    """基于示例文件的端到端精简校验"""

    def test_sample_simplifies_to_expected_shape(self, sample_data):
        simplified = extractor.simplify_response(sample_data)

        # 顶层仅保留有用键
        expected_top = {"returnCode", "addressDescription", "pois", "addressComponent"}
        assert set(simplified.keys()) == expected_top

        # pois 至多 2 个
        assert len(simplified["pois"]) <= 2

        # addressComponent 无 streetNumber / adminCode，city 无 cityId
        ac = simplified["addressComponent"]
        assert "streetNumber" not in ac
        assert "adminCode" not in ac
        assert "cityId" not in ac["city"]


class TestExtractRequestLocation:
    """请求 payload 经纬度提取测试"""

    PAYLOAD = (
        '{"location":{"latitude":31.97951471724566,"longitude":118.76740202569802},'
        '"language":"zh-CN","isExtension":true,"isExtendedAoi":true,'
        '"sortBy":0,"requestId":"01100_02_1782551703_74373686"}'
    )

    def test_extracts_lat_lng(self):
        captured = {"request_body": self.PAYLOAD}
        loc = extractor.extract_request_location(captured)
        assert loc == {
            "latitude": 31.97951471724566,
            "longitude": 118.76740202569802,
        }

    def test_returns_floats(self):
        loc = extractor.extract_request_location({"request_body": self.PAYLOAD})
        assert isinstance(loc["latitude"], float)
        assert isinstance(loc["longitude"], float)

    def test_missing_request_body_returns_none(self):
        assert extractor.extract_request_location({}) is None

    def test_empty_request_body_returns_none(self):
        assert extractor.extract_request_location({"request_body": ""}) is None

    def test_invalid_json_returns_none(self):
        assert extractor.extract_request_location({"request_body": "{not json"}) is None

    def test_missing_location_field_returns_none(self):
        payload = '{"language":"zh-CN","sortBy":0}'
        assert extractor.extract_request_location({"request_body": payload}) is None

    def test_location_missing_latitude_returns_none(self):
        payload = '{"location":{"longitude":118.76}}'
        assert extractor.extract_request_location({"request_body": payload}) is None

    def test_non_dict_location_returns_none(self):
        payload = '{"location":"not a dict"}'
        assert extractor.extract_request_location({"request_body": payload}) is None


class TestOutputIntegration:
    """模拟 main 流程：精简响应 + 注入 payload 经纬度"""

    PAYLOAD = (
        '{"location":{"latitude":31.97951471724566,"longitude":118.76740202569802},'
        '"language":"zh-CN"}'
    )

    def test_output_includes_top_level_location(self, sample_data):
        simplified = extractor.simplify_response(sample_data)
        location = extractor.extract_request_location({"request_body": self.PAYLOAD})
        if location is not None:
            simplified["location"] = location

        assert simplified["location"] == {
            "latitude": 31.97951471724566,
            "longitude": 118.76740202569802,
        }
        # location 为顶层字段，与 addressDescription 同级
        assert "location" in simplified
        assert "addressDescription" in simplified

    def test_output_without_payload_has_no_location(self, sample_data):
        """未捕获 payload 时不写入 location 字段"""
        simplified = extractor.simplify_response(sample_data)
        location = extractor.extract_request_location({})
        if location is not None:
            simplified["location"] = location

        assert "location" not in simplified


class TestFormatResult:
    """format_result 标准输出格式化测试"""

    LOC = {"latitude": 31.97951, "longitude": 118.7674}

    def test_address_only_when_no_location_and_no_output(self):
        """无经纬度、未指定 --output：仅输出地址一行。"""
        text = extractor.format_result("南京市A区", None, None)
        assert text == "用户当前地址: 南京市A区"

    def test_includes_location_line(self):
        """有经纬度、未指定 --output：地址 + 经纬度两行。"""
        text = extractor.format_result("南京市A区", self.LOC, None)
        assert text == (
            "用户当前地址: 南京市A区\n经纬度: 31.97951, 118.7674"
        )

    def test_includes_output_file_line(self):
        """指定 --output：追加详细数据文件路径行。"""
        text = extractor.format_result(
            "南京市A区", self.LOC, "C:/tmp/reverse-geocode-response.json"
        )
        assert text == (
            "用户当前地址: 南京市A区\n"
            "经纬度: 31.97951, 118.7674\n"
            "详细数据已保存到 C:/tmp/reverse-geocode-response.json"
            "（包含省市区行政区划、附近 POI 等信息）"
        )

    def test_output_file_line_without_location(self):
        """指定 --output 但无经纬度：省略经纬度行，仍提示文件路径。"""
        text = extractor.format_result(
            "南京市A区", None, "C:/tmp/reverse-geocode-response.json"
        )
        assert text == (
            "用户当前地址: 南京市A区\n"
            "详细数据已保存到 C:/tmp/reverse-geocode-response.json"
            "（包含省市区行政区划、附近 POI 等信息）"
        )


