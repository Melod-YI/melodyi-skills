# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 Agent Skill 项目，让 AI Agent 具备获取用户地理位置的能力。实现方式：通过 Playwright 自动化登录华为云空间，触发「查找设备」功能，拦截 `reverseGeocode` 网络响应，提取用户当前地址。

## 常用命令

```bash
# 安装依赖
pip install -r script/requirements.txt
playwright install chromium

# 运行（需配置华为账号凭据）
python script/run.py --output .

# 调试模式（显示浏览器 + 详细日志）
python script/run.py --output . --headed --verbose
```

凭据可通过**环境变量**或**配置文件**提供，环境变量优先：
- 环境变量：`HUAWEI_USERNAME`、`HUAWEI_PASSWORD`
- 配置文件：`~/.melodyi-skills/get-user-location/config.json`（字段 `huawei_username`、`huawei_password`）
- 也可用 `--config <路径>` 指定任意配置文件

## CLI 参数完整参考

| 参数 | 说明 |
|---|---|
| `--output DIR` | 输出目录；不指定则不保存文件，仅标准输出地址与经纬度 |
| `--headed` | 显示浏览器窗口 |
| `--verbose` / `-v` | 详细日志输出 |
| `--config PATH` | 配置文件路径（默认 `~/.melodyi-skills/get-user-location/config.json`） |

无参数时为无头模式，仅标准输出地址与经纬度，不保存文件。

## 输出格式

### stdout

不指定 `--output` 时仅输出地址与经纬度，不保存任何文件：

```
用户当前地址: 江苏省南京市雨花台区雨花街道华为南京研究所A区
经纬度: 31.97951, 118.76740
```

未捕获到请求经纬度时第二行省略。指定 `--output DIR` 时额外保存 JSON 并追加一行提示：

```
用户当前地址: 江苏省南京市雨花台区雨花街道华为南京研究所A区
经纬度: 31.97951, 118.76740
详细数据已保存到 C:/workspace/helper/reverse-geocode-response.json（包含省市区行政区划、附近 POI 等信息）
```

### JSON 文件结构

`reverse-geocode-response.json` 是华为 reverseGeocode 接口响应经精简后的结果（原始响应中的 `aois`、`roads`、`intersections`、`returnDesc` 已移除，`pois` 仅保留 distance 最小的至多 2 个，`addressComponent` 中 `streetNumber`、`adminCode` 及 `city.cityId` 已移除）：

```json
{
  "returnCode": "0",
  "addressDescription": "完整地址文本",
  "location": { "latitude": 31.97951, "longitude": 118.76740 },
  "pois": [
    { "name", "address", "distance", "poiType", "location": { "latitude", "longitude" } }
  ],
  "addressComponent": {
    "adminLevel1": "省", "adminLevel2": "市",
    "adminLevel3": "区", "adminLevel4": "街道",
    "countryCode": "CN", "countryName": "中国",
    "city": { "cityName": "市", "cityCode": "区号" }
  }
}
```

顶层 `location` 取自 reverseGeocode **请求 payload**（即本次查询的输入经纬度），是输出中最真实准确的定位坐标；未捕获到 payload 时该字段省略。

## 错误处理

| 错误类型 | 处理方式 |
|---|---|
| 凭据缺失（环境变量与配置文件均未提供） | 脚本打印具体缺失项，提示用户配置 |
| Python/playwright 未安装 | `pip install -r script/requirements.txt` |
| Chromium 未安装 | `playwright install chromium` |
| 登录失败（密码错误、验证码） | 联系用户 |
| 页面元素未找到 | 联系用户，建议用 `--headed --verbose` 调试 |
| 网络请求未捕获 | 联系用户，建议用 `--headed --verbose` 调试 |
| 其他未预期错误 | 联系用户，提供完整错误信息 |

## 架构

入口 `script/run.py` → 调用 `huawei_cloud.main.run(argv)` 执行完整流水线。

**流水线阶段**（`main.py`）：
1. **配置**（`config.py`）：argparse 解析 CLI 参数 + 凭据（环境变量优先，回退配置文件）→ `Config` dataclass
2. **浏览器**（`browser.py`）：启动 Chromium，注入反检测参数
3. **认证**（`auth.py`）：导航到华为云 → 等待 iframe → 填写登录表单 → 验证登录成功
4. **拦截**（`interceptor.py`）：被动监听 `reverseGeocode` 响应，同时捕获请求 payload（POST body，含查询经纬度）→ 点击「查找设备」触发请求
5. **提取**（`extractor.py`）：解析响应 JSON → 校验 `returnCode` → 提取 `addressDescription` → 从请求 payload 提取查询经纬度 → 精简响应（移除无用字段、裁剪 pois）→ 注入顶层 `location` → 保存文件

**核心设计决策**：网络拦截使用 `page.on("response", callback)` 被动监听，而非 `route.fetch()` 主动拦截（Python 版 Playwright 的 `route.fetch()` 存在 bug）。

## Playwright Python 踩坑记录

| 问题 | Node.js 写法 | Python 写法 |
|------|-------------|-------------|
| iframe 定位 | `page.locator('#frame').contentFrame()` | `page.frame_locator('#frame')` — Python 中 `content_frame()` 不存在 |
| 响应 headers | `await response.headersArray()` | `response.headers` — Python 中是属性不是方法 |
| route 拦截 | `route.fetch()` + `route.fulfill()` | `route.fetch()` 有 bug，**必须用 `page.on("response", callback)` 被动监听** |

## 反检测策略

- 始终 `headless=False` 启动，无头模式通过 `--headless=new` 参数实现（旧版无头模式会被网站检测）
- `--disable-blink-features=AutomationControlled` 隐藏自动化标志
- 登录操作间加入随机延时（`_random_delay`）模拟人工操作
- 被动监听网络响应而非 route 拦截，减少被检测风险
