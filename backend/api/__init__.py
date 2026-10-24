from backend.api import (
    approval_routes,
    dashboard_routes,
    governance_routes,
    invoice_routes,
    mock_routes,
)

ROUTERS = (
    invoice_routes.router,
    approval_routes.router,
    governance_routes.router,
    dashboard_routes.router,
    mock_routes.router,
)

__all__ = ["ROUTERS"]
