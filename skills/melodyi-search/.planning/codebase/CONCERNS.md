# CONCERNS.md

**Last mapped:** 2026-05-04

## 技术债务

### 1. 异步架构不完整

**问题**: 项目声明支持异步但未充分利用

| 文件 | 当前状态 | 建议 |
|------|----------|------|
| `http_client.py` | 只有同步实现 | 添加 async 版本 |
| `ExecutionStrategy` | 使用 `threading.Thread` | 考虑 `asyncio` 替代 |
| 提供商 `search()` | 仅同步方法 | 可添加 `async search()` |

**影响**: 
- 比对模式使用 daemon thread，可能在高并发下不稳定
- 无法与异步 Agent 框架良好集成

**建议阶段**: Phase 1 架构重构

---

### 2. 配置验证不足

**问题**: YAML 配置加载缺乏完整性验证

| 文件 | 当前状态 |
|------|----------|
| `config_loader.py` | 仅 Pydantic 模型验证 |
| 环境变量 | 可能缺失但无运行时检测 |

**潜在问题**:
- API Key 缺失时运行到实际调用才发现
- 提供商配置错误时报错信息不清晰

**建议**: 
- 启动时验证所有配置完整性
- 添加 `config validate` CLI 命令

---

### 3. 错误处理边界不清

**问题**: 部分提供商实现捕获了过于宽泛的异常

```python
# 当前: 捕获所有 Exception
except Exception as e:
    error_msg = str(e)
```

**建议**: 
- 区分网络错误、API 错误、配置错误
- 使用 `ErrorType` 枚举分类

---

## 已知问题

### 1. Windows 符号链接兼容

**文件**: `melodyi_search/infrastructure/logging/search_logger.py`

```python
# Windows 可能无法创建符号链接
try:
    search_log.symlink_to(self._current_log_file.name)
except (OSError, NotImplementedError):
    pass  # 静默忽略
```

**影响**: Windows 上 `search.log` 可能不存在

**状态**: 已处理（静默忽略）

---

### 2. daemon thread 日志丢失

**文件**: `melodyi_search/domain/services/execution_strategy.py`

比对模式使用 `daemon=True` 线程：

```python
thread = threading.Thread(..., daemon=True)
```

**潜在风险**: 主进程退出时后台线程可能未完成日志写入

**影响**: 低风险，比对日志主要用于分析

---

## 安全考量

### 1. API Key 存储

**当前**: 通过环境变量 (`${MINIMAX_API_KEY}`)

**安全状态**: ✓ 安全（不硬编码在配置文件）

**建议**: 
- 添加 `.env.example` 模板
- 文档说明密钥管理最佳实践

---

### 2. 日志敏感信息

**当前**: 不记录 API Key

**验证**: `SearchLogger` 不记录认证信息

---

## 性能考量

### 1. HTTP 连接复用

**文件**: `melodyi_search/infrastructure/http/http_client.py`

**当前**: 每次请求创建新连接

**建议**: 考虑连接池复用（httpx 支持）

---

### 2. 提供商串行执行

**当前**: 正常模式串行执行所有提供商

**优化方向**: 
- 并行发起多个提供商请求
- 返回最快成功的结果

---

## 代码质量

### 覆盖率

**状态**: 有完整测试结构，覆盖率未统计

**建议**: 运行 `pytest --cov` 并设置目标

---

### 文档

| 类型 | 状态 |
|------|------|
| 代码注释 | 中文注释，充分 |
| API 文档 | `skill.md` 已提供 |
| 需求文档 | `需求.md` 已提供 |
| 内联文档 | Pydantic `Field.description` 充分 |

---

## 外部依赖风险

| 提供商 | 稳定性 | 备注 |
|--------|--------|------|
| MiniMax CN | 新提供商 | API 可能变化 |
| SearXNG | 本地部署 | 用户自行维护 |
| Firecrawl | 本地部署 | 用户自行维护 |

---

*Mapped by sequential codebase analysis on 2026-05-04*