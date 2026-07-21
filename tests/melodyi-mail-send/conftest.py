"""melodyi-mail-send 测试 conftest。

将该 skill 的 scripts/ 目录加入模块搜索路径，使测试可直接 import send_mail。
仅注入本 skill 的 scripts，避免与其他 skill 的同名顶层模块冲突。
"""

import sys
from pathlib import Path

SCRIPTS_DIR = (
    Path(__file__).resolve().parents[2] / "skills" / "melodyi-mail-send" / "scripts"
)
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
