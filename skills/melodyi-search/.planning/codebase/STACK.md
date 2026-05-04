# STACK.md

**Last mapped:** 2026-05-04

## 技术栈概览

melodyi-search 是一个 Python 多提供商搜索工具，采用 DDD (领域驱动设计) 架构，支持多种搜索 API 的统一调用和智能切换。

## 语言与运行时

| 项目 | 版本 | 说明 |
|------|------|------|
| Python | >=3.10 | 主要语言，使用现代 Python 特性 |
| Hatch | - | 构建后端 (hatchling) |

## 核心依赖

### 数据验证与配置

| 库 | 版本 | 用途 |
|---|------|------|
| `pydantic` | >=2.0 | 数据模型验证、请求/响应结构定义 |
| `pyyaml` | >=6.0 | YAML 配置文件解析 |
| `python-dotenv` | >=1.0 | 环境变量加载 (.env 文件) |

### HTTP 与网络

| 库 | 版本 | 用途 |
|---|------|------|
| `httpx` | >=0.25 | 异步 HTTP 客户端，支持同步和异步请求 |

### CLI

| 库 | 版本 | 用途 |
|---|------|------|
| `click` | >=8.0 | 命令行界面框架，提供 `@click.group` 和 `@click.command` 装饰器 |

## 开发依赖

| 库 | 版本 | 用途 |
|---|------|------|
| `pytest` | >=7.0 | 测试框架 |
| `pytest-asyncio` | >=0.21 | 异步测试支持 |

## 包管理

使用 `pyproject.toml` 进行依赖管理：

```
C:\workspace\melodyi-skills\skills\melodyi-search\pyproject.toml
```

### 项目结构

```toml
[project]
name = "melodyi-search"
version = "0.1.0"
requires-python = ">=3.10"

[project.scripts]
melodyi-search = "melodyi_search.application.cli:main"
```

## 配置文件

| 文件 | 格式 | 用途 |
|------|------|------|
| `melodyi_search/infrastructure/config/default_config.yaml` | YAML | 默认提供商配置 |
| `.env` (外部) | dotenv | API 密钥存储 |

## 代码统计

- 总代码行数: ~6098 行 Python
- 源文件: 35 个 `.py` 文件
- 测试文件: 32 个 `test_*.py` 文件

---

*Mapped by sequential codebase analysis on 2026-05-04*