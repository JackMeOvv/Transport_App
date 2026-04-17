"""Shared database enums used by ORM models and migrations."""

from __future__ import annotations

from enum import StrEnum


class DeliverySlipStatus(StrEnum):
    """High-level delivery lifecycle state."""

    CREATED = "CREATED"
    STORED = "STORED"
    DOCUMENTS_IN_PREPARATION = "DOCUMENTS_IN_PREPARATION"
    RELEASED_BY_TRANSPORT = "RELEASED_BY_TRANSPORT"
    READY_TO_LOAD = "READY_TO_LOAD"
    LOADING_IN_PROGRESS = "LOADING_IN_PROGRESS"
    SHIPPED = "SHIPPED"
    SIGNED_CMR_PENDING = "SIGNED_CMR_PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SplitTransportStatus(StrEnum):
    """Lifecycle state for the rare split transport exception flow."""

    PLANNED = "PLANNED"
    READY_TO_LOAD = "READY_TO_LOAD"
    LOADED = "LOADED"
    DISPATCHED = "DISPATCHED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DocumentType(StrEnum):
    PACKING_SLIP = "PACKING_SLIP"
    CMR = "CMR"
    SIGNED_CMR = "SIGNED_CMR"
    CERTIFICATE = "CERTIFICATE"
    STICKER = "STICKER"
    TRANSPORT_DOCUMENT = "TRANSPORT_DOCUMENT"
    OTHER = "OTHER"


class DocumentStatus(StrEnum):
    EXPECTED = "EXPECTED"
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class PalletStatus(StrEnum):
    REGISTERED = "REGISTERED"
    IN_WAREHOUSE = "IN_WAREHOUSE"
    STAGED = "STAGED"
    LOADED = "LOADED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    LOST = "LOST"
    DAMAGED = "DAMAGED"


class WarehouseLocationType(StrEnum):
    RECEIVING = "RECEIVING"
    STORAGE = "STORAGE"
    STAGING = "STAGING"
    LOADING_DOCK = "LOADING_DOCK"
    QUARANTINE = "QUARANTINE"
    OUTBOUND_BUFFER = "OUTBOUND_BUFFER"


class PalletMovementType(StrEnum):
    RECEIVED = "RECEIVED"
    PUT_AWAY = "PUT_AWAY"
    RELOCATED = "RELOCATED"
    STAGED_FOR_LOADING = "STAGED_FOR_LOADING"
    LOADED = "LOADED"
    UNLOADED = "UNLOADED"
    CORRECTED = "CORRECTED"


class PrintTargetType(StrEnum):
    DELIVERY = "DELIVERY"
    DOCUMENT = "DOCUMENT"
    SPLIT_TRANSPORT = "SPLIT_TRANSPORT"


class PrintJobStatus(StrEnum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    PRINTED = "PRINTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AuditEntityType(StrEnum):
    DELIVERY_SLIP = "DELIVERY_SLIP"
    PALLET = "PALLET"
    WAREHOUSE_LOCATION = "WAREHOUSE_LOCATION"
    DOCUMENT = "DOCUMENT"
    PRINT_JOB = "PRINT_JOB"
    SPLIT_TRANSPORT = "SPLIT_TRANSPORT"
    SYSTEM = "SYSTEM"


class AuditActionType(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    STATUS_CHANGE = "STATUS_CHANGE"
    PRINT = "PRINT"
    UPLOAD = "UPLOAD"
    MOVE = "MOVE"
    LOAD = "LOAD"
    UNLOAD = "UNLOAD"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"


class ApplicationLogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
