"""DATABASE_URL handling for the shared Supabase Postgres database (no network needed)."""

import pytest

from backend.database.database import make_engine, normalize_database_url, rls_statements


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            "postgres://u:p@db.x.supabase.co:5432/postgres",
            "postgresql+psycopg://u:p@db.x.supabase.co:5432/postgres",
        ),
        ("postgresql://u:p@host:6543/postgres", "postgresql+psycopg://u:p@host:6543/postgres"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:///./trustpay.db", "sqlite:///./trustpay.db"),
    ],
)
def test_supabase_url_is_accepted_as_pasted(raw, expected):
    assert normalize_database_url(raw) == expected


def test_postgres_engine_uses_psycopg_and_pooler_safe_settings():
    engine = make_engine(
        "postgresql://u:p@db.example.supabase.co:5432/postgres"
    )  # no connection made
    assert engine.dialect.name == "postgresql" and engine.dialect.driver == "psycopg"
    assert engine.pool._pre_ping is True


def test_sqlite_still_works_for_local_dev_and_tests():
    assert make_engine("sqlite://").dialect.name == "sqlite"


def test_rls_enabled_on_every_table():
    stmts = rls_statements()
    for table in (
        "invoices",
        "agent_decisions",
        "tool_calls",
        "audit_events",
        "approvals",
        "inbox_messages",
    ):
        assert f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY' in stmts
