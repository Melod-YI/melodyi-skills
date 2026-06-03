# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 Agent Skill 项目，让 AI Agent 具备获取用户地理位置的能力。实现方式：通过 Playwright 自动化登录华为云空间，触发「查找设备」功能，拦截 `reverseGeocode` 网络响应，提取用户当前地址。

## 常用命令

```bash
# 安装依赖
pip install -r script/requirements.txt
playwright install chromium

# 运行（需先设置环境变量 HUAWEI_USERNAME 和 HUAWEI_PASSWORD）
python script/run.py --output .

# 调试模式（显示浏览器 + 详细日志）
python script/run.py --output . --headed --verbose
```

## CLI 参数完整参考

| 参数 | 说明 |
|---|---|
| `--output DIR` | 输出目录（默认系统临时目录） |
| `--headed` | 显示浏览器窗口 |
| `--verbose` / `-v` | 详细日志输出 |

无参数时为无头模式 + 输出到临时目录。

## 输出格式

### stdout

```
用户当前地址: 江苏省南京市雨花台区雨花街道华为南京研究所A区
完整数据已保存到 C:/workspace/helper/reverse-geocode-response.json
```

### JSON 文件完整结构

`reverse-geocode-response.json` 是华为 reverseGeocode 接口的原始响应：

```json
{
  "returnCode": "0",
  "addressDescription": "完整地址文本",
  "addressComponent": {
    "adminLevel1": "省", "adminLevel2": "市",
    "adminLevel3": "区", "adminLevel4": "街道",
    "countryCode": "CN", "countryName": "中国",
    "streetNumber": { "streetName": "...", "formatAddress": "..." }
  },
  "pois": [{ "name", "address", "distance", "poiType", "location": { "latitude", "longitude" } }],
  "roads": [{ "name", "distance", "direction", "location" }],
  "aois": [{ "name", "area", "distance", "poiType", "location" }],
  "intersections": [{ "name", "distance", "direction", "location" }]
}
```

## 错误处理

| 错误类型 | 处理方式 |
|---|---|
| 环境变量缺失 | 脚本打印具体缺失变量名，提示用户配置 |
| Python/playwright 未安装 | `pip install -r script/requirements.txt` |
| Chromium 未安装 | `playwright install chromium` |
| 登录失败（密码错误、验证码） | 联系用户 |
| 页面元素未找到 | 联系用户，建议用 `--headed --verbose` 调试 |
| 网络请求未捕获 | 联系用户，建议用 `--headed --verbose` 调试 |
| 其他未预期错误 | 联系用户，提供完整错误信息 |

## 架构

入口 `script/run.py` → 调用 `huawei_cloud.main.run(argv)` 执行完整流水线。

**流水线阶段**（`main.py`）：
1. **配置**（`config.py`）：argparse 解析 CLI 参数 + 环境变量 → `Config` dataclass
2. **浏览器**（`browser.py`）：启动 Chromium，注入反检测参数
3. **认证**（`auth.py`）：导航到华为云 → 等待 iframe → 填写登录表单 → 验证登录成功
4. **拦截**（`interceptor.py`）：被动监听 `reverseGeocode` 响应 → 点击「查找设备」触发请求
5. **提取**（`extractor.py`）：解析 JSON → 校验 `returnCode` → 提取 `addressDescription` → 保存文件

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
