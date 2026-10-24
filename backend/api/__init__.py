from backend.api import (
    approval_routes,
    dashboard_routes,
    demo_routes,
    governance_routes,
    inbox_routes,
    invoice_routes,
    mock_routes,
)

ROUTERS = (
    invoice_routes.router,
    approval_routes.router,
    governance_routes.router,
    dashboard_routes.router,
    mock_routes.router,
    demo_routes.router,
    inbox_routes.router,
)

__all__ = ["ROUTERS"]
