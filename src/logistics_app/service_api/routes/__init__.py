"""HTTP route modules grouped by business capability."""

from logistics_app.service_api.routes.audit import router as audit_router
from logistics_app.service_api.routes.deliveries import router as deliveries_router
from logistics_app.service_api.routes.documents import router as documents_router
from logistics_app.service_api.routes.pallets import router as pallets_router
from logistics_app.service_api.routes.printing import router as printing_router

__all__ = [
    "audit_router",
    "deliveries_router",
    "documents_router",
    "pallets_router",
    "printing_router",
]
