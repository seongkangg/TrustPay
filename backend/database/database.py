"""SQLAlchemy engine and session.

`DATABASE_URL` picks the database:
- SQLite (`sqlite:///./trustpay.db`) — local dev and the test suite.
- Supabase Postgres (the shared team database) — paste the connection string from the Supabase
  dashboard as-is; `postgres://` / `postgresql://` are switched to the psycopg 3 driver here.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import get_settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    """Accept the URL exactly as Supabase shows it; use the psycopg 3 driver for Postgres."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def make_engine(database_url: str | None = None):
    url = normalize_database_url(database_url or get_settings().database_url)
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False}, future=True)
    return create_engine(
        url,
        pool_pre_ping=True,  # a remote DB drops idle connections; reconnect instead of erroring
        pool_recycle=300,
        # Supabase's transaction pooler (port 6543) does not support prepared statements.
        connect_args={"prepare_threshold": None},
        future=True,
    )


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def rls_statements() -> list[str]:
    """Supabase serves every table in `public` over its REST API to anyone with the project's
    (public) anon key, unless row-level security is on. RLS with no policies closes that route;
    the backend connects directly as the table owner and is unaffected."""
    from backend.database import tables  # noqa: F401

    return [
        f'ALTER TABLE "{t.name}" ENABLE ROW LEVEL SECURITY' for t in Base.metadata.sorted_tables
    ]


def init_db(bind=None) -> None:
    """Create all tables (idempotent). Importing `tables` registers them on `Base`."""
    from backend.database import tables  # noqa: F401

    target = bind or engine
    Base.metadata.create_all(bind=target)
    if target.dialect.name == "postgresql":
        with target.begin() as conn:
            for stmt in rls_statements():
                conn.execute(text(stmt))


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
