# melodyi-web

多提供商搜索与网页抓取 CLI 工具。支持 6 个搜索提供商和 4 个网页抓取提供商，提供时间过滤、域名过滤、比对模式等功能。

## 安装

要求 Python >= 3.10。

```bash
# 安装
pip install .

# 开发模式（可编辑安装）
pip install -e .

# 含测试依赖
pip install -e ".[dev]"
```

安装完成后验证：

```bash
melodyi-web --version
```

## 快速开始

**网页抓取开箱即用**，无需任何配置：

```bash
melodyi-web fetch https://example.com
```

**搜索需要配置 API Key**，见下方配置章节。

## 配置

### 第一步：生成配置文件

```bash
melodyi-web config init
```

这会在 `~/.melodyi-skills/melodyi-web/` 下创建：

```
~/.melodyi-skills/melodyi-web/
├── config.yaml   # 主配置文件
└── .env          # API Key（需手动创建）
```

### 第二步：配置 API Key

创建 `~/.melodyi-skills/melodyi-web/.env` 文件，填入你的 API Key：

```env
# 根据需要填写，不需要全部填写
TAVILY_API_KEY=tvly-xxxxx
BRAVE_API_KEY=xxxxx
EXA_API_KEY=xxxxx
MINIMAX_API_KEY=xxxxx
FIRECRAWL_API_KEY=xxxxx
```

项目目录下也支持放置 `.env` 文件，两处都会自动加载。

### 第三步：编辑配置文件

编辑 `~/.melodyi-skills/melodyi-web/config.yaml`，取消注释需要使用的搜索提供商：

```yaml
search_providers:
  - name: tavily
    api_key: ${TAVILY_API_KEY}
    timeout_ms: 10000
    max_results: 20

  - name: brave
    api_key: ${BRAVE_API_KEY}
    timeout_ms: 10000
    max_results: 20
```

`api_key` 字段支持 `${ENV_VAR}` 语法引用环境变量，也可以直接填写（不推荐）。

### 第四步：验证配置

```bash
melodyi-web config show
```

## 搜索

```bash
melodyi-web search "搜索关键词" [选项]
```

| 选项 | 缩写 | 说明 | 默认值 |
|------|:---:|------|:---:|
| `--max-results` | `-n` | 最大结果数 | 10 |
| `--time-range` | `-t` | 时间过滤：`day` / `week` / `month` / `year` | 无 |
| `--include-domains` | `-i` | 仅搜索指定域名（可多次使用） | 无 |
| `--exclude-domains` | `-e` | 排除指定域名（可多次使用） | 无 |
| `--provider` | `-p` | 指定提供商 | 全部已配置的 |
| `--comparison` | `-c` | 比对模式 | 关闭 |
| `--output` | `-o` | 输出格式：`text` / `json` | text |
| `--config` | `-f` | 自定义配置文件路径 | 自动查找 |

### 示例

```bash
# 基本搜索
melodyi-web search "Python 异步编程"

# 搜索本周最新 AI 新闻，多要结果
melodyi-web search "AI 进展" -t week -n 20

# 限定域名搜索
melodyi-web search "React 教程" -i juejin.cn -i dev.to

# 指定提供商
melodyi-web search "开源项目" -p tavily

# JSON 输出
melodyi-web search "API 设计" -o json
```

## 抓取

```bash
melodyi-web fetch <URL> [选项]
```

| 选项 | 缩写 | 说明 | 默认值 |
|------|:---:|------|:---:|
| `--provider` | `-p` | 指定提供商 | 全部已配置的 |
| `--comparison` | `-c` | 比对模式 | 关闭 |
| `--output` | `-o` | 输出格式：`text` / `json` | text |
| `--config` | `-f` | 自定义配置文件路径 | 自动查找 |

### 示例

```bash
# 基本抓取（默认用 jina + markdown-new，无需配置）
melodyi-web fetch https://docs.python.org/3/tutorial/

# 指定提供商
melodyi-web fetch https://spa-app.com -p jina-reader

# JSON 输出
melodyi-web fetch https://example.com -o json
```

## 比对模式

`-c` 或 `--comparison` 让所有已配置的提供商都执行同一任务，第一个提供商的结果立即返回，其余在后台执行。所有结果写入 SQLite 数据库，用于分析不同提供商的质量差异。

```bash
melodyi-web search "测试查询" -c
melodyi-web fetch https://example.com -c
```

数据库默认存储在 `~/.melodyi-skills/melodyi-web/data/compare.db`。

## 搜索提供商

| 提供商 | 需要 API Key | 时间过滤 | 域名过滤 | 说明 |
|--------|:---:|:---:|:---:|------|
| `tavily` | ✅ | ✅ | ✅ | 高质量搜索 API，支持 `depth: advanced` 深度搜索 |
| `brave` | ✅ | ✅ | ❌ | Brave Search，独立索引 |
| `exa` | ✅ | ✅ | ✅ | AI 语义搜索，支持 `type: neural` |
| `minimax-cn` | ✅ | ❌ | ❌ | MiniMax 中国区，时间/域名过滤通过关键词注入和后处理模拟 |
| `searxng` | ❌ | ✅ | ❌ | 自托管搜索引擎，需配置 `host` |
| `firecrawl` | ✅ | ❌ | ❌ | 搜索 + 抓取，需配置 `host` 或 API Key |

## 抓取提供商

| 提供商 | 需要 API Key | JS 渲染 | 说明 |
|--------|:---:|:---:|------|
| `jina-reader` | ❌（可选） | ✅ | 功能最丰富，支持 `engine: browser` JS 渲染 |
| `markdown-new` | ❌ | ❌ | 最简洁，纯 Markdown 转换 |
| `tavily-extract` | ✅ | ✅ | 深度提取，支持 `extract_depth: advanced` |
| `exa-contents` | ✅ | ❌ | 内容提取 |

## 配置文件查找顺序

配置按以下优先级查找，找到即停：

1. CLI `--config` 参数指定的路径
2. `~/.melodyi-skills/melodyi-web/config.yaml`
3. 内置默认值（fetch 默认可用，search 需配置）

## 常见错误

| 错误信息 | 原因 | 解决方法 |
|----------|------|----------|
| `未配置任何搜索供应商` | 配置文件中没有启用搜索提供商 | 编辑 `~/.melodyi-skills/melodyi-web/config.yaml`，取消注释提供商 |
| `API key is invalid or missing` | API Key 未设置或无效 | 检查 `.env` 文件或配置中的 `api_key` |
| `Request was rate-limited` | 请求频率超限 | 稍后重试，或换用其他提供商 |
| `All providers failed` | 所有提供商都失败 | 检查网络和 API Key 配置 |
| `Request timed out` | 请求超时 | 增加 `timeout_ms` 或换提供商 |

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行特定测试
pytest tests/domain/ -v
pytest -k "test_name"
```
