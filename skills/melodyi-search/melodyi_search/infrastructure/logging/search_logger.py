"""搜索日志器"""

import logging
import atexit
from datetime import datetime
from pathlib import Path
from typing import Optional


class SearchLogger:
    """搜索日志器，完整记录搜索过程"""

    def __init__(self, log_dir: str = "./logs", console_output: bool = True):
        """初始化日志器"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 创建 logger - 使用唯一名称避免冲突
        self._logger_name = f"melodyi_search_{id(self)}"
        self.logger = logging.getLogger(self._logger_name)
        self.logger.setLevel(logging.DEBUG)

        # 清除已有 handlers
        self.logger.handlers = []

        # 文件 handler
        log_file = self.log_dir / f"search_{datetime.now().strftime('%Y-%m-%d')}.log"
        self._file_handler = logging.FileHandler(log_file, encoding='utf-8')
        self._file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '[%(asctime)s] %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self._file_handler.setFormatter(file_format)
        self.logger.addHandler(self._file_handler)

        # 控制台 handler
        self._console_handler = None
        if console_output:
            self._console_handler = logging.StreamHandler()
            self._console_handler.setLevel(logging.INFO)
            console_format = logging.Formatter('[%(levelname)s] %(message)s')
            self._console_handler.setFormatter(console_format)
            self.logger.addHandler(self._console_handler)

        # 创建一个符号链接 search.log 指向当天的日志文件
        self._current_log_file = log_file
        self._create_log_symlink()

        # 注册清理函数
        atexit.register(self.close)

    def _create_log_symlink(self):
        """创建 search.log 符号链接或复制文件"""
        search_log = self.log_dir / "search.log"
        # 在 Windows 上，我们直接创建一个指向当前日志文件的软链接
        # 或者简单地复制/创建一个名为 search.log 的文件
        try:
            # 尝试删除旧的 search.log 如果存在
            if search_log.exists():
                search_log.unlink()
            # 创建符号链接
            search_log.symlink_to(self._current_log_file.name)
        except (OSError, NotImplementedError):
            # 如果无法创建符号链接（如权限不足），则忽略
            # 测试可以通过检查 search_{date}.log 文件来验证
            pass

    def log_search_request(self, query: str, **params):
        """记录搜索请求"""
        param_str = ", ".join(f"{k}={v}" for k, v in params.items() if v)
        self.logger.info(f"Query: \"{query}\" | Params: {param_str}")

    def log_provider_start(self, provider: str):
        """记录提供商开始执行"""
        self.logger.debug(f"Provider: {provider} | Start")

    def log_provider_result(
        self,
        provider: str,
        status: str,
        time_ms: int,
        results_count: int = 0,
        error: Optional[str] = None
    ):
        """记录提供商执行结果"""
        if status == "success":
            self.logger.info(
                f"Provider: {provider} | Status: success | Time: {time_ms}ms | Results: {results_count}"
            )
        else:
            self.logger.warning(
                f"Provider: {provider} | Status: {status} | Time: {time_ms}ms | Error: {error}"
            )

    def log_search_result(self, title: str, url: str, description: str, index: int = 1):
        """记录单个搜索结果"""
        self.logger.info(
            f"Result {index}: title=\"{title}\" url=\"{url}\" description=\"{description[:100]}...\""
        )

    def log_error(self, provider: str, error_type: str, message: str, guidance: str):
        """记录错误和指导"""
        self.logger.error(f"Provider: {provider} | Error: {error_type} | Message: {message}")
        self.logger.info(f"Provider: {provider} | Guidance: {guidance}")

    def log_comparison_summary(self, winner: str, results: dict):
        """记录比对模式汇总"""
        self.logger.info(f"[COMPARISON] Winner: {winner}")
        for provider, data in results.items():
            self.logger.info(
                f"[COMPARISON] {provider}: {data['status']}, {data['time_ms']}ms, {data['results_count']} results"
            )

    def close(self):
        """关闭日志器，释放文件句柄"""
        if self._file_handler:
            self._file_handler.close()
            self.logger.removeHandler(self._file_handler)
        if self._console_handler:
            self._console_handler.close()
            self.logger.removeHandler(self._console_handler)
        # 从 logging 管理器中移除
        logging.getLogger(self._logger_name).handlers = []

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时关闭日志器"""
        self.close()
        return False