"""Shared fixtures: a fresh in-memory SQLite session per test and the reference data."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.database import Base
from backend.database.seed_data import get_reference_data, load_demo_invoices


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    from backend.database import tables  # noqa: F401 — register tables

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    s = Session()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()


@pytest.fixture(scope="session")
def ref():
    return get_reference_data()


@pytest.fixture(scope="session")
def demo_invoices():
    return load_demo_invoices()
