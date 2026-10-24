"""FastAPI entrypoint. Run with: uvicorn backend.main:app --reload"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.config import get_settings
from backend.database.database import engine, init_db
from backend.database.seed_data import get_reference_data
from backend.utils.logging_config import setup_logging

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    init_db()
    ref = get_reference_data()
    log.info(
        "startup complete: %d vendors, %d purchase orders, %d approval limits, llm_mode=%s",
        len(ref.vendors),
        len(ref.purchase_orders),
        len(ref.approval_limits),
        settings.llm_mode,
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TrustPay — Governed Multi-Agent Invoice Approval",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:  # noqa: BLE001 — health must never raise
            db_status = "error"
        return {
            "status": "ok" if db_status == "ok" else "degraded",
            "llm_mode": settings.llm_mode,
            "db": db_status,
        }

    # API routers are mounted here in Sprint 4 (backend/api/).
    return app


app = create_app()
