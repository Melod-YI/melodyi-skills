---
name: get-user-location
description: 获取用户的实时地理位置。当用户询问「我在哪」「我的位置」「获取我的地址」「定位」「查手机位置」或任何涉及获取用户当前地理位置的场景时触发此技能（例如需要帮用户查询附近的xxx、查询用户附近的天气等）。
---

# 获取用户位置

**此技能处于开发阶段。** 环境依赖问题（缺少 Python 包、Playwright 浏览器等）可根据下方指引自行修复；其他运行时错误**请直接联系用户**，不要自行尝试修复。

## 使用方法

在用户的工作目录下执行：

```bash
python <skill-path>/script/run.py --output .
```

`<skill-path>` 是本技能的安装路径（即 SKILL.md 所在目录）。整个流程约需 60 秒，通过 Bash 工具执行时请将 timeout 设置为 **180000**（3 分钟）。

需要两个凭据：`HUAWEI_USERNAME`（华为账号）和 `HUAWEI_PASSWORD`（密码）。可通过**环境变量**或**配置文件**提供，环境变量优先。

配置文件路径：`~/.melodyi-skills/get-user-location/config.json`，格式：

```json
{
  "huawei_username": "手机号/邮箱/账号名",
  "huawei_password": "密码"
}
```

也可用 `--config <路径>` 指定任意配置文件。脚本启动时会校验，缺失时会打印错误并退出。

## 读取输出

脚本的标准输出格式如下（两行）：

```
用户当前地址: 江苏省南京市雨花台区雨花街道华为南京研究所A区
经纬度: 31.97951, 118.76740
```

**通常只需读取 stdout 的地址与经纬度即可回复用户。** 未捕获到请求经纬度时第二行省略。

如需更详细的位置信息（省市区等行政区划、附近 POI 等），请加 `--output DIR` 参数，脚本会额外保存一份 JSON 文件并在 stdout 末尾提示路径：

```
用户当前地址: 江苏省南京市雨花台区雨花街道华为南京研究所A区
经纬度: 31.97951, 118.76740
详细数据已保存到 C:/workspace/helper/reverse-geocode-response.json（包含省市区行政区划、附近 POI 等信息）
```

**不指定 `--output` 时不保存任何文件，仅标准输出地址与经纬度。**

## JSON 详细格式

`reverse-geocode-response.json` 是华为 reverseGeocode 接口响应经精简后的结果（原始响应中的 `aois`、`roads`、`intersections`、`returnDesc` 已移除，`pois` 仅保留 distance 最小的至多 2 个，`addressComponent` 中 `streetNumber`、`adminCode` 及 `city.cityId` 已移除），结构如下：

```json
{
  "returnCode": "0",
  "addressDescription": "完整地址文本",
  "location": { "latitude": 31.97951, "longitude": 118.76740 },
  "pois": [
    { "name": "...", "address": "...", "distance": 0, "poiType": "...",
      "location": { "latitude": 0, "longitude": 0 } }
  ],
  "addressComponent": {
    "adminLevel1": "省", "adminLevel2": "市",
    "adminLevel3": "区", "adminLevel4": "街道",
    "countryCode": "CN", "countryName": "中国",
    "city": { "cityName": "市", "cityCode": "区号" }
  }
}
```

| 字段 | 说明 |
|---|---|
| `returnCode` | `"0"` 表示成功 |
| `addressDescription` | 完整的人类可读地址 |
| `location` | 顶层经纬度，取自 reverseGeocode **请求 payload**（即本次查询的输入经纬度），是输出中最真实准确的定位坐标；未捕获到 payload 时该字段省略 |
| `addressComponent` | 结构化行政区划：`adminLevel1`(省)、`adminLevel2`(市)、`adminLevel3`(区)、`adminLevel4`(街道) |
| `pois` | 附近兴趣点列表（按距离升序，至多 2 个），每个 POI 含 `name`、`address`、`distance`、`poiType`、`location`(经纬度) |

## 环境自检与修复

如果遇到环境问题，按以下方式处理：

```bash
# 1. 检查 Python 版本（需要 3.10+）
python --version

# 2. 安装 playwright 包
pip install -r <skill-path>/script/requirements.txt

# 3. 安装 Chromium 浏览器（报错 Executable doesn't exist 时执行）
playwright install chromium
```

## 调试模式

如果执行遇到运行时问题（非环境依赖），应联系用户。如果用户希望自行调试，可以加上 `--headed` 和 `--verbose` 参数重新执行：

```bash
python <skill-path>/script/run.py --output . --headed --verbose
```

这会显示浏览器窗口并输出详细日志，方便用户观察问题。
