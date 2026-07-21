# melodyi-mail-send 设计文档

- 日期：2026-07-21
- 状态：已通过设计评审，待实现

## 1. 目标

在 melodyi-skills 仓库下新增一个发邮件 skill，通过通用 SMTP 协议发送邮件，QQ 邮箱作为内置默认模板。用户选用**方案 B（纯 skill）**：无独立 package、无安装，脚本直接放在 skill 目录下，用 Python 标准库 `email.message.EmailMessage` + `smtplib` 实现。

只实现 `send`（发信）与 `--init`（生成配置模板）两个动作，不做收件、不做草稿、不做 HTML 正文、不做附件密码打包。

## 2. 形态与文件布局

```
skills/melodyi-mail-send/
├── SKILL.md                      # skill 定义 + 使用手册（Claude 运行时读）
└── scripts/
    └── send_mail.py              # argparse 脚本，标准库实现
tests/
└── melodyi-mail-send/
    ├── conftest.py               # 把 scripts/ 注入 sys.path
    └── test_send_mail.py         # 单测
```

- 脚本用 argparse（CLAUDE.md：「argparse 用于简单脚本」，本场景属此类，无外部依赖）。
- 调用方式：`python skills/melodyi-mail-send/scripts/send_mail.py ...`
- 同步：`sync_skills.py` 会复制到隔离 workspace 的 `.claude/skills/melodyi-mail-send/`。

## 3. 配置

配置文件：`~/.melodyi-skills/melodyi-mail-send/config.yaml`，**仅含 SMTP 账号信息，不含任何邮件内容默认值**（收件人/抄送/标题/正文/附件全部由 CLI 输入）。

```yaml
smtp:
  host: smtp.qq.com       # QQ 默认模板，可改 163/Gmail 等
  port: 465
  use_ssl: true           # 465=SMTP_SSL；587=false 走 STARTTLS
  username: ""            # 完整邮箱地址，如 xxx@qq.com
  auth_code: ""           # QQ 授权码（16位），非登录密码
  sender: ""              # 发件人地址；留空则用 username
  sender_name: ""         # 发件人显示名（可选）
log:
  level: INFO
```

- 优先级：CLI 参数 > 环境变量（`MELODYI_MAIL_*`，如 `MELODYI_MAIL_AUTH_CODE`，敏感字段推荐走 env 不落盘）> 配置文件 > 内置默认。
- 内置默认仅给 host/port/use_ssl（QQ 模板）；`username/auth_code` 无默认，必须提供。
- 配置加载器内置默认指向 `~/.melodyi-skills/melodyi-mail-send/config.yaml`；找不到则用全默认值并提示先 `--init`。

## 4. CLI 接口

两个动作：发信、初始化配置。

```
# 发信
python skills/melodyi-mail-send/scripts/send_mail.py \
  --to "a@x.com,b@x.com"        # 必填，逗号分隔多个收件人
  --subject <标题>               # 必填
  --body <纯文本正文>            # 必填
  [--cc "b@x.com,c@x.com"]
  [--bcc "..."]
  [--attach "f1.pdf,f2.csv"]     # 逗号分隔多个文件路径
  [--config <配置路径>]          # 可选，默认 ~/.melodyi-skills/melodyi-mail-send/config.yaml

# 初始化配置模板
python skills/melodyi-mail-send/scripts/send_mail.py --init
# 仅在没有配置时生成模板；已存在则仅提示、不覆盖（无强制覆盖出口）
```

- 所有多值字段（to/cc/bcc/attach）均为**单值 + 逗号分隔**，argparse 用默认 `store`（不用 `append`）。
- `--init` 与发信参数互斥：给 `--init` 只生成配置、不发信；已存在配置时不覆盖、仅提示并退出码 0。
- 无 `--from`（发件人固定来自配置 sender/username）、无 `--dry-run`、无 `--print-config`、无 `--body-file`、无 `--force`。
- 发送前确认由 SKILL.md 的 CAUTION 约定保证（Claude 把内容给用户确认后才执行命令）。
- 退出码：`0` 成功；`2` 参数缺失；`3` 配置缺失；非 0 含文件不存在、SMTP 错误等。
- 输出：成功打印 `sent: <message-id>` + 收件人清单；失败打印错误与可操作提示。

## 5. 发送逻辑与错误处理

单文件 `send_mail.py`，函数划分便于测试：`parse_addresses`、`parse_paths`、`load_config`、`build_message`、`send`、`main`。

1. **解析参数** → 校验必填 `--to/--subject/--body`，缺一退出码 2。`--init` 走配置生成分支，提前 return。
2. **加载配置** → 合并优先级（内置默认 ← 配置文件 ← 环境变量 `MELODYI_MAIL_*`）。校验 `username/auth_code` 非空，缺失退出码 3 并提示先 `--init`。
3. **构建 `EmailMessage`**：
   - `From`：`sender` 或回退 `username`，带 `sender_name` 时用 `"名" <addr>` 格式。
   - `To`/`Cc`：写入 header（逗号分隔）。
   - `Bcc`：**不写入任何 header**，仅加入实际收件人列表（信封收件人）。
   - `Subject`：直接设，含非 ASCII 由 `EmailMessage` 自动 RFC2047 编码。
   - `set_content(body)`：纯文本。
   - `add_attachment`：`maintype/subtype` 按 `mimetypes.guess_type` 推断，读 bytes 附加，日志记录大小。
4. **连接 SMTP**：`use_ssl=true` → `SMTP_SSL(host, port, timeout=30)`；`use_ssl=false` → `SMTP(host, port, timeout=30)` + `.starttls()`。`.login(username, auth_code)`。入口/登录/发件/退出均有 INFO 日志，凭据绝不入日志。
5. **发送**：`server.send_message(msg, from_addr=sender, to_addrs=all_recipients)`，`all_recipients = to + cc + bcc`（去重）。
6. **收尾**：`quit()`；打印 `sent: <msg-id>` + 收件人清单。

**路径规范化**（`parse_paths`）：按逗号切分 → `strip` → 去空 → `Path.expanduser()`（展开 `~`）→ `Path.resolve()`（绝对化、统一分隔符、消解 `..`/`.`）→ 去重（按规范化后路径）。存在性/可读校验在 `build_message` 阶段做，不存在则 `FileNotFoundError` 并指出规范化后路径。

**地址解析**（`parse_addresses`）：按逗号切分 → `strip` → 去空 → 去重。

**错误处理**（每类对应退出码 + 可操作提示）：
- `socket.gaierror`/`timeout` → 网络问题，提示检查 host/网络。
- `smtplib.SMTPAuthenticationError` → 授权码/账号错，提示重生成授权码、确认 `username` 是完整邮箱。
- `smtplib.SMTPException`/其他 → 打印服务器返回，提示看日志。
- `FileNotFoundError`（附件）→ 指出哪个文件。
- 任何异常 `logging.exception` 记完整 traceback 后退出。

日志：`logging` 输出 stdout，level 由配置 `log.level` 控制；核心方法入口出口都有日志。

## 6. SKILL.md 约定

- frontmatter：`name: melodyi-mail-send`，`description`：触发条件（如「通过 SMTP 发送邮件，默认 QQ 邮箱」）。
- 顶部 `[CAUTION]`：write 命令——发送前必须把收件人/抄送/标题/正文/附件清单发给用户确认，得到允许后才执行。
- Flags 表：`--to/--cc/--bcc/--subject/--body/--attach/--config/--init`，逗号分隔多值规则。
- Examples：发信、带抄送、带附件、初始化配置各一例。
- `reference/` 目录约定：可存常用收件地址、正文模板，Claude 发信前可读取（可选，不存在不报错）。
- 配置说明：账号在 `~/.melodyi-skills/melodyi-mail-send/config.yaml`，首次用 `--init` 生成；授权码建议走 `MELODYI_MAIL_AUTH_CODE` 环境变量不落盘。
- 提示：附件超 25MB 仅警告不阻断；QQ 授权码非登录密码。

## 7. 测试

放 `tests/melodyi-mail-send/`，`conftest.py` 把 `skills/melodyi-mail-send/scripts` 注入 `sys.path`。**不连真实 SMTP**，用 `unittest.mock` 拦截 `smtplib.SMTP_SSL`，断言调用参数。用例：

1. 地址解析：`--to "a@x.com,b@x.com"` → `[a,b]`；逗号 + 去重。
2. Bcc 不泄漏：构建的 `msg` header 有 To/Cc、无 Bcc；信封收件人含 bcc。
3. EmailMessage 构建：中文 Subject 正确编码；From 带 sender_name 格式正确；正文与附件正确附加。
4. 附件：多附件按序附加、maintype/subtype 推断正确；不存在抛 `FileNotFoundError` 并退出码非 0；路径规范化（`~`/相对/`..`/反斜杠均能解析）。
5. 配置优先级：内置默认 < 配置文件 < `MELODYI_MAIL_AUTH_CODE`；`username/auth_code` 缺失报错。
6. 发送主流程：mock `SMTP_SSL`，验证 `login(username, auth_code)`、`send_message` 用了正确的 `from_addr` 与 `to_addrs=to+cc+bcc`、`quit` 被调用；成功 stdout 含 `sent:`。
7. `--init`：临时目录生成 config.yaml，含 QQ 模板默认且 `username/auth_code` 为空；已存在配置时不覆盖（用户自定义内容保留）、仅提示并退出码 0。
8. 参数校验：缺 `--to/--subject/--body` 退出码 2。

## 8. 非目标

- 不实现收件（IMAP/POP3）。
- 不实现 HTML 正文（仅纯文本）。
- 不实现 `--draft`（SMTP 无草稿概念）。
- 不实现附件密码打包（gws-gmail-send 的 `pack_attachments.py` 流程不引入）。
- 不引入第三方依赖（仅标准库）。
