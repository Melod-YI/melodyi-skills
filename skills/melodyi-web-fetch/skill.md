---
name: melodyi-web-fetch
description: "Fetch and extract web page content as markdown using melodyi-web CLI. Use this skill whenever you need to read, extract, or scrape content from a specific URL. This includes: reading articles, extracting documentation, converting web pages to readable format, getting page content for analysis, or when the user pastes a URL and asks 'what does this page say'. The default providers (jina-reader, markdown-new) work without any API key configuration. Prefer this over direct HTTP requests when you need clean, readable content from a web page."
---

# melodyi-web fetch — 网页内容抓取工具

通过 `melodyi-web fetch` 命令抓取指定 URL 的网页内容，并转换为可读的 Markdown 格式。默认提供商无需 API Key，开箱即用。

## 基本用法

```bash
melodyi-web fetch https://example.com
```

抓取完成后，阅读返回的 Markdown 内容，根据用户需求提取关键信息并整理回答。

## 常用参数

### 指定提供商

用 `-p` 或 `--provider` 指定使用特定的抓取提供商。可用的提供商：

| 提供商 | 说明 | 需要 API Key | 特点 |
|--------|------|:---:|------|
| `jina-reader` | Jina Reader | ❌（可选） | 支持 JS 渲染，输出 Markdown，功能最丰富 |
| `markdown-new` | Markdown.new | ❌ | 最简洁，纯 Markdown 转换 |
| `tavily-extract` | Tavily Extract | ✅ | 支持深度提取，可处理动态页面 |
| `exa-contents` | Exa Contents | ✅ | 内容提取，适合结构化数据 |

如果不确定用哪个，不指定 `-p` 即可——系统默认使用 `jina-reader` 和 `markdown-new`，两者都不需要配置。

```bash
# 使用默认提供商（推荐日常使用）
melodyi-web fetch https://docs.python.org/3/tutorial/

# 指定 Jina Reader（需要 JS 渲染的页面）
melodyi-web fetch https://spa-app.com/page -p jina-reader

# 指定 Tavily Extract（需要深度提取）
melodyi-web fetch https://example.com -p tavily-extract
```

### 输出格式

默认输出为文本格式。用 `-o json` 获取结构化 JSON 数据：

```bash
melodyi-web fetch https://example.com -o json
```

JSON 输出包含 `provider`、`url`、`title`、`content`、`response_time_ms`、`metadata` 等字段。需要对抓取结果做程序化处理时使用。通常默认的 text 格式就够了。

### 比对模式

用 `-c` 或 `--comparison` 启用比对模式，让所有配置的提供商都抓取同一页面，结果存入数据库用于对比：

```bash
melodyi-web fetch https://example.com -c
```

日常抓取不需要开启此模式。

## 使用场景

### 阅读文章或文档

用户给出一个 URL 想知道内容时：

```bash
melodyi-web fetch https://blog.example.com/some-article
```

### 提取技术文档

获取 API 文档、库文档等技术资料：

```bash
melodyi-web fetch https://docs.rs/tokio/latest/tokio/
melodyi-web fetch https://react.dev/reference/react
```

### 获取动态渲染页面

对于使用 JavaScript 动态渲染内容的 SPA 应用，Jina Reader 支持浏览器引擎渲染：

```bash
melodyi-web fetch https://dynamic-site.com -p jina-reader
```

## 错误处理

如果抓取失败，命令会输出错误信息和恢复提示：

- **"Request timed out"** — 页面加载太慢，系统会重试或切换提供商
- **"Network connection error"** — 检查网络连接
- **"All providers failed"** — 所有提供商都失败了，可能是目标网站不可访问

遇到超时时，换一个提供商（如从 `markdown-new` 换到 `jina-reader`）通常能解决问题。Jina Reader 有 JS 渲染能力，对于动态页面更可靠。

## 配置

默认的 `jina-reader` 和 `markdown-new` 提供商无需任何配置即可使用。如果需要配置其他提供商（如 `tavily-extract`），编辑 `~/.melodyi-web/config.yaml`：

```bash
# 生成默认配置文件
melodyi-web config init

# 查看当前配置
melodyi-web config show
```
