# backend/utils/

Small shared helpers with no business logic.

| File | What it does |
|------|--------------|
| `logging_config.py` | Structured JSON logging setup. Attaches correlation ID / invoice ID to every log line and routes log messages through `masking_service` so raw sensitive values never hit the log. |
| `timestamps.py` | `now_utc()` and ISO-8601 formatting/parsing helpers so every timestamp in the system looks the same. |
| `validation.py` | Generic validators: required-field checks, amount/currency range checks, ID-prefix format checks, date parsing. Used by the intake agent and the API layer to flag malformed input. |
