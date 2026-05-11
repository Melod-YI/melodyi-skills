# Web-Fetch 供应商调研报告

**Created:** 2026-05-11  
**Purpose:** 为 melodyi-web fetch 功能设计提供供应商选型依据

---

## 1. 调研范围

本报告调研**云端 SaaS 服务**，不包含需要自托管的方案。

调研供应商列表：
- Jina Reader
- Firecrawl Scrape
- Browserless
- ScrapingBee
- ZenRows

---

## 2. 供应商对比表

| 供应商 | API 端点 | JS 渲染 | 输出格式 | 免费额度 | 最低付费 | 认证方式 | 推荐指数 |
|--------|----------|---------|----------|----------|----------|----------|----------|
| Jina Reader | `r.jina.ai/{url}` | ✅ | Markdown, JSON, HTML, Text | 有（无 Key 限制） | API Key 提升速率 | Bearer Token | ⭐⭐⭐⭐⭐ |
| Firecrawl | `/v1/scrape` | ✅ | Markdown, JSON, HTML, Screenshot | 1000 次/月 | $99/月 (100K) | API Key | ⭐⭐⭐⭐⭐ |
| Browserless | Browser API | ✅ | HTML, Screenshot, PDF | 有 | 按使用量付费 | Token | ⭐⭐⭐⭐ |
| ScrapingBee | `/v1/` | ✅ | HTML, JSON | 有 | 按使用量付费 | API Key | ⭐⭐⭐ |
| ZenRows | Universal Scraper API | ✅ | HTML, JSON | 有 | 按使用量付费 | API Key | ⭐⭐⭐⭐ |

---

## 3. 供应商详细分析

### 3.1 Jina Reader

**官网:** https://jina.ai/reader/

**API 设计:**

```
# 基础用法：URL 前缀方式（无需 API Key）
https://r.jina.ai/https://example.com/article

# 带认证的 API 方式
curl https://r.jina.ai/https://example.com \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**端点:**
- `r.jina.ai/{url}` — 读取 URL，返回 Markdown
- `s.jina.ai/{query}` — 搜索网络，返回结果
- `g.jina.ai/{statement}` — 事实核查

**请求参数:**
- `url`: 目标 URL（必填）
- 请求头控制输出格式：
  - `x-respond-with: markdown` — Markdown 输出
  - `x-respond-with: json` — JSON 输出（包含 URL、标题、内容）
  - `x-respond-with: html` — HTML 输出

**响应格式:**

```json
// JSON 模式
{
  "url": "https://example.com",
  "title": "文章标题",
  "content": "Markdown 内容...",
  "description": "页面描述",
  "publishedTime": "2025-01-01"
}
```

**能力特性:**
- ✅ **JS 渲染**: 使用无头浏览器（Puppeteer）渲染动态内容
- ✅ **内容清洗**: 使用 Mozilla Readability 提取主要内容
- ✅ **多媒体支持**: 图片 OCR、PDF 解析、视频元数据提取
- ✅ **Alt 生成**: 为缺少 alt 标签的图片自动生成描述
- ✅ **流式处理**: 支持逐步加载长文档

**速率限制:**
- 无 API Key: 有速率限制（约 20 次/分钟）
- 有 API Key: 更高速率限制

**定价模型:**
- **免费**: 基础使用免费，无需注册
- **付费**: API Key 可提升速率，具体定价需官网查看

**集成难度:**
- ⭐ **极低**: 只需添加 URL 前缀，无需配置
- 支持 HTTP 直接调用
- 无 SDK，但可直接用 `requests` 库

**优点:**
- 零门槛使用，无需 API Key
- 支持多种输出格式
- 内容清洗效果好
- 开源项目，可自托管

**缺点:**
- 无 API Key 时速率限制较严
- 不支持自定义选择器
- 复杂页面可能解析不完整

---

### 3.2 Firecrawl Scrape

**官网:** https://firecrawl.dev/

**API 设计:**

```python
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key="fc-YOUR_API_KEY")

# 单页抓取
result = app.scrape_url("https://example.com", 
    params={"formats": ["markdown", "html", "json"]})

# 网站爬取（多页）
crawl_result = app.crawl_url("https://docs.example.com",
    params={"limit": 100, "scrapeOptions": {"formats": ["markdown"]}})
```

**端点:**
| 端点 | 用途 | 说明 |
|------|------|------|
| `/v1/scrape` | 单页抓取 | 抓取指定 URL 内容 |
| `/v1/crawl` | 网站爬取 | 递归爬取整个网站 |
| `/v1/search` | 网络搜索 | 搜索并返回清理后的内容 |
| `/v1/extract` | 结构化提取 | 根据提示提取特定数据 |
| `/v1/map` | URL 映射 | 生成网站 URL 清单 |

**请求参数:**
- `url`: 目标 URL（必填）
- `formats`: 输出格式数组（`["markdown", "html", "json", "screenshot"]`）
- `onlyMainContent`: 仅提取主要内容（默认 true）
- `waitFor`: 等待特定元素或时间
- `actions`: 执行操作（点击、滚动、填表等）

**响应格式:**

```json
{
  "success": true,
  "data": {
    "markdown": "# 标题\n\n内容...",
    "html": "<html>...</html>",
    "metadata": {
      "title": "页面标题",
      "description": "描述",
      "language": "en",
      "sourceURL": "https://example.com"
    }
  }
}
```

**能力特性:**
- ✅ **JS 渲染**: 完整无头浏览器支持
- ✅ **反爬绕过**: 自动处理 CAPTCHA、IP 封禁
- ✅ **代理轮换**: 自动管理代理池
- ✅ **智能等待**: 自动等待页面完全加载
- ✅ **PDF/DOCX 解析**: 支持文件解析
- ✅ **LLM 集成**: 无缝对接 LangChain、LlamaIndex

**定价模型:**
| 计划 | 价格 | 包含 | 超额费用 |
|------|------|------|----------|
| Free | $0 | 1,000 次/月 | N/A |
| Pro | $99/月 | 100,000 次 | $0.001/次 |
| Enterprise | 自定义 | 无限 | 批量折扣 |

**集成难度:**
- ⭐⭐ **低**: 提供 Python/Node.js SDK
- SDK 安装: `pip install firecrawl-py`
- 认证: API Key (`fc-xxx` 格式)

**优点:**
- 功能全面（scrape + crawl + extract + search）
- 反爬能力强
- 官方 SDK 支持好
- 开源，可自托管
- 与现有 search 功能共用供应商

**缺点:**
- Pro 版价格较高（$99/月）
- 单次抓取成本较高

---

### 3.3 Browserless

**官网:** https://www.browserless.io/

**API 设计:**

Browserless 是**浏览器自动化服务**，而非直接的内容抓取 API。适合需要精细控制的场景。

```javascript
// 使用 Puppeteer 连接 Browserless
const browser = await puppeteer.connect({
  browserWSEndpoint: 'wss://chrome.browserless.io?token=YOUR_TOKEN'
});

const page = await browser.newPage();
await page.goto('https://example.com');
const content = await page.content();
```

**端点:**
| 端点 | 用途 |
|------|------|
| `/content` | 获取页面 HTML |
| `/screenshot` | 截图 |
| `/pdf` | 生成 PDF |
| `/scrape` | 抓取数据 |
| `/browserql` | 新一代自动化语言 |

**能力特性:**
- ✅ **JS 渲染**: 完整浏览器支持
- ✅ **反爬绕过**: 自研 BrowserQL 绕过检测
- ✅ **会话持久化**: 支持会话保持
- ✅ **实时调试**: 可观看脚本运行
- ✅ **合规认证**: SOC 2 Type II, GDPR, HIPAA

**定价模型:**
- Free tier: 6 小时/月
- 付费: 按使用量计费

**集成难度:**
- ⭐⭐⭐ **中等**: 需熟悉 Puppeteer/Playwright
- 需要 WebSocket 连接
- 认证: Token

**优点:**
- 控制精细
- 反爬能力强
- 支持复杂交互场景

**缺点:**
- 需要编写浏览器自动化代码
- 不直接提供内容清洗
- 学习成本较高

---

### 3.4 ScrapingBee

**官网:** https://www.scrapingbee.com/

**API 设计:**

```python
from scrapingbee import ScrapingBeeClient

client = ScrapingBeeClient(api_key='YOUR_API_KEY')

response = client.get(
    'https://example.com',
    params={
        'render_js': 'true',
        'premium_proxy': 'true'
    }
)
```

**端点:**
- `GET /v1/` — HTML 抓取
- `POST /v1/` — 带参数抓取

**请求参数:**
- `url`: 目标 URL
- `render_js`: 是否渲染 JS（true/false）
- `premium_proxy`: 是否使用高级代理
- `country`: 代理国家
- `forward_headers`: 自定义请求头

**能力特性:**
- ✅ **JS 渲染**: 无头浏览器支持
- ✅ **代理轮换**: 自动管理代理
- ✅ **99.9% 成功率**
- ✅ **CSS 选择器**: 支持精准提取

**定价模型:**
- Free tier: 1,000 次
- 付费: 按使用量计费，比 ScraperAPI 便宜约 50%

**集成难度:**
- ⭐⭐ **低**: 提供 Python/Node.js SDK

**优点:**
- 成功率高
- 价格相对便宜
- 功能齐全

**缺点:**
- 不直接提供 Markdown 输出
- 内容清洗需自行处理

---

### 3.5 ZenRows

**官网:** https://www.zenrows.com/

**API 设计:**

```python
import zenrows

client = zenrows.Client(api_key="YOUR_API_KEY")

response = client.get("https://example.com", 
    params={"js_render": "true", "antibot": "true"})
```

**能力特性:**
- ✅ **JS 渲染**: 支持
- ✅ **反爬绕过**: 99.93% 成功率
- ✅ **住宅代理**: 高质量住宅 IP
- ✅ **Scraping Browser**: 一行代码集成 Playwright

**定价模型:**
- Free tier: 有免费试用
- 付费: 按使用量计费

**集成难度:**
- ⭐⭐ **低**: 提供 Python SDK

**优点:**
- 成功率极高
- 反爬能力强
- 与 Playwright 无缝集成

**缺点:**
- 价格相对较高
- 不直接提供 Markdown 输出

---

## 4. 推荐优先集成的供应商

基于调研结果，推荐优先集成以下 3 个供应商：

### 推荐排名

| 排名 | 供应商 | 推荐理由 |
|------|--------|----------|
| **#1** | Jina Reader | 零门槛、免费使用、直接输出 Markdown、集成最简单 |
| **#2** | Firecrawl | 功能全面、与现有 search 共用供应商、官方 SDK 完善 |
| **#3** | ZenRows | 成功率最高、反爬能力强、适合复杂场景 |

### 推荐实现顺序

1. **第一阶段**: 实现 Jina Reader Provider
   - 原因: 最简单、无 API Key 要求、可直接验证 fetch 框架设计
   
2. **第二阶段**: 实现 Firecrawl Scrape Provider
   - 原因: 已有 search 实现，可复用 API Key 和配置
   
3. **第三阶段**: 实现 ZenRows Provider（可选）
   - 原因: 作为备选，应对复杂反爬场景

---

## 5. 实现建议

### 5.1 Fetch 基类设计建议

```python
class BaseFetchProvider:
    """Fetch 提供商基类"""
    
    @property
    def name(self) -> str:
        """提供商标识符"""
    
    def fetch(self, request: FetchRequest) -> FetchResult:
        """执行抓取"""
    
    def supports_js_render(self) -> bool:
        """是否支持 JS 渲染"""
    
    def get_output_formats(self) -> List[str]:
        """支持的输出格式"""
```

### 5.2 FetchRequest 模型建议

```python
class FetchRequest(BaseModel):
    """抓取请求"""
    url: str  # 目标 URL
    output_format: str = "markdown"  # 输出格式
    js_render: bool = True  # 是否渲染 JS
    wait_for: Optional[str] = None  # 等待选择器
```

### 5.3 FetchResult 模型建议

```python
class FetchResult(BaseModel):
    """抓取结果"""
    url: str
    title: Optional[str]
    content: str  # 主要内容（Markdown）
    raw_html: Optional[str]
    metadata: dict
    response_time_ms: int
    error: Optional[FetchError]
```

---

## 6. 附录

### 6.1 各供应商 SDK 安装命令

```bash
# Firecrawl
pip install firecrawl-py

# ScrapingBee
pip install scrapingbee

# ZenRows
pip install zenrows

# Jina Reader（无 SDK，直接 HTTP）
# 无需安装，使用 requests 即可
```

### 6.2 Firecrawl 双端点对比

| 端点 | 用途 | 归属领域 | melodyi-web 对应 |
|------|------|----------|------------------|
| `/v1/search` | 网络搜索 | Search | `melodyi-web search` |
| `/v1/scrape` | 网页抓取 | Fetch | `melodyi-web fetch` |

---

*Created: 2026-05-11*