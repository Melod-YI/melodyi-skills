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

需要两个环境变量：`HUAWEI_USERNAME`（华为账号）和 `HUAWEI_PASSWORD`（密码）。脚本启动时会校验，缺失时会打印错误并退出。

## 读取输出

脚本的标准输出格式如下：

```
用户当前地址: 江苏省南京市雨花台区雨花街道华为南京研究所A区
完整数据已保存到 C:/workspace/helper/reverse-geocode-response.json
```

**通常只需读取 stdout 第一行的地址信息即可回复用户。** 仅当用户需要更详细的位置信息（经纬度、附近 POI 等）时，再读取输出的 JSON 文件。

## JSON 详细格式

`reverse-geocode-response.json` 包含完整的逆地理编码数据，关键字段：

| 字段 | 说明 |
|---|---|
| `returnCode` | `"0"` 表示成功 |
| `addressDescription` | 完整的人类可读地址 |
| `addressComponent` | 结构化行政区划：`adminLevel1`(省)、`adminLevel2`(市)、`adminLevel3`(区)、`adminLevel4`(街道) |
| `pois` | 附近兴趣点列表（按距离排序），每个 POI 含 `name`、`address`、`distance`、`poiType`、`location`(经纬度) |
| `roads` | 附近道路列表 |
| `aois` | 所在区域面（商圈/园区等） |

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
