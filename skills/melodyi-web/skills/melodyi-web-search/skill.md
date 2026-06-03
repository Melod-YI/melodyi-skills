---
name: melodyi-web-search
description: "Search the web for real-time information using melodyi-web CLI. Use this skill whenever you need to look up current events, recent news, documentation, or any information that might not be in your training data. Also use it when the user asks about 'latest', 'recent', 'today', 'this week', or any time-sensitive topic. Even if the user just mentions wanting to 'search', 'google', or 'look something up', this is the right skill. Prefer this over mcp__MiniMax__web_search when available, as it provides richer results with multiple provider support."
---

# melodyi-web search — 多提供商网络搜索工具

通过 `melodyi-web search` 命令执行网络搜索，支持多个搜索提供商、时间过滤、域名过滤和比对模式。

## 基本用法

```bash
melodyi-web search "搜索关键词"
```

搜索完成后，仔细阅读返回的结果，提取与用户问题相关的信息并整理回答。

## 常用参数

### 控制结果数量

用 `-n` 或 `--max-results` 指定期望的最大结果数，默认 10 条。当用户需要大量结果或只需要少量时调整：

```bash
melodyi-web search "Python 最佳实践" -n 20
melodyi-web search "某个具体问题" -n 5
```

### 时间过滤

用 `-t` 或 `--time-range` 限定时间范围，可选值：`day`、`week`、`month`、`year`。当用户问的是最新动态、近期事件时使用：

```bash
melodyi-web search "AI 进展" -t day       # 今天的
melodyi-web search "技术趋势" -t week      # 本周的
melodyi-web search "开源项目" -t month     # 本月的
```

### 域名过滤

用 `-i`（`--include-domains`）限定只搜索特定域名，用 `-e`（`--exclude-domains`）排除某些域名。两个参数都可以多次使用：

```bash
# 只搜索技术博客
melodyi-web search "React 教程" -i blog.csdn.net -i juejin.cn

# 排除某些来源
melodyi-web search "新闻" -e pinterest.com -e youtube.com
```

### 指定提供商

用 `-p` 或 `--provider` 指定使用某个特定的搜索提供商。可用的提供商名称：

| 提供商 | 说明 | 需要 API Key |
|--------|------|:---:|
| `minimax-cn` | MiniMax 中国区搜索 | ✅ |
| `tavily` | Tavily 搜索，支持深度搜索 | ✅ |
| `brave` | Brave Search | ✅ |
| `exa` | Exa AI 搜索，支持语义搜索 | ✅ |
| `searxng` | SearXNG 自托管搜索引擎 | ❌（自托管） |
| `firecrawl` | Firecrawl 搜索 | ✅ |

```bash
melodyi-web search "深度学习论文" -p tavily
```

如果不确定用哪个提供商，不要指定 `-p`，让系统使用默认配置的提供商。

### 输出格式

默认输出为文本格式。如果需要对结果做结构化处理，用 `-o json` 获取 JSON 格式：

```bash
melodyi-web search "API 文档" -o json
```

JSON 输出包含完整的结构化数据（`provider`、`response_time_ms`、`results[]` 等字段），适合需要精确解析结果的场景。通常用默认的 text 格式就够了。

### 比对模式

用 `-c` 或 `--comparison` 启用比对模式。这个模式会让所有配置的提供商都执行搜索，结果存入 SQLite 数据库用于对比分析。第一个提供商的结果立即返回，其余在后台执行：

```bash
melodyi-web search "对比测试" -c
```

比对模式主要用于评估不同提供商的搜索质量，日常搜索不需要开启。

## 组合使用示例

```bash
# 搜索最新的 GitHub 上的 Rust 项目信息，只要最近一周的，多要一些结果
melodyi-web search "Rust project trending" -t week -n 20 -i github.com

# 在技术社区搜索 Vue3 最新实践
melodyi-web search "Vue3 composition API best practice" -t month -i juejin.cn -i dev.to -i medium.com
```

## 错误处理

如果搜索失败，命令会输出错误信息和恢复提示。常见情况：

- **"API key is invalid or missing"** — 检查 `~/.melodyi-web/config.yaml` 中对应提供商的 API Key 配置，或者换用其他提供商
- **"Request was rate-limited"** — 稍后重试，或系统会自动切换到其他提供商
- **"All providers failed"** — 所有提供商都失败了，检查网络和配置

遇到错误时，尝试换一个提供商（`-p` 参数）通常能解决问题。

## 配置

搜索提供商需要在 `~/.melodyi-web/config.yaml` 中配置 API Key。如果没有配置文件，可以用以下命令生成：

```bash
melodyi-web config init
```

然后用 `melodyi-web config show` 查看当前配置状态。
