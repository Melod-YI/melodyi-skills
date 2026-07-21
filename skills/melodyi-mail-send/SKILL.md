---
name: melodyi-mail-send
description: 通过通用 SMTP 协议发送纯文本邮件（QQ 邮箱为内置默认模板，也支持 163/Gmail 等任意 SMTP 邮箱）。当用户想发送邮件、发通知邮件、用 QQ 邮箱发信时使用。
---

# melodyi-mail-send

通过通用 SMTP 协议发送纯文本邮件，QQ 邮箱为内置默认模板。基于 Python 标准库 `email.message.EmailMessage` + `smtplib` 实现，无独立 package、无需安装，直接运行脚本。

## 注意

> [!CAUTION]
> 这是一个 **write** 命令——会真实发送邮件。在正式执行之前，你需要把打算发送的内容（收件人、抄送、密送、标题、正文、附件清单）发给用户确认，并得到允许后才能执行发送。

## 配置（首次使用）

账号信息统一放在用户主目录：`~/.melodyi-skills/melodyi-mail-send/config.yaml`，**只存 SMTP 账号，不含任何邮件内容默认值**。首次使用先生成模板：

```bash
python skills/melodyi-mail-send/scripts/send_mail.py --init
```

生成后编辑填入 `username`（完整邮箱地址）与 `auth_code`。**QQ 授权码不是 QQ 登录密码**，需在 QQ 邮箱「设置 → 账户 → 开启 SMTP 服务」获取（16 位字符串）。

授权码是敏感信息，推荐用环境变量注入不落盘：

```bash
export MELODYI_MAIL_AUTH_CODE="你的授权码"
```

配置优先级：CLI 参数 > 环境变量 `MELODYI_MAIL_*` > 配置文件 > 内置默认（QQ 模板）。

## Usage

```bash
python skills/melodyi-mail-send/scripts/send_mail.py \
  --to <收件人> --subject <标题> --body <纯文本正文> \
  [--cc <抄送>] [--bcc <密送>] [--attach <附件>] [--config <配置路径>]
```

## Flags

| Flag | 必填 | 默认 | 说明 |
|------|:----:|------|------|
| `--to` | ✓ | — | 收件人，逗号分隔多个 |
| `--subject` | ✓ | — | 邮件标题 |
| `--body` | ✓ | — | 纯文本正文 |
| `--cc` | — | — | 抄送，逗号分隔多个 |
| `--bcc` | — | — | 密送，逗号分隔多个（不写入邮件头，仅作为信封收件人） |
| `--attach` | — | — | 附件路径，逗号分隔多个；支持 `~`、相对路径、`..`、Windows 路径，自动规范化 |
| `--config` | — | `~/.melodyi-skills/melodyi-mail-send/config.yaml` | 配置文件路径 |
| `--init` | — | — | 生成配置模板并退出；**已存在则仅提示、不覆盖**（与发信互斥） |

多值字段（`--to`/`--cc`/`--bcc`/`--attach`）均为**单值 + 逗号分隔**，地址与附件路径均自动去重。

## Examples

```bash
# 初始化配置
python skills/melodyi-mail-send/scripts/send_mail.py --init

# 普通发信
python skills/melodyi-mail-send/scripts/send_mail.py \
  --to alice@example.com --subject '你好' --body '这是一封测试邮件'

# 多收件人 + 抄送
python skills/melodyi-mail-send/scripts/send_mail.py \
  --to "alice@example.com,bob@example.com" \
  --cc "carol@example.com" --subject '周报' --body '见附件'

# 带附件（逗号分隔多文件）
python skills/melodyi-mail-send/scripts/send_mail.py \
  --to alice@example.com --subject '报告' --body '请查收' \
  --attach "C:/reports/week.pdf,C:/reports/data.csv"
```

## Tips

- 成功输出 `sent: <message-id>` 与 `recipients: <收件人列表>`；失败输出错误与可操作提示。
- 退出码：`0` 成功；`2` 参数缺失；`3` 配置缺失（先 `--init`）；`4` SMTP/网络错误。
- 附件超 25MB 仅警告不阻断，但 SMTP 服务器可能拒绝。
- 切换其他邮箱：改配置 `host`/`port`/`use_ssl` 即可（如 163 `smtp.163.com:465`，Gmail `smtp.gmail.com:465`）。
- 依赖 pyyaml 解析 config.yaml；若环境无 pyyaml，脚本会报错并提示 `pip install pyyaml`。

## reference

检查 skill 目录下的 `reference/` 目录，如果其中有内容也要读取。
其中可能记录用户的常用收件地址、正文模板等信息（目录可选，不存在不报错）。
