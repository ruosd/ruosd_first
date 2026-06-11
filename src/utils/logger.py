"""
日志模块 — 双格式输出

控制台: 人类可读的纯文本格式
文件:   机器可解析的 JSON 格式（每行一条 JSON）

用法不变:
    from src.utils import get_logger
    logger = get_logger("module_name")
    logger.info("消息内容")
"""

import logging
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


class JSONFormatter(logging.Formatter):
    """JSON 格式化器 — 每条日志一个 JSON 对象"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "module": record.name,
            "event": record.getMessage(),
        }

        # 异常信息
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        # 调用位置（出错时定位代码行）
        if record.levelno >= logging.WARNING:
            log_entry["location"] = f"{record.filename}:{record.lineno}"

        return json.dumps(log_entry, ensure_ascii=False)


class Logger:
    """日志记录器 — 单例模式，每个模块名一个实例"""

    _instances: dict = {}

    def __new__(cls, name: str = "app"):
        if name not in cls._instances:
            cls._instances[name] = super().__new__(cls)
            cls._instances[name]._initialized = False
        return cls._instances[name]

    def __init__(self, name: str = "app"):
        if self._initialized:
            return
        self.name = name
        self.logger = self._setup_logger()
        self._initialized = True

    def _setup_logger(self) -> logging.Logger:
        """配置双格式日志处理器"""
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)

        if logger.handlers:
            return logger

        log_dir = Path("./logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # ── 文件处理器：JSON 格式 ──
        log_file = log_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())

        # ── 控制台处理器：人类可读文本 ──
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
            datefmt="%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False):
        self.logger.critical(message, exc_info=exc_info)


def get_logger(name: str = "app") -> Logger:
    """获取日志记录器实例"""
    return Logger(name)
