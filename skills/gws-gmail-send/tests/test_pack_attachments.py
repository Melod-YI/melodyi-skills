"""pack_attachments.py 测试。

需要环境里存在 7z（默认从 PATH 查找）。无 7z 时整组测试 skip。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import pack_attachments as pa

SEVEN_ZIP = shutil.which("7z")
pytestmark = pytest.mark.skipif(SEVEN_ZIP is None, reason="环境无 7z，跳过打包测试")


def _extract_outer(outer: Path, password: str, dest: Path) -> None:
    """用密码解压外层 zip 到 dest。"""
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [SEVEN_ZIP, "x", f"-p{password}", "-y", str(outer)],
        check=True, capture_output=True, cwd=dest,
    )


def _extract_inner(inner: Path, dest: Path) -> None:
    """解压无密码内层 zip 到 dest。"""
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [SEVEN_ZIP, "x", "-y", str(inner)],
        check=True, capture_output=True, cwd=dest,
    )


def _parse_stdout(capsys) -> tuple[Path, str]:
    out = capsys.readouterr().out.strip().splitlines()
    archive = next(line.split("=", 1)[1] for line in out if line.startswith("ARCHIVE="))
    password = next(line.split("=", 1)[1] for line in out if line.startswith("PASSWORD="))
    return Path(archive), password


def test_single_file_round_trip(tmp_path, capsys):
    src = tmp_path / "a.txt"
    src.write_text("hello gmail", encoding="utf-8")
    out = tmp_path / "out.zip"

    rc = pa.main([str(src), "-o", str(out), "-p", "pw123"])
    assert rc == 0
    assert out.exists()

    archive, password = _parse_stdout(capsys)
    assert archive == out.resolve()
    assert password == "pw123"

    # 外层只暴露 inner.zip
    listing = subprocess.run(
        [SEVEN_ZIP, "l", "-ppw123", str(out)], check=True, capture_output=True, text=True,
    ).stdout
    assert "inner.zip" in listing

    # 两轮解压还原内容
    outer_dir = tmp_path / "outer"
    _extract_outer(out, "pw123", outer_dir)
    inner = outer_dir / "inner.zip"
    assert inner.exists()
    inner_dir = tmp_path / "inner"
    _extract_inner(inner, inner_dir)
    assert (inner_dir / "a.txt").read_text(encoding="utf-8") == "hello gmail"


def test_multiple_files_and_directory_round_trip(tmp_path, capsys):
    f1 = tmp_path / "a.txt"; f1.write_text("A")
    f2 = tmp_path / "b.txt"; f2.write_text("B")
    d = tmp_path / "docs"; d.mkdir()
    (d / "c.txt").write_text("C")
    out = tmp_path / "multi.zip"

    rc = pa.main([str(f1), str(f2), str(d), "-o", str(out)])
    assert rc == 0
    _, password = _parse_stdout(capsys)
    assert password and pa.PASSWORD_LENGTH == len(password)

    outer_dir = tmp_path / "outer"
    _extract_outer(out, password, outer_dir)
    inner_dir = tmp_path / "inner"
    _extract_inner(outer_dir / "inner.zip", inner_dir)

    assert (inner_dir / "a.txt").read_text() == "A"
    assert (inner_dir / "b.txt").read_text() == "B"
    assert (inner_dir / "docs" / "c.txt").read_text() == "C"


def test_default_random_password_is_random(tmp_path, capsys):
    src = tmp_path / "a.txt"; src.write_text("x")

    pa.main([str(src), "-o", str(tmp_path / "r1.zip")])
    _, p1 = _parse_stdout(capsys)
    pa.main([str(src), "-o", str(tmp_path / "r2.zip")])
    _, p2 = _parse_stdout(capsys)

    assert p1 != p2
    assert len(p1) == pa.PASSWORD_LENGTH
    assert set(p1) <= set(pa.PASSWORD_ALPHABET)


def test_wrong_password_cannot_extract(tmp_path, capsys):
    src = tmp_path / "a.txt"; src.write_text("secret")
    out = tmp_path / "out.zip"
    pa.main([str(src), "-o", str(out), "-p", "correctpw"])
    _ = _parse_stdout(capsys)

    proc = subprocess.run(
        [SEVEN_ZIP, "t", "-pwrongpw", str(out)], capture_output=True, text=True,
    )
    assert proc.returncode != 0


def test_custom_output_path_honored(tmp_path, capsys):
    src = tmp_path / "a.txt"; src.write_text("x")
    out = tmp_path / "nested" / "deep" / "final.zip"

    rc = pa.main([str(src), "-o", str(out), "-p", "pw"])
    assert rc == 0
    archive, _ = _parse_stdout(capsys)
    assert archive == out.resolve()
    assert out.exists()


def test_missing_path_errors(tmp_path, capsys):
    rc = pa.main([str(tmp_path / "nope.txt")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "路径不存在" in err


def test_no_paths_errors(tmp_path):
    with pytest.raises(pa.PackError):
        pa.pack([], password="x", output=tmp_path / "x.zip", seven_zip="7z")
