"""Structured JSON logging with sensitive-data masking on every line.

Usage: `setup_logging()` once at startup, then `logging.getLogger(__name__)` anywhere.
Pass `extra={"invoice_id": ..., "correlation_id": ...}` to tag a line.
Lines also go to a dev log file; `log_dev_error` puts a traceback there and returns a ref
the user-facing message can quote instead of the raw exception.
"""

import json
import logging
import sys
import uuid
from pathlib import Path

from backend.services.masking_service import mask_text
from backend.utils.timestamps import now_utc, to_iso

CONTEXT_KEYS = ("invoice_id", "correlation_id", "agent", "tool", "event_type")


class MaskingFilter(logging.Filter):
    """Masks the rendered message so raw bank/tax values can never reach a log sink."""

    def filter(self, record: logging.LogRecord) -> bool:
        rendered = record.getMessage()
        masked, _ = mask_text(rendered)
        record.msg = masked
        record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": to_iso(now_utc()),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in CONTEXT_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            # Tracebacks repeat exception messages, which can hold raw values.
            payload["exception"] = mask_text(self.formatException(record.exc_info))[0]
        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO", dev_log_file: str | None = None) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if dev_log_file:
        Path(dev_log_file).parent.mkdir(parents=True, exist_ok=True)
        # shortcut: no rotation, fine for a demo; switch to RotatingFileHandler if it grows.
        handlers.append(logging.FileHandler(dev_log_file, encoding="utf-8"))
    for handler in handlers:
        handler.setFormatter(JsonFormatter())
        handler.addFilter(MaskingFilter())
        root.addHandler(handler)
    root.setLevel(level.upper())


def log_dev_error(logger: logging.Logger, what: str, **extra) -> str:
    """Log the current exception with its traceback; return the ref to show the user."""
    ref = f"ERR-{uuid.uuid4().hex[:8]}"
    logger.exception("%s ref=%s", what, ref, extra=extra)
    return ref
