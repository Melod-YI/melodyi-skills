# scripts — melodyi-filebot 开发辅助脚本

本目录下的脚本为**开发辅助工具**，不属于 skill 对外运行时能力（不写入 `SKILL.md` 的 agent 手册）。

## gen-fixtures.py — 从真实源目录生成极小测试用例

把一个真实影视目录（几十 GB 的视频）转成几乎不占空间、但保留真实目录结构与时长元数据的测试用例（fixture），用于测试 `analyze` / `draft-plan` / `execute-plan` 等命令。

### 原理

- `analyze` 的时长来自 `ffprobe -show_entries format=duration`，读的是**容器元数据**，不逐帧扫描。
- 用 `ffmpeg -f lavfi -i color=black:s=4x4:d=<秒>:r=1/<秒>` 生成 **1 帧**黑屏视频：容器 `duration` 元数据报 `<秒>`，但文件体积恒定 ~1 KB，与时长无关。
- 字幕等非视频文件**原样复制**（保留真实伴生关系，可测伴生改名）。

### 用法

```bash
python skills/melodyi-filebot/scripts/gen-fixtures.py <源目录> --name <用例名> [--overwrite]
```

默认输出到 `packages/melodyi-filebot/tests/fixtures/<用例名>/`，并写 `manifest.json`（记录每个视频的相对路径、真实时长、生成体积）。

示例（高达SEED 重制版）：

```bash
python skills/melodyi-filebot/scripts/gen-fixtures.py \
    "D:/download/机动战士高达seed+seed destiny  重制版 1080P" \
    --name gundam-seed-hd
```

实测：源 87 GB → fixture 5.4 MB（98 视频 + 98 字幕），`analyze` 正确显示 `00:23:53`。

### 测试时如何使用 fixture

fixture 入库为**只读模板**。测试时 `copytree` 到 pytest 的 `tmp_path` 隔离使用、跑完即弃，见 `tests/test_fixtures.py`：

```python
import shutil
from melodyi_filebot import structure

def test_xxx(gundam_fixture, tmp_path):
    dst = tmp_path / "Season 1"
    shutil.copytree(gundam_fixture / "Season 1", dst)
    result = structure.analyze_path(str(dst))  # 真实 ffprobe
    assert result.total_videos == 48
```

### 依赖

`ffprobe` / `ffmpeg`（PATH 可见）、`melodyi_filebot` 包（`pip install -e packages/melodyi-filebot`）。

### 添加新用例

1. 准备一个真实源目录（含视频 + 字幕）。
2. 跑 `gen-fixtures.py <src> --name <name>` 生成。
3. 在 `tests/test_fixtures.py` 加测试消费它。
