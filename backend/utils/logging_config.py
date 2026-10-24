"""Structured JSON logging with sensitive-data masking on every line.

Usage: `setup_logging()` once at startup, then `logging.getLogger(__name__)` anywhere.
Pass `extra={"invoice_id": ..., "correlation_id": ...}` to tag a line.
"""

import json
import logging
import sys

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
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(MaskingFilter())
    root.addHandler(handler)
    root.setLevel(level.upper())
