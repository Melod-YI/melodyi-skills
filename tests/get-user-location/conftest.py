"""get-user-location 测试 conftest。

将该 skill 的 script/ 目录（注意为单数）加入模块搜索路径，使测试可直接
import huawei_cloud 包。仅注入本 skill 的 script，避免与其他 skill 的
同名顶层模块冲突。
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "skills" / "get-user-location" / "script"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
