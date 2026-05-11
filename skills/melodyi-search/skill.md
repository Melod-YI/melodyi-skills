---
name: melodyi-web
description: 搜索网络获取知识截止日期之外的信息
---

## 描述

允许搜索网络以获取当前、实时的信息。提供最新的资讯、数据、文档等内容，弥补知识截止日期的限制。

**关键特性：**
- 多供应商自动切换与负载均衡
- 自动重试与错误恢复
- 支持域名过滤、时间范围筛选
- 中文搜索优化

## 使用

当需要获取以下类型信息时使用此工具：
- 当前事件和最新新闻
- 最近发布的文档或更新
- 实时数据（股价、天气、汇率等）
- 知识截止日期之后的新信息

**搜索是自动执行的**，无需用户确认。

## 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 搜索查询关键词，建议使用 3-5 个关键词以获得最佳结果 |
| max_results | int | 否 | 期望返回的最大结果数，默认 10，最小值 1 |
| time_range | object | 否 | 时间过滤配置 |
| include_domains | array | 否 | 仅搜索指定域名列表 |
| exclude_domains | array | 否 | 排除指定域名列表 |
| language | string | 否 | ISO 语言代码（如 zh, en） |

### time_range 配置

支持两种方式：

**简单范围类型：**
```json
{"range_type": "day"}  // 可选值：day, week, month, year
```

**精确日期范围：**
```json
{
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-12-31T23:59:59"
}
```

## 输出格式

返回搜索结果列表，每个结果包含：

| 字段 | 说明 |
|------|------|
| title | 结果标题 |
| url | 结果链接 |
| description | 内容摘要/片段 |
| published_date | 发布日期（如可用） |
| source_domain | 来源域名 |

## 重要说明

### 必须包含来源信息

回答用户问题后，**必须**在回复末尾包含 "Sources:" 部分，列出所有引用的来源链接。

**格式示例：**

```markdown
[您的回答内容]

Sources:
- [来源标题1](https://example.com/1)
- [来源标题2](https://example.com/2)
```

这是**强制性要求**——绝不跳过在回复中包含来源信息。

### 时效性注意

- 当前日期信息请自行确认
- 搜索近期信息时，在查询中包含当前年份
- 例如：用户询问"最新 React 文档"，应搜索 "React documentation 2026"

## 错误处理

当搜索遇到错误时，返回结果将包含 `error` 字段，其中包含：

| 字段 | 说明 |
|------|------|
| error_type | 错误类型分类 |
| original_message | 原始错误信息 |
| guidance | 错误处理指导 |

### 常见错误类型

| 错误类型 | 说明 | 建议操作 |
|----------|------|----------|
| API_KEY_INVALID | API 密钥无效或缺失 | 检查配置中的 API 密钥设置 |
| RATE_LIMITED | 请求被限流 | 等待后重试，系统会自动切换供应商 |
| QUOTA_EXCEEDED | API 配额已耗尽 | 系统会自动切换供应商 |
| NETWORK_ERROR | 网络连接错误 | 检查网络连接后重试 |
| TIMEOUT | 请求超时 | 系统会自动重试或切换供应商 |
| INVALID_REQUEST | 请求参数无效 | 检查请求参数是否符合要求 |

根据 `guidance` 字段中的提示进行相应的修复或规避操作。

## 示例输出

### 成功响应

```json
{
  "provider": "provider-name",
  "response_time_ms": 234,
  "results": [
    {
      "title": "示例文章标题",
      "url": "https://example.com/article",
      "description": "这是一段关于文章内容的摘要描述...",
      "published_date": "2024-01-15T10:30:00",
      "source_domain": "example.com"
    }
  ],
  "error": null
}
```

### 错误响应

```json
{
  "provider": "provider-name",
  "response_time_ms": 5000,
  "results": [],
  "error": {
    "error_type": "RATE_LIMITED",
    "original_message": "Too many requests",
    "guidance": "请求被此提供商限流。操作：请等待后重试，或系统将自动切换到另一个提供商。"
  }
}
```