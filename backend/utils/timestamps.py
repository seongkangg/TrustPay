"""UTC timestamp helpers so every timestamp in the system looks the same (ISO-8601, Z suffix)."""

from datetime import UTC, datetime


def now_utc() -> datetime:
    return datetime.now(UTC)


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; everything stored is UTC. Attach the zone, never shift."""
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=UTC)


def to_iso(dt: datetime) -> str:
    """Render as `2026-10-24T10:00:00Z` (seconds precision, Z not +00:00)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> datetime:
    """Accept both `...Z` and `...+00:00`; always return an aware UTC datetime."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
