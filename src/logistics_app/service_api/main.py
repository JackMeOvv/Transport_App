"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Internal Logistics Service API",
        version="0.1.0",
    )
    return application


app = create_application()
