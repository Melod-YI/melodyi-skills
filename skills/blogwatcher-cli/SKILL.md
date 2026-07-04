---
name: blogwatcher-cli
description: 使用 blogwatcher CLI 管理博客文章。当用户需要查看文章列表、博客列表、分类列表、扫描博客更新、标记文章已读/未读、添加备注等操作时使用此 skill。触发词包括：文章、博客、分类、扫描、已读、未读、备注、note、blogwatcher。
---

# BlogWatcher CLI 使用指南

BlogWatcher 是一个博客文章管理 CLI 工具，用于管理订阅的博客及其文章。

## 命令概览

```
blogwatcher <command> [subcommand] [flags]
```

主要命令：
- `article` - 文章管理（列表、标记已读/未读）
- `blog` - 博客管理（列表、扫描）
- `category` - 分类管理（列表）
- `note` - 备注管理（添加、删除）

## 输出格式约定

**所有获取类命令默认使用 JSON 格式输出**，便于解析和处理数据：

```bash
blogwatcher article list --format json
blogwatcher blog list --format json
blogwatcher category list --format json
```

仅在用户明确要求"表格形式"或"可读格式"时使用 `--format table`。

---

## 文章管理 (article)

### 列出文章

```bash
blogwatcher article list --format json [--unread|--read] [--not-noted] [--blog <name>] [--category <name>] [--after <date>] [--limit <n>] [--offset <n>]
```

筛选参数：
- `--unread` - 仅未读文章
- `--read` - 仅已读文章
- `--not-noted` - 仅无备注文章
- `--blog <name>` - 按博客名称筛选
- `--category <name>` - 按分类筛选（**注意：需先确认分类名称存在**）
- `--after YYYY-MM-DD` - 指定日期之后的文章
- `--limit <n>` - 限制返回数量（**默认 20，最大 100，0 表示无限制**）
- `--offset <n>` - 跳过前 n 条结果（用于翻页）

常用组合示例：
```bash
# 查看所有未读文章
blogwatcher article list --format json --unread

# 查看未读且无备注的文章
blogwatcher article list --format json --unread --not-noted

# 查看某分类下的未读文章（最多10条）
blogwatcher article list --format json --category tech --unread --limit 10

# 翻页查看（跳过前20条，查看第21-40条）
blogwatcher article list --format json --limit 20 --offset 20

# 查看所有文章（无限制）
blogwatcher article list --format json --limit 0
```

### 标记文章状态

```bash
# 标记单篇文章已读
blogwatcher article mark-read <id>

# 标记所有未读文章已读
blogwatcher article mark-read --all

# 标记文章未读
blogwatcher article mark-unread <id>
```

---

## 博客管理 (blog)

### 列出博客

```bash
blogwatcher blog list --format json [--category <name>]
```

按分类筛选时需先确认分类名称存在。

### 扫描博客获取新文章

```bash
# 扫描所有博客
blogwatcher blog scan

# 扫描指定博客
blogwatcher blog scan <name>

# 扫描某分类下的所有博客
blogwatcher blog scan --category <name>
```

扫描结果会显示新获取的文章数量。注意：`<name>` 和 `--category` 不能同时使用。

---

## 分类管理 (category)

### 列出分类

```bash
blogwatcher category list --format json
```

返回所有分类及其包含的博客数量。

---

## 备注管理 (note)

### 添加备注

备注需要从文件读取，操作流程如下：

1. **创建临时备注文件**
   ```bash
   echo "备注内容" > /tmp/note_<article_id>.md
   ```

2. **执行 note 命令**
   ```bash
   blogwatcher note --article-id <id> --file /tmp/note_<id>.md
   ```

3. **删除临时文件**（防止堆积）
   ```bash
   rm /tmp/note_<article_id>.md
   ```

**完整示例**：
```bash
# 为文章 ID 123 添加备注
echo "这篇文章讨论了 Go 并发模式的最佳实践" > /tmp/note_123.md
blogwatcher note --article-id 123 --file /tmp/note_123.md
rm /tmp/note_123.md
```

### 删除备注

```bash
blogwatcher note delete --article-id <id>
```

---

## 分类名称确认流程

当需要使用用户提到的分类名称进行筛选时（如 `--category tech`），**分类名称必须与数据库中的真实名称完全匹配**。

用户可能使用模糊或近似的名称，例如：
- 用户说"技术分类"，实际名称可能是 "tech" 或 "技术"
- 用户说"科技"，实际名称可能是 "technology"

### 确认步骤

1. **先查询所有分类**
   ```bash
   blogwatcher category list --format json
   ```

2. **对比用户提供的名称与真实名称**
   - 如果找到完全匹配：直接使用
   - 如果有多个近似匹配：向用户确认具体是哪一个
   - 如果没有匹配：告知用户该分类不存在，并列出可用分类

**示例**：
```
用户：查看技术分类下的未读文章
Agent：
  1. 执行 category list 获取分类列表
  2. 发现分类有：["tech", "生活", "设计", "technology"]
  3. "技术"与 "tech" 和 "technology" 都可能对应
  4. 向用户确认："您说的是 'tech' 还是 'technology' 分类？"
```

---

## 特殊场景

### 批量操作

用户想批量标记已读或扫描多个博客时：

```bash
# 标记所有未读文章已读（慎用）
blogwatcher article mark-read --all

# 扫描所有博客
blogwatcher blog scan
```

### 组合筛选

用户想找"某个博客下的未读无备注文章"：

```bash
blogwatcher article list --format json --blog "Tech Blog" --unread --not-noted
```

### 日期范围筛选

用户想看"最近一周的文章"：

```bash
# 计算一周前的日期，然后查询
blogwatcher article list --format json --after 2026-05-11
```

### 限制结果数量与翻页

`article list` **默认返回 20 条结果，最大 100 条**。

```bash
# 查看前5条
blogwatcher article list --format json --limit 5

# 翻页查看（第二页，即第21-40条）
blogwatcher article list --format json --limit 20 --offset 20

# 查看全部文章（无限制）
blogwatcher article list --format json --limit 0
```

---

## 注意事项

- 文章 ID 可从 `article list` 的 JSON 输出中获取
- 博客名称需要精确匹配（可从 `blog list` 获取）
- `article list` 默认返回 20 条，最大 100 条，需翻页或 `--limit 0` 查看全部
- 扫描操作可能耗时较长，取决于博客数量和网络状况
- 备注文件使用后务必删除，避免临时文件堆积