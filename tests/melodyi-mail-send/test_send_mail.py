"""send_mail.py 单测。

不连真实 SMTP：注入 FakeSMTP 工厂，断言调用参数。
覆盖：地址解析、路径规范化、邮件构建、Bcc 不泄漏、附件、配置优先级、
发送主流程、--init、参数校验。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import send_mail


# ---------------------------------------------------------------------------
# 辅助：假 SMTP 服务器
# ---------------------------------------------------------------------------

class FakeSMTP:
    """记录调用参数的假 SMTP_SSL/SMTP。"""

    def __init__(self, host="smtp.qq.com", port=465, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.login_args = None
        self.send_args = None
        self.quit_called = False
        self.starttls_called = False

    def starttls(self) -> None:
        self.starttls_called = True

    def login(self, user, pwd) -> None:
        self.login_args = (user, pwd)

    def send_message(self, msg, from_addr=None, to_addrs=None):
        self.send_args = (from_addr, list(to_addrs) if to_addrs else [], msg)
        return {}  # 无被拒收件人

    def quit(self) -> None:
        self.quit_called = True


def make_smtp_cfg(**overrides) -> dict:
    cfg = {
        "host": "smtp.qq.com",
        "port": 465,
        "use_ssl": True,
        "username": "me@qq.com",
        "auth_code": "secretcode",
    }
    cfg.update(overrides)
    return cfg


# ---------------------------------------------------------------------------
# 1. 地址解析
# ---------------------------------------------------------------------------

class TestParseAddresses:
    def test_comma_split(self):
        assert send_mail.parse_addresses("a@x.com,b@x.com") == ["a@x.com", "b@x.com"]

    def test_dedupe_preserve_order(self):
        assert send_mail.parse_addresses("a@x.com,b@x.com,a@x.com") == ["a@x.com", "b@x.com"]

    def test_whitespace_and_empty(self):
        assert send_mail.parse_addresses(" a@x.com , , b@x.com ,") == ["a@x.com", "b@x.com"]

    def test_none_or_empty(self):
        assert send_mail.parse_addresses(None) == []
        assert send_mail.parse_addresses("") == []


# ---------------------------------------------------------------------------
# 2. 路径规范化
# ---------------------------------------------------------------------------

class TestParsePaths:
    def test_basic_split(self, tmp_path):
        f1 = tmp_path / "a.txt"; f1.touch()
        f2 = tmp_path / "b.txt"; f2.touch()
        raw = f"{f1},{f2}"
        result = send_mail.parse_paths(raw)
        assert [p.name for p in result] == ["a.txt", "b.txt"]
        # 全部已 resolve 为绝对路径
        assert all(p.is_absolute() for p in result)

    def test_dedupe(self, tmp_path):
        f1 = tmp_path / "a.txt"; f1.touch()
        result = send_mail.parse_paths(f"{f1},{f1}")
        assert len(result) == 1

    def test_dotdot_and_relative_resolved(self, tmp_path, monkeypatch):
        sub = tmp_path / "sub"; sub.mkdir()
        f = sub / "a.txt"; f.touch()
        monkeypatch.chdir(sub)
        # 相对路径 + .. 应规范化为绝对路径
        result = send_mail.parse_paths("../sub/a.txt")
        assert len(result) == 1
        assert result[0].resolve() == f.resolve()

    def test_empty(self):
        assert send_mail.parse_paths(None) == []
        assert send_mail.parse_paths("") == []


# ---------------------------------------------------------------------------
# 3. 邮件构建
# ---------------------------------------------------------------------------

class TestBuildMessage:
    def test_basic_headers_and_recipients(self):
        msg, recipients, from_addr = send_mail.build_message(
            subject="测试标题", body="正文",
            to=["a@x.com"], cc=["c@x.com"], bcc=["b@x.com"],
            sender="me@qq.com", sender_name="", attachments=[],
        )
        assert msg["Subject"] == "测试标题"  # EmailMessage 自动编码中文
        assert msg["From"] == "me@qq.com"
        assert msg["To"] == "a@x.com"
        assert msg["Cc"] == "c@x.com"
        # Bcc 不出现在 header
        assert msg.get("Bcc") is None
        # 信封收件人含 bcc，去重保序
        assert recipients == ["a@x.com", "c@x.com", "b@x.com"]
        assert from_addr == "me@qq.com"

    def test_sender_name_format(self):
        msg, _, _ = send_mail.build_message(
            subject="s", body="b", to=["a@x.com"], cc=[], bcc=[],
            sender="me@qq.com", sender_name="小机器人", attachments=[],
        )
        # formataddr 产出 "小机器人" <me@qq.com>
        assert "me@qq.com" in msg["From"]
        assert "小机器人" in msg["From"]

    def test_multiple_to_cc_in_headers(self):
        msg, recipients, _ = send_mail.build_message(
            subject="s", body="b",
            to=["a@x.com", "b@x.com"], cc=["c@x.com", "d@x.com"], bcc=[],
            sender="me@qq.com", sender_name="", attachments=[],
        )
        assert "a@x.com" in msg["To"] and "b@x.com" in msg["To"]
        assert recipients == ["a@x.com", "b@x.com", "c@x.com", "d@x.com"]

    def test_recipient_dedupe(self):
        # to/cc/bcc 中重复地址在信封收件人中去重
        _, recipients, _ = send_mail.build_message(
            subject="s", body="b",
            to=["a@x.com"], cc=["a@x.com"], bcc=["a@x.com"],
            sender="me@qq.com", sender_name="", attachments=[],
        )
        assert recipients == ["a@x.com"]


# ---------------------------------------------------------------------------
# 4. 附件
# ---------------------------------------------------------------------------

class TestAttachments:
    def test_multiple_attachments_in_order(self, tmp_path):
        f1 = tmp_path / "a.txt"; f1.write_bytes(b"hello")
        f2 = tmp_path / "b.json"; f2.write_bytes(b'{"k":1}')
        msg, _, _ = send_mail.build_message(
            subject="s", body="b", to=["a@x.com"], cc=[], bcc=[],
            sender="me@qq.com", sender_name="",
            attachments=[f1.resolve(), f2.resolve()],
        )
        names = [part.get_filename() for part in msg.iter_attachments()]
        assert names == ["a.txt", "b.json"]
        # maintype/subtype 推断
        parts = list(msg.iter_attachments())
        types = [(p.get_content_maintype(), p.get_content_subtype()) for p in parts]
        assert ("text", "plain") in types
        assert ("application", "json") in types

    def test_missing_attachment_raises(self, tmp_path):
        missing = tmp_path / "nope.txt"
        with pytest.raises(FileNotFoundError):
            send_mail.build_message(
                subject="s", body="b", to=["a@x.com"], cc=[], bcc=[],
                sender="me@qq.com", sender_name="",
                attachments=[missing],
            )


# ---------------------------------------------------------------------------
# 5. 配置优先级与校验
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_builtin_default_when_no_file(self, tmp_path, monkeypatch):
        # 无配置文件，仅内置默认
        monkeypatch.delenv("MELODYI_MAIL_AUTH_CODE", raising=False)
        monkeypatch.delenv("MELODYI_MAIL_USERNAME", raising=False)
        cfg = send_mail.load_config(tmp_path / "missing.yaml")
        assert cfg["smtp"]["host"] == "smtp.qq.com"
        assert cfg["smtp"]["port"] == 465
        assert cfg["smtp"]["use_ssl"] is True
        assert cfg["smtp"]["username"] == ""

    def test_file_overrides_builtin(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MELODYI_MAIL_AUTH_CODE", raising=False)
        path = tmp_path / "config.yaml"
        path.write_text("smtp:\n  host: smtp.163.com\n  username: me@163.com\n  auth_code: 'c1'\n",
                        encoding="utf-8")
        cfg = send_mail.load_config(path)
        assert cfg["smtp"]["host"] == "smtp.163.com"
        assert cfg["smtp"]["username"] == "me@163.com"
        # 未覆盖的字段保留内置默认
        assert cfg["smtp"]["port"] == 465

    def test_env_overrides_file(self, tmp_path, monkeypatch):
        path = tmp_path / "config.yaml"
        path.write_text("smtp:\n  username: me@qq.com\n  auth_code: 'filecode'\n",
                        encoding="utf-8")
        monkeypatch.setenv("MELODYI_MAIL_AUTH_CODE", "envcode")
        cfg = send_mail.load_config(path)
        assert cfg["smtp"]["auth_code"] == "envcode"
        assert cfg["smtp"]["username"] == "me@qq.com"

    def test_env_port_and_ssl_coerce(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MELODYI_MAIL_PORT", "587")
        monkeypatch.setenv("MELODYI_MAIL_USE_SSL", "false")
        cfg = send_mail.load_config(tmp_path / "missing.yaml")
        assert cfg["smtp"]["port"] == 587
        assert cfg["smtp"]["use_ssl"] is False

    def test_validate_missing_creds(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MELODYI_MAIL_AUTH_CODE", raising=False)
        monkeypatch.delenv("MELODYI_MAIL_USERNAME", raising=False)
        cfg = send_mail.load_config(tmp_path / "missing.yaml")
        with pytest.raises(ValueError, match="username"):
            send_mail.validate_smtp_config(cfg)

    def test_sender_falls_back_to_username(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MELODYI_MAIL_USERNAME", "me@qq.com")
        monkeypatch.setenv("MELODYI_MAIL_AUTH_CODE", "c1")
        cfg = send_mail.load_config(tmp_path / "missing.yaml")
        username, auth_code, sender = send_mail.validate_smtp_config(cfg)
        assert username == "me@qq.com"
        assert sender == "me@qq.com"


# ---------------------------------------------------------------------------
# 6. 发送主流程
# ---------------------------------------------------------------------------

class TestSend:
    def test_ssl_flow(self):
        fake = FakeSMTP()
        msg, recipients, from_addr = send_mail.build_message(
            subject="s", body="b", to=["a@x.com"], cc=["c@x.com"], bcc=["b@x.com"],
            sender="me@qq.com", sender_name="", attachments=[],
        )
        msg_id = send_mail.send(
            msg, recipients, from_addr, make_smtp_cfg(),
            smtp_factory=lambda host, port, timeout=30: fake,
            smtp_plain_factory=lambda *a, **k: fake,
        )
        assert fake.login_args == ("me@qq.com", "secretcode")
        send_from, send_to, sent_msg = fake.send_args
        assert send_from == "me@qq.com"
        assert send_to == ["a@x.com", "c@x.com", "b@x.com"]
        assert sent_msg is msg
        assert fake.quit_called is True
        assert fake.starttls_called is False
        assert msg_id == msg["Message-ID"]

    def test_starttls_flow(self):
        fake = FakeSMTP()
        msg, recipients, from_addr = send_mail.build_message(
            subject="s", body="b", to=["a@x.com"], cc=[], bcc=[],
            sender="me@qq.com", sender_name="", attachments=[],
        )
        send_mail.send(
            msg, recipients, from_addr, make_smtp_cfg(use_ssl=False, port=587),
            smtp_factory=lambda *a, **k: fake,
            smtp_plain_factory=lambda host, port, timeout=30: fake,
        )
        assert fake.starttls_called is True
        assert fake.quit_called is True


# ---------------------------------------------------------------------------
# 7. --init
# ---------------------------------------------------------------------------

class TestInitConfig:
    def test_generates_template(self, tmp_path):
        path = tmp_path / "config.yaml"
        created = send_mail.init_config(path)
        assert created is True
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "smtp.qq.com" in text
        assert "username" in text and "auth_code" in text

    def test_existing_not_overwritten(self, tmp_path):
        path = tmp_path / "config.yaml"
        send_mail.init_config(path)
        # 写入用户自定义内容
        path.write_text("smtp:\n  username: custom@qq.com\n", encoding="utf-8")
        # 再次 init：不覆盖，用户内容保留
        created = send_mail.init_config(path)
        assert created is False
        assert "custom@qq.com" in path.read_text(encoding="utf-8")

    def test_init_via_main_creates(self, tmp_path, capsys):
        path = tmp_path / "config.yaml"
        rc = send_mail.main(["--init", "--config", str(path)])
        assert rc == send_mail.EXIT_OK
        assert path.exists()
        out = capsys.readouterr().out
        assert "已生成配置模板" in out

    def test_init_via_main_existing(self, tmp_path, capsys):
        path = tmp_path / "config.yaml"
        send_mail.init_config(path)
        rc = send_mail.main(["--init", "--config", str(path)])
        assert rc == send_mail.EXIT_OK
        out = capsys.readouterr().out
        assert "配置已存在" in out


# ---------------------------------------------------------------------------
# 8. 参数校验
# ---------------------------------------------------------------------------

class TestArgValidation:
    def test_missing_to(self, tmp_path, monkeypatch, capsys):
        monkeypatch.delenv("MELODYI_MAIL_AUTH_CODE", raising=False)
        monkeypatch.delenv("MELODYI_MAIL_USERNAME", raising=False)
        rc = send_mail.main([
            "--subject", "s", "--body", "b",
            "--config", str(tmp_path / "missing.yaml"),
        ])
        assert rc == send_mail.EXIT_ARG_ERROR
        err = capsys.readouterr().err
        assert "--to" in err

    def test_missing_subject(self, tmp_path, monkeypatch, capsys):
        monkeypatch.delenv("MELODYI_MAIL_AUTH_CODE", raising=False)
        monkeypatch.delenv("MELODYI_MAIL_USERNAME", raising=False)
        rc = send_mail.main([
            "--to", "a@x.com", "--body", "b",
            "--config", str(tmp_path / "missing.yaml"),
        ])
        assert rc == send_mail.EXIT_ARG_ERROR

    def test_missing_config_creds(self, tmp_path, monkeypatch, capsys):
        # 参数齐全但配置缺凭据 -> EXIT_CONFIG_ERROR
        monkeypatch.delenv("MELODYI_MAIL_AUTH_CODE", raising=False)
        monkeypatch.delenv("MELODYI_MAIL_USERNAME", raising=False)
        rc = send_mail.main([
            "--to", "a@x.com", "--subject", "s", "--body", "b",
            "--config", str(tmp_path / "missing.yaml"),
        ])
        assert rc == send_mail.EXIT_CONFIG_ERROR
