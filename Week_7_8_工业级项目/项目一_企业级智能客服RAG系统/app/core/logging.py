"""结构化日志支持。

- `JsonFormatter`：标准库实现的 JSON 行日志格式化器，零第三方依赖。
- `configure_logging`：统一配置根日志器，可通过环境变量 `LOG_FORMAT=json` 切换。

用法：日志调用方通过 `extra={"request_id": ...}` 传递请求上下文，
JSON 模式下会并入输出字段，便于日志采集（ELK/Loki）索引。
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """将日志记录输出为单行 JSON。

    固定字段：ts(ISO8601) / level / logger / message / module / line。
    额外字段：记录中的 `extra` 字典（如 request_id）会被合并输出；
    异常时附带 `exc_info` 堆栈文本。
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # 合并 extra 字段（request_id 等请求上下文）
        for key, value in record.__dict__.items():
            if key not in self._reserved and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)

    _reserved = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "taskName", "message", "asctime",
    })


def configure_logging(level: str = "INFO", log_format: str = "text") -> None:
    """配置根日志器。

    Args:
        level: 日志级别（INFO/DEBUG/WARNING/ERROR）。
        log_format: "json" 输出结构化 JSON 行；其他值输出纯文本（开发默认）。
    """

    handler = logging.StreamHandler(sys.stdout)
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
