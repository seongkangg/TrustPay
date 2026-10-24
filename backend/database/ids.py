"""Sequential, human-readable IDs (INV-1001, EVT-001, TOOL-001, …).

Numbered from the highest existing ID for the prefix, not from the row count: the count drops
when rows are deleted (a partial cleanup, a re-run), and "count + 1" then reissues a number that
a surviving row still holds — a primary-key collision that fails the whole invoice.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def next_id(session: Session, column, prefix: str, *, width: int = 3, start: int = 1) -> str:
    """`{prefix}-{n}`, one past the highest existing number for `prefix` (at least `start`).

    Zero-padded IDs only sort numerically within one length, so order by length first:
    EVT-1000 is after EVT-999.
    """
    last = session.scalar(
        select(column)
        .where(column.like(f"{prefix}-%"))
        .order_by(func.length(column).desc(), column.desc())
        .limit(1)
    )
    n = start
    if last:
        tail = last.rsplit("-", 1)[-1]
        if tail.isdigit():
            n = max(start, int(tail) + 1)
    return f"{prefix}-{n:0{width}d}"
