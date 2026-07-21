"""melodyi-mail-send 发信脚本。

通过通用 SMTP 协议发送纯文本邮件，QQ 邮箱为内置默认模板。
仅依赖 Python 标准库 + pyyaml（解析 config.yaml；缺失时友好报错）。

设计要点：
- 邮件内容（收件人/抄送/密送/标题/正文/附件）全部由 CLI 输入，配置只存 SMTP 账号。
- 发件人地址固定来自配置（sender 或回退 username），无 --from。
- 函数化拆分 parse_addresses / parse_paths / load_config / build_message / send，
  便于单测注入 mock SMTP 连接。
"""

from __future__ import annotations

import argparse
import logging
import mimetypes
import os
import smtplib
import socket
import sys
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

# ---------------------------------------------------------------------------
# 内置默认与路径约定
# ---------------------------------------------------------------------------

# 内置默认配置：仅给 QQ 模板的 host/port/use_ssl，凭据无默认必须提供。
BUILTIN_DEFAULT_CONFIG: dict = {
    "smtp": {
        "host": "smtp.qq.com",
        "port": 465,
        "use_ssl": True,
        "username": "",
        "auth_code": "",
        "sender": "",
        "sender_name": "",
    },
    "log": {"level": "INFO"},
}

# 配置目录与文件路径（绝对路径，遵循仓库 ~/.melodyi-skills/<skill>/ 约定）。
CONFIG_DIR = Path.home() / ".melodyi-skills" / "melodyi-mail-send"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.yaml"

# 环境变量前缀；敏感字段 auth_code 推荐走 env 不落盘。
ENV_PREFIX = "MELODYI_MAIL_"

# 环境变量到配置键的映射（仅标量字段）。
ENV_KEY_MAP = {
    "HOST": ("smtp", "host"),
    "PORT": ("smtp", "port"),  # int 转换在加载时做
    "USE_SSL": ("smtp", "use_ssl"),  # bool 转换
    "USERNAME": ("smtp", "username"),
    "AUTH_CODE": ("smtp", "auth_code"),
    "SENDER": ("smtp", "sender"),
    "SENDER_NAME": ("smtp", "sender_name"),
    "LOG_LEVEL": ("log", "level"),
}

# --init 生成的 config.yaml 模板。
CONFIG_TEMPLATE = """\
# melodyi-mail-send 配置
# 仅含 SMTP 账号信息；收件人/标题/正文等邮件内容每次由命令行参数输入。
#
# 优先级：CLI 参数 > 环境变量 MELODYI_MAIL_* > 本文件 > 内置默认。
# 敏感字段 auth_code 推荐用环境变量 MELODYI_MAIL_AUTH_CODE 注入，不在本文件留明文。

smtp:
  host: smtp.qq.com        # QQ 默认；163: smtp.163.com / Gmail: smtp.gmail.com
  port: 465                # 465=SSL, 587=STARTTLS
  use_ssl: true            # port 465 用 true；587 用 false（走 STARTTLS）
  username: ""             # 完整邮箱地址，如 xxx@qq.com
  auth_code: ""            # QQ 授权码（16 位），不是登录密码
  sender: ""               # 发件人地址；留空则用 username
  sender_name: ""          # 发件人显示名（可选）

log:
  level: INFO              # DEBUG / INFO / WARNING
"""

logger = logging.getLogger("melodyi_mail_send")


# ---------------------------------------------------------------------------
# 退出码
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ARG_ERROR = 2
EXIT_CONFIG_ERROR = 3
EXIT_SEND_ERROR = 4


# ---------------------------------------------------------------------------
# 解析工具
# ---------------------------------------------------------------------------

def parse_addresses(raw: str | None) -> list[str]:
    """解析逗号分隔的邮箱地址列表：去空白、去空、去重（保序）。"""
    if not raw:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for part in raw.split(","):
        addr = part.strip()
        if not addr or addr in seen:
            continue
        seen.add(addr)
        result.append(addr)
    return result


def parse_paths(raw: str | None) -> list[Path]:
    """解析逗号分隔的附件路径：展开 ~、resolve 规范化、去重（保序）。

    无论传入 Windows 反斜杠、正斜杠、相对路径、~、含 .. 的路径，
    统一规范化为绝对路径。存在性校验在 build_message 阶段做。
    """
    if not raw:
        return []
    seen: set[str] = set()
    result: list[Path] = []
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        path = Path(token).expanduser().resolve()
        key = str(path).lower()  # Windows 大小写不敏感，去重按小写
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    """读取 yaml 文件；pyyaml 缺失时抛可识别错误。"""
    try:
        import yaml  # type: ignore
    except ImportError as e:  # pragma: no cover - 环境相关
        raise RuntimeError(
            "解析配置需要 pyyaml，请安装：pip install pyyaml"
        ) from e
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"配置文件顶层应为映射：{path}")
    return data


def _deep_merge(base: dict, overlay: dict) -> dict:
    """深合并：overlay 覆盖 base，嵌套 dict 递归合并。"""
    result = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _coerce_env_value(key: str, section: str, field: str, raw: str):
    """环境变量字符串转对应类型。"""
    if key == "PORT":
        return int(raw)
    if key == "USE_SSL":
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return raw


def _env_overrides() -> dict:
    """从 MELODYI_MAIL_* 环境变量收集覆盖项。"""
    overrides: dict = {}
    for env_key, (section, field) in ENV_KEY_MAP.items():
        raw = os.environ.get(ENV_PREFIX + env_key)
        if raw is None or raw == "":
            continue
        value = _coerce_env_value(env_key, section, field, raw)
        overrides.setdefault(section, {})[field] = value
    return overrides


def load_config(config_path: Path | None = None) -> dict:
    """加载配置：内置默认 < 配置文件 < 环境变量。

    返回合并后的完整配置 dict。配置文件不存在时仅用内置默认 + env，
    并不抛错（调用方负责校验 username/auth_code）。
    """
    path = (config_path or DEFAULT_CONFIG_PATH).expanduser().resolve()
    logger.info("加载配置: %s", path)
    cfg = dict(BUILTIN_DEFAULT_CONFIG)
    if path.is_file():
        file_cfg = _load_yaml(path)
        cfg = _deep_merge(cfg, file_cfg)
        logger.debug("已合并配置文件")
    else:
        logger.debug("配置文件不存在，使用内置默认")
    env_ov = _env_overrides()
    if env_ov:
        cfg = _deep_merge(cfg, env_ov)
        logger.debug("已合并环境变量覆盖")
    return cfg


def validate_smtp_config(cfg: dict) -> tuple[str, str, str]:
    """校验 SMTP 必填字段，返回 (username, auth_code, sender)。缺失抛 ValueError。"""
    smtp = cfg.get("smtp", {})
    username = (smtp.get("username") or "").strip()
    auth_code = smtp.get("auth_code") or ""
    if not username or not auth_code:
        raise ValueError(
            "SMTP 账号信息缺失：username 与 auth_code 均必填。"
            f"配置路径：{DEFAULT_CONFIG_PATH}（可用 --init 生成模板）。"
            "auth_code 也可用环境变量 MELODYI_MAIL_AUTH_CODE 注入。"
        )
    sender = (smtp.get("sender") or "").strip() or username
    return username, auth_code, sender


# ---------------------------------------------------------------------------
# 构建邮件
# ---------------------------------------------------------------------------

def build_message(
    *,
    subject: str,
    body: str,
    to: list[str],
    cc: list[str],
    bcc: list[str],
    sender: str,
    sender_name: str,
    attachments: list[Path],
) -> tuple[EmailMessage, list[str], str]:
    """构建 EmailMessage 与信封收件人列表。

    Bcc 不写入任何 header，仅加入信封收件人。返回 (msg, all_recipients, from_addr)。
    """
    logger.info("构建邮件：subject=%r to=%d cc=%d bcc=%d attach=%d",
                subject, len(to), len(cc), len(bcc), len(attachments))
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid()
    if sender_name:
        msg["From"] = formataddr((sender_name, sender))
    else:
        msg["From"] = sender
    if to:
        msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    # bcc 故意不写入 header
    msg.set_content(body)

    for path in attachments:
        if not path.is_file():
            raise FileNotFoundError(f"附件不存在或不可读: {path}")
        ctype, _ = mimetypes.guess_type(str(path))
        if ctype is None:
            maintype, subtype = "application", "octet-stream"
        else:
            maintype, subtype = ctype.split("/", 1)
        data = path.read_bytes()
        msg.add_attachment(
            data, maintype=maintype, subtype=subtype, filename=path.name
        )
        size_kb = len(data) / 1024
        logger.info("附件已附加: %s (%.1f KB, %s/%s)", path.name, size_kb, maintype, subtype)
        if size_kb > 25 * 1024:
            logger.warning("附件 %s 超过 25MB，SMTP 可能拒绝", path.name)

    # 信封收件人 = to + cc + bcc，去重保序
    all_recipients: list[str] = []
    seen: set[str] = set()
    for addr in to + cc + bcc:
        a = addr.strip()
        if a and a not in seen:
            seen.add(a)
            all_recipients.append(a)
    return msg, all_recipients, sender


# ---------------------------------------------------------------------------
# 发送
# ---------------------------------------------------------------------------

def send(
    msg: EmailMessage,
    all_recipients: list[str],
    from_addr: str,
    smtp_cfg: dict,
    *,
    smtp_factory=smtplib.SMTP_SSL,
    smtp_plain_factory=smtplib.SMTP,
) -> str:
    """连接 SMTP 并发送。smtp_factory 可注入 mock。

    返回 message-id。各类异常向上抛，由 main 捕获分类处理。
    """
    host = smtp_cfg["host"]
    port = smtp_cfg["port"]
    use_ssl = smtp_cfg["use_ssl"]
    username = smtp_cfg["username"]
    auth_code = smtp_cfg["auth_code"]

    logger.info("连接 SMTP %s:%s ssl=%s", host, port, use_ssl)
    if use_ssl:
        server = smtp_factory(host, port, timeout=30)
    else:
        server = smtp_plain_factory(host, port, timeout=30)
        server.starttls()
    try:
        server.login(username, auth_code)
        logger.info("登录成功: %s", username)
        refused = server.send_message(msg, from_addr=from_addr, to_addrs=all_recipients)
        if refused:
            logger.warning("部分收件人被服务器拒绝: %s", refused)
        msg_id = msg.get("Message-ID", "(unknown)")
        logger.info("发送完成: %s -> %s", msg_id, all_recipients)
        return msg_id
    finally:
        try:
            server.quit()
        except Exception:  # noqa: BLE001
            logger.debug("quit 异常已忽略")


# ---------------------------------------------------------------------------
# 配置初始化
# ---------------------------------------------------------------------------

def init_config(path: Path, force: bool = False) -> Path:
    """生成 config.yaml 模板。已存在且未 --force 时抛 FileExistsError。"""
    if path.exists() and not force:
        raise FileExistsError(f"配置已存在: {path}（如需覆盖请加 --force）")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    logger.info("已生成配置模板: %s", path)
    return path


# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------

def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="send_mail.py",
        description="通过 SMTP 发送纯文本邮件（QQ 邮箱为内置默认模板）。",
    )
    p.add_argument("--to", default="", help="收件人，逗号分隔多个")
    p.add_argument("--cc", default="", help="抄送，逗号分隔多个")
    p.add_argument("--bcc", default="", help="密送，逗号分隔多个")
    p.add_argument("--subject", default="", help="邮件标题")
    p.add_argument("--body", default="", help="纯文本正文")
    p.add_argument("--attach", default="", help="附件路径，逗号分隔多个")
    p.add_argument("--config", default=str(DEFAULT_CONFIG_PATH),
                   help=f"配置文件路径（默认 {DEFAULT_CONFIG_PATH}）")
    p.add_argument("--init", action="store_true", help="生成配置模板并退出")
    p.add_argument("--force", action="store_true", help="--init 时覆盖已存在的配置")
    return p


def main(argv: list[str] | None = None) -> int:
    """入口，返回退出码。"""
    args = build_arg_parser().parse_args(argv)
    setup_logging("INFO")  # init 分支先 INFO，正式发送时按配置重设

    if args.init:
        path = Path(args.config).expanduser().resolve()
        try:
            init_config(path, force=args.force)
        except FileExistsError as e:
            print(f"错误：{e}", file=sys.stderr)
            return EXIT_CONFIG_ERROR
        print(f"已生成配置模板：{path}")
        print("请编辑填入 username 与 auth_code（QQ 授权码，非登录密码）。")
        return EXIT_OK

    # 正式发信：加载配置后按其 log.level 重设日志
    config_path = Path(args.config).expanduser().resolve()
    cfg = load_config(config_path)
    setup_logging(cfg.get("log", {}).get("level", "INFO"))

    # 参数校验
    to = parse_addresses(args.to)
    cc = parse_addresses(args.cc)
    bcc = parse_addresses(args.bcc)
    subject = args.subject.strip()
    body = args.body
    attachments = parse_paths(args.attach)

    missing = []
    if not to:
        missing.append("--to")
    if not subject:
        missing.append("--subject")
    if not body:
        missing.append("--body")
    if missing:
        print(f"错误：缺少必填参数：{', '.join(missing)}", file=sys.stderr)
        return EXIT_ARG_ERROR

    # 配置校验
    try:
        username, auth_code, sender = validate_smtp_config(cfg)
    except ValueError as e:
        print(f"错误：{e}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    smtp_cfg = dict(cfg["smtp"])
    smtp_cfg["username"] = username
    smtp_cfg["auth_code"] = auth_code
    sender_name = (cfg["smtp"].get("sender_name") or "").strip()

    # 构建邮件
    try:
        msg, all_recipients, from_addr = build_message(
            subject=subject, body=body, to=to, cc=cc, bcc=bcc,
            sender=sender, sender_name=sender_name, attachments=attachments,
        )
    except FileNotFoundError as e:
        print(f"错误：{e}", file=sys.stderr)
        return EXIT_ARG_ERROR

    # 发送
    try:
        msg_id = send(msg, all_recipients, from_addr, smtp_cfg)
    except smtplib.SMTPAuthenticationError as e:
        logger.exception("SMTP 认证失败")
        print(f"错误：SMTP 认证失败。请确认 username 为完整邮箱地址、auth_code 为正确的"
              f"授权码（非登录密码）。服务器返回：{e}", file=sys.stderr)
        return EXIT_SEND_ERROR
    except (socket.gaierror, socket.timeout, TimeoutError) as e:
        logger.exception("网络错误")
        print(f"错误：网络问题，请检查 host 与网络连通性：{e}", file=sys.stderr)
        return EXIT_SEND_ERROR
    except smtplib.SMTPException as e:
        logger.exception("SMTP 错误")
        print(f"错误：SMTP 服务器返回错误：{e}", file=sys.stderr)
        return EXIT_SEND_ERROR

    print(f"sent: {msg_id}")
    print(f"recipients: {', '.join(all_recipients)}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
