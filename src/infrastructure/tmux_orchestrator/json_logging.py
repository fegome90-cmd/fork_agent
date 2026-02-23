import json
import logging
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    def __init__(self, include_extra: bool = True) -> None:
        super().__init__()
        self._include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        if self._include_extra:
            for key, value in record.__dict__.items():
                if key not in (
                    "msg",
                    "args",
                    "exc_info",
                    "exc_text",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "message",
                    "name",
                    "stack_info",
                ):
                    if not key.startswith("_"):
                        log_obj[key] = value

        return json.dumps(log_obj)


def setup_json_logging(logger_name: str | None = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    return logger


def get_json_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
