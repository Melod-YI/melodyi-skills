#!/usr/bin/env python3
"""
华为云空间 - 查找设备定位数据提取工具

用法:
  python run.py                          # 无头模式，输出到临时目录
  python run.py --headed                 # 有头模式，输出到临时目录
  python run.py --output /path/to/dir    # 无头模式，输出到指定目录
  python run.py --headed --output ./out  # 有头模式，输出到指定目录

环境变量:
  HUAWEI_USERNAME  — 手机号/邮箱/账号名
  HUAWEI_PASSWORD  — 密码

也可用配置文件 ~/.melodyi-skills/get-user-location/config.json 提供凭据
（字段 huawei_username / huawei_password），或用 --config 指定路径；
环境变量优先于配置文件。

输出:
  <输出目录>/reverse-geocode-response.json
"""

import asyncio
import sys

from huawei_cloud.main import run


def main():
    try:
        asyncio.run(run(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\n已中断")
        sys.exit(130)
    except RuntimeError as e:
        print(f"✗ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
