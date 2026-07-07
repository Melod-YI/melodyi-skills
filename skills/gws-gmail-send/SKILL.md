---
name: gws-gmail-send
description: "Gmail: Send an email."
---

# gmail send

Send an email

## 注意
> [!CAUTION]
> This is a **write** command — confirm with the user before executing.

你在正式执行发送之前，需要把你打算发送的内容（地址、标题、正文、附件等信息）发送给用户确认，并得到允许后才能发送。

## Usage

```bash
gws gmail +send --to <EMAILS> --subject <SUBJECT> --body <TEXT>
```

## Flags

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--to` | ✓ | — | Recipient email address(es), comma-separated |
| `--subject` | ✓ | — | Email subject |
| `--body` | ✓ | — | Email body (plain text, or HTML with --html) |
| `--from` | — | — | Sender address (for send-as/alias; omit to use account default) |
| `--attach` | — | — | Attach a file (can be specified multiple times) |
| `--cc` | — | — | CC email address(es), comma-separated |
| `--bcc` | — | — | BCC email address(es), comma-separated |
| `--html` | — | — | Treat --body as HTML content (default is plain text) |
| `--dry-run` | — | — | Show the request that would be sent without executing it |
| `--draft` | — | — | Save as draft instead of sending |

## Examples

```bash
gws gmail +send --to alice@example.com --subject 'Hello' --body 'Hi Alice!'
gws gmail +send --to alice@example.com --subject 'Hello' --body 'Hi!' --cc bob@example.com
gws gmail +send --to alice@example.com --subject 'Hello' --body '<b>Bold</b> text' --html
gws gmail +send --to alice@example.com --subject 'Hello' --body 'Hi!' --from alias@example.com
gws gmail +send --to alice@example.com --subject 'Report' --body 'See attached' -a report.pdf
gws gmail +send --to alice@example.com --subject 'Files' --body 'Two files' -a a.pdf -a b.csv
gws gmail +send --to alice@example.com --subject 'Hello' --body 'Hi!' --draft
```

## Tips

- Handles RFC 5322 formatting, MIME encoding, and base64 automatically.
- Use --from to send from a configured send-as alias instead of your primary address.
- Use -a/--attach to add file attachments. Can be specified multiple times. Total size limit: 25MB.
- With --html, use fragment tags (<p>, <b>, <a>, <br>, etc.) — no <html>/<body> wrapper needed.
- Use --draft to save the message as a draft instead of sending it immediately.

## reference

检查skill目录下的 reference 目录，如果其中有内容也要读取。
其中可能会记录用户的常见邮箱地址、发送邮件的内容要求、模板等信息。

## 附件流程

gmail的附件会有"类型"、"大小"的限制，我希望在附件附送前统一进行压缩。
该行为仅为绕开限制而非保护文件，因此不需要考虑密码安全相关的问题。

### 附件打包

调用脚本 `scripts/pack_attachments.py` 完成带密码压缩：

```bash
python skills/gws-gmail-send/scripts/pack_attachments.py <文件或文件夹> [<文件或文件夹> ...] [-p <密码>] [-o <输出zip路径>]
```

- 入参为一个或多个文件/文件夹路径。
- `-p/--password` 指定 zip 密码；**省略时随机生成**。
- `-o/--output` 指定最终 zip 路径；省略时写入当前目录 `gmail_attachments_<时间戳>.zip`。
- 脚本 stdout 输出两行供解析：
  - `ARCHIVE=<最终 zip 绝对路径>`
  - `PASSWORD=<密码>`

### 发送流程

1. 运行上述脚本，从 `ARCHIVE=` 取得最终 zip 路径、`PASSWORD=` 取得密码。
2. 用 `gws gmail +send ... --attach <ARCHIVE 路径>` 发送。
3. **正文必须说明解压方式**：用密码解压 zip 即得原始文件。示例正文：

   > 附件为带密码 zip，解压密码：`<密码>`。
4. 发送完成后，清理生成的zip文件。
