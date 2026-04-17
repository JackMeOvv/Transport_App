"""Request and response schemas for the service API."""

from logistics_app.service_api.schemas.audit import AuditLogResponse, AuditLogWriteRequest
from logistics_app.service_api.schemas.common import ApiErrorResponse, OrmResponseModel
from logistics_app.service_api.schemas.deliveries import (
    DeliverySlipDetailResponse,
    DeliverySlipSummaryResponse,
    DeliverySlipUpdateRequest,
)
from logistics_app.service_api.schemas.documents import DocumentResponse
from logistics_app.service_api.schemas.pallets import (
    PalletLoadedRequest,
    PalletMovementRequest,
    PalletMovementResponse,
    PalletResponse,
    PalletUpdateRequest,
)
from logistics_app.service_api.schemas.printing import (
    PrintInstructionResponse,
    PrintInstructionUpsertRequest,
    PrintJobFailedRequest,
    PrintJobPrintedRequest,
    PrintJobReprintRequest,
    PrintJobRequestSchema,
    PrintJobResponse,
    PrintRequirementSummaryResponse,
)

__all__ = [
    "ApiErrorResponse",
    "AuditLogResponse",
    "AuditLogWriteRequest",
    "DeliverySlipDetailResponse",
    "DeliverySlipSummaryResponse",
    "DeliverySlipUpdateRequest",
    "DocumentResponse",
    "OrmResponseModel",
    "PalletLoadedRequest",
    "PalletMovementRequest",
    "PalletMovementResponse",
    "PalletResponse",
    "PalletUpdateRequest",
    "PrintInstructionResponse",
    "PrintInstructionUpsertRequest",
    "PrintJobFailedRequest",
    "PrintJobPrintedRequest",
    "PrintJobReprintRequest",
    "PrintJobRequestSchema",
    "PrintJobResponse",
    "PrintRequirementSummaryResponse",
]
