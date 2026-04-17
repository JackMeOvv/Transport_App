"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from logistics_app.infrastructure.config.settings import get_settings
from logistics_app.infrastructure.logging.setup import configure_logging
from logistics_app.service_api.routes import (
    audit_router,
    deliveries_router,
    documents_router,
    pallets_router,
    printing_router,
)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.logging.level)

    application = FastAPI(
        title="Internal Logistics Service API",
        version="0.1.0",
        description=(
            "Internal service layer for the Windows desktop client. "
            "The API exposes stable business operations and keeps the desktop "
            "client away from direct database access."
        ),
    )
    application.include_router(deliveries_router)
    application.include_router(pallets_router)
    application.include_router(documents_router)
    application.include_router(printing_router)
    application.include_router(audit_router)

    @application.get("/health")
    def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "environment": settings.environment,
                "service": "internal-logistics-service-api",
            }
        )

    return application


app = create_application()
