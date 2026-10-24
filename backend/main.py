"""FastAPI entrypoint. Run with: uvicorn backend.main:app --reload"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.config import get_settings
from backend.database.database import engine, init_db
from backend.database.seed_data import get_reference_data
from backend.orchestration.state_machine import InvalidTransition
from backend.services.errors import ServiceError
from backend.utils.logging_config import setup_logging
from backend.utils.timestamps import now_utc, to_iso

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

    from backend.api import ROUTERS

    for router in ROUTERS:
        app.include_router(router)

    @app.exception_handler(ServiceError)
    def _service_error(_request: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=_error_body(exc.code, exc.message, exc)
        )

    @app.exception_handler(InvalidTransition)
    def _invalid_transition(_request: Request, exc: InvalidTransition) -> JSONResponse:
        return JSONResponse(
            status_code=409, content=_error_body("INVALID_TRANSITION", str(exc), None)
        )

    return app


def _error_body(code: str, message: str, exc: ServiceError | None) -> dict:
    return {
        "error": code,
        "message": message,
        "invoice_id": getattr(exc, "invoice_id", None),
        "correlation_id": getattr(exc, "correlation_id", None),
        "timestamp": to_iso(now_utc()),
    }


app = create_app()
