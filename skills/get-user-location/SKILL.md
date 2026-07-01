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

## 收藏点（附近地点判断）

定位精度有限：反向地理编码得到的地址文本在经纬度小幅偏移时，描述可能偏差较大（例如定位点偏移几十米后，命中的街道/POI 文本可能完全不同）；但经纬度本身偏差很小。**收藏点功能**通过比较经纬度的球面距离，更稳定地判断用户是否处于特定地点附近（例如家附近、公司附近），作为地址文本的补充——只要定位点落在收藏点 200m 范围内，即视为「在该收藏点附近」并在结果中列出。

收藏点存放在独立文件 `~/.melodyi-skills/get-user-location/favorites.json`（与凭据 `config.json` 分离），格式为 JSON 顶层数组：

```json
[
  {"name": "家", "latitude": 31.97951, "longitude": 118.76740},
  {"name": "公司", "latitude": 31.98500, "longitude": 118.77000}
]
```

每条记录需含 `name`（字符串）、`latitude`/`longitude`（数值）。文件不存在或格式非法时静默忽略（不影响定位主流程）；字段缺失或类型非法的单条记录会被跳过。匹配半径固定 200m，多个命中按距离从近到远排序。仅当成功捕获到定位经纬度时才进行匹配。

## 读取输出

脚本的标准输出格式如下（地址一行，纬度/经度各一行，均带中英文标注）：

```
用户当前地址: 江苏省南京市雨花台区雨花街道华为南京研究所A区
纬度(latitude): 31.97951
经度(longitude): 118.76740
```

**通常只需读取 stdout 的地址与经纬度即可回复用户。** 未捕获到请求经纬度时纬度/经度两行省略。

如需更详细的位置信息（省市区等行政区划、附近 POI 等），请加 `--output DIR` 参数，脚本会额外保存一份 JSON 文件并在 stdout 末尾提示路径：

```
用户当前地址: 江苏省南京市雨花台区雨花街道华为南京研究所A区
纬度(latitude): 31.97951
经度(longitude): 118.76740
附近收藏点:
  - 家 (85m)
  - 公司 (121m)
详细数据已保存到 C:/workspace/helper/reverse-geocode-response.json（包含省市区行政区划、附近 POI 等信息）
```

**不指定 `--output` 时不保存任何文件，仅标准输出地址与经纬度。**

### 附近收藏点输出

当定位点落在某收藏点 200m 内时，stdout 会在经纬度行之后追加「附近收藏点」块，列出每个命中收藏点的名称与距离（四舍五入到整米），按距离从近到远排序：

```
用户当前地址: 江苏省南京市雨花台区雨花街道华为南京研究所A区
纬度(latitude): 31.97951
经度(longitude): 118.76740
附近收藏点:
  - 家 (85m)
  - 公司 (121m)
```

无任何收藏点命中时省略整个块。未配置 `favorites.json` 或文件缺失时同样省略，不影响定位主流程。

### 多次调用与入参不一致

「查找设备」页面可能短时间内对 `reverseGeocode` 发起多次调用。脚本会静默期等待收集这些调用：**取时间最新的那次结果为准**。当多次调用的请求经纬度**不一致**时，stdout 会在经纬度行之后追加一条警告，例如：

```
用户当前地址: 江苏省南京市雨花台区雨花街道华为南京研究所A区
纬度(latitude): 31.97951
经度(longitude): 118.76740
⚠ 检测到 3 次定位请求且经纬度不一致，已采用最后一次结果
```

多次调用但经纬度一致时静默取最新，不追加警告。此时如需查看每次调用的详情，加 `--verbose`（见下文）。

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
  },
  "nearby_favorites": [
    { "name": "家", "latitude": 31.97951, "longitude": 118.76740, "distance_m": 85.2 }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `returnCode` | `"0"` 表示成功 |
| `addressDescription` | 完整的人类可读地址 |
| `location` | 顶层经纬度，取自 reverseGeocode **请求 payload**（即本次查询的输入经纬度），是输出中最真实准确的定位坐标；未捕获到 payload 时该字段省略 |
| `addressComponent` | 结构化行政区划：`adminLevel1`(省)、`adminLevel2`(市)、`adminLevel3`(区)、`adminLevel4`(街道) |
| `pois` | 附近兴趣点列表（按距离升序，至多 2 个），每个 POI 含 `name`、`address`、`distance`、`poiType`、`location`(经纬度) |
| `nearby_favorites` | 200m 内命中的收藏点列表（按距离升序），每项含 `name`、`latitude`、`longitude`、`distance_m`(米)；无命中或未配置收藏点时该字段省略 |

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

这会显示浏览器窗口并输出详细日志，方便用户观察问题。`--verbose` 还会逐次打印每次 `reverseGeocode` 请求的**时间、入参经纬度（纬度/经度分行标注）、返回地址描述**（无论是否一致），便于核对多次调用情况。
