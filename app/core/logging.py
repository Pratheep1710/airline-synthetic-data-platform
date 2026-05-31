from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from enum import Enum
from typing import Any

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")
_BASE_LOG_RECORD_KEYS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())


class JsonFormatter(logging.Formatter):
    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, dict):
            return {str(k): JsonFormatter._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [JsonFormatter._to_jsonable(v) for v in value]
        return str(value)

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx_var.get(),
        }
        extra = {
            key: self._to_jsonable(value)
            for key, value in record.__dict__.items()
            if key not in _BASE_LOG_RECORD_KEYS and key not in {"message", "asctime"}
        }
        if extra:
            payload["context"] = extra
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
