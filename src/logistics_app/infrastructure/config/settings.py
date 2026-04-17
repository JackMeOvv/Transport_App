"""Application configuration models and helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["development", "test", "staging", "production"]


class DatabaseSettings(BaseModel):
    """Database connection settings for the service and desktop client."""

    host: str = "localhost"
    port: int = 5432
    database_name: str = "logistics_app"
    username: str = "logistics_user"
    password: str = ""
    echo_sql: bool = False
    pool_size: int = 10
    max_overflow: int = 20

    @property
    def sqlalchemy_url(self) -> str:
        """Build the SQLAlchemy connection URL from individual fields."""
        return (
            f"postgresql+psycopg://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database_name}"
        )


class StorageSettings(BaseModel):
    """Filesystem paths used for document storage and operational exports."""

    documents_root: Path = Path("C:/ProgramData/InternalLogistics/documents")
    temporary_files_root: Path = Path("C:/ProgramData/InternalLogistics/temp")
    exports_root: Path = Path("C:/ProgramData/InternalLogistics/exports")


class PrinterDefaults(BaseModel):
    """Default printer routes used by warehouse and transport operations."""

    warehouse_main_printer: str = "WAREHOUSE_MAIN"
    loading_dock_printer: str = "LOADING_DOCK"
    office_printer: str = "OFFICE"
    label_printer: str = "LABEL"


class DocumentTypePrinterMapping(BaseModel):
    """Default printer route per document type.

    Values refer to fields on `PrinterDefaults`, not direct printer names.
    This lets IT change physical printer names without changing document
    routing policy in the application logic.
    """

    packing_slip: str = "warehouse_main_printer"
    cmr: str = "warehouse_main_printer"
    signed_cmr: str = "office_printer"
    certificate: str = "office_printer"
    sticker: str = "label_printer"
    transport_document: str = "warehouse_main_printer"
    other: str = "office_printer"


class PrinterSettings(BaseModel):
    """Printer behavior and default printer assignments."""

    spooler_backend: str = "windows"
    job_timeout_seconds: int = 60
    allow_direct_print: bool = True
    defaults: PrinterDefaults = Field(default_factory=PrinterDefaults)
    document_type_mapping: DocumentTypePrinterMapping = Field(
        default_factory=DocumentTypePrinterMapping
    )


class ApiSettings(BaseModel):
    """Settings for the internal FastAPI service layer."""

    host: str = "0.0.0.0"
    port: int = 8000
    base_url: str = "http://localhost:8000"
    request_timeout_seconds: int = 30


class DesktopSettings(BaseModel):
    """Settings specific to the Windows desktop client."""

    company_display_name: str = "Internal Logistics"
    default_language: str = "en"
    theme_name: str = "enterprise_light"


class LoggingSettings(BaseModel):
    """Logging destinations and thresholds."""

    level: str = "INFO"
    persist_application_logs: bool = True
    application_logger_name: str = "logistics_app"


class ApplicationSettings(BaseSettings):
    """Central application settings loaded from environment variables or `.env` files.

    The nested structure keeps related settings together while still allowing
    IT to override individual values through standard environment variables.
    Example:

    - `LOGISTICS_APP_DATABASE__HOST=db-server.internal`
    - `LOGISTICS_APP_STORAGE__DOCUMENTS_ROOT=D:/Logistics/Documents`
    - `LOGISTICS_APP_PRINTERS__DEFAULTS__WAREHOUSE_MAIN_PRINTER=WarehousePrinter01`
    """

    environment: EnvironmentName = "development"
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    printers: PrinterSettings = Field(default_factory=PrinterSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    desktop: DesktopSettings = Field(default_factory=DesktopSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = SettingsConfigDict(
        env_prefix="LOGISTICS_APP_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @property
    def document_storage_root(self) -> Path:
        """Backward-compatible access to the primary document storage path."""
        return self.storage.documents_root


@lru_cache(maxsize=1)
def get_settings() -> ApplicationSettings:
    """Load and cache application settings for the current process."""
    return ApplicationSettings()
