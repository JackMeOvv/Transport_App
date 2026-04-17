"""Document storage service for file persistence outside the database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import mimetypes
from pathlib import Path
import re
from uuid import uuid4

from sqlalchemy.orm import Session

from logistics_app.data.models.delivery_slip import DeliverySlip
from logistics_app.data.models.document import Document
from logistics_app.data.models.enums import DocumentStatus, DocumentType
from logistics_app.data.models.pallet import Pallet
from logistics_app.data.models.split_transport import SplitTransport
from logistics_app.data.repositories.document_repository import DocumentRepository
from logistics_app.infrastructure.config.settings import ApplicationSettings, get_settings

SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True, slots=True)
class StoreDocumentRequest:
    """Input for storing a document file and metadata."""

    delivery_slip_id: int
    document_type: DocumentType
    source_file_path: Path
    uploaded_by: str | None = None
    pallet_id: int | None = None
    split_transport_id: int | None = None
    remarks: str | None = None
    document_date: date | None = None


class DocumentStorageError(Exception):
    """Base exception for document storage errors."""


class DocumentFileMissingError(DocumentStorageError):
    """Raised when a requested source file does not exist."""


class DocumentLinkValidationError(DocumentStorageError):
    """Raised when business links between delivery, pallet, and split transport do not match."""


class DocumentStorageService:
    """Stores document files on disk and keeps metadata in the database.

    Files are written outside the database. The database stores only document
    metadata, file location, checksums, and version information.
    """

    def __init__(
        self,
        session: Session,
        settings: ApplicationSettings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._repository = DocumentRepository(session)

    def store_document(self, request: StoreDocumentRequest) -> Document:
        """Store a document file and create a new metadata version record."""
        source_file_path = request.source_file_path
        if not source_file_path.exists() or not source_file_path.is_file():
            raise DocumentFileMissingError(f"Source file does not exist: {source_file_path}")

        delivery_slip = self._session.get(DeliverySlip, request.delivery_slip_id)
        if delivery_slip is None:
            raise DocumentLinkValidationError(
                f"Delivery slip {request.delivery_slip_id} was not found."
            )

        pallet = self._load_and_validate_pallet(
            pallet_id=request.pallet_id,
            delivery_slip_id=request.delivery_slip_id,
        )
        split_transport = self._load_and_validate_split_transport(
            split_transport_id=request.split_transport_id,
            delivery_slip_id=request.delivery_slip_id,
        )
        self._validate_combined_links(pallet=pallet, split_transport=split_transport)

        latest_document = self._repository.get_latest_version(
            delivery_slip_id=request.delivery_slip_id,
            document_type=request.document_type,
            pallet_id=request.pallet_id,
            split_transport_id=request.split_transport_id,
        )
        next_version_number = 1 if latest_document is None else latest_document.version_number + 1

        storage_directory = self._build_storage_directory(
            delivery_slip=delivery_slip,
            pallet=pallet,
            split_transport=split_transport,
            document_type=request.document_type,
        )
        storage_directory.mkdir(parents=True, exist_ok=True)

        original_filename = source_file_path.name
        safe_storage_filename = self._build_storage_filename(
            original_filename=original_filename,
            document_type=request.document_type,
            version_number=next_version_number,
        )
        destination_file_path = storage_directory / safe_storage_filename
        if destination_file_path.exists():
            raise DocumentStorageError(
                f"Refusing to overwrite existing file: {destination_file_path}"
            )

        checksum_sha256 = self._copy_file_with_checksum(
            source_file_path=source_file_path,
            destination_file_path=destination_file_path,
        )
        file_size_bytes = destination_file_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(destination_file_path.name)
        uploaded_at = datetime.now(UTC)

        self._repository.mark_existing_versions_not_latest(
            delivery_slip_id=request.delivery_slip_id,
            document_type=request.document_type,
            pallet_id=request.pallet_id,
            split_transport_id=request.split_transport_id,
        )

        document = Document(
            delivery_slip_id=request.delivery_slip_id,
            pallet_id=request.pallet_id,
            split_transport_id=request.split_transport_id,
            document_type=request.document_type,
            document_status=DocumentStatus.AVAILABLE,
            original_filename=original_filename,
            stored_filename=safe_storage_filename,
            storage_relative_path=self._to_relative_storage_path(destination_file_path),
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            checksum_sha256=checksum_sha256,
            uploaded_at=uploaded_at,
            uploaded_by=request.uploaded_by,
            document_date=request.document_date,
            version_number=next_version_number,
            is_latest_version=True,
            remarks=request.remarks,
        )
        self._repository.add(document)
        self._session.flush()
        return document

    def _load_and_validate_pallet(
        self,
        pallet_id: int | None,
        delivery_slip_id: int,
    ) -> Pallet | None:
        if pallet_id is None:
            return None

        pallet = self._session.get(Pallet, pallet_id)
        if pallet is None:
            raise DocumentLinkValidationError(f"Pallet {pallet_id} was not found.")
        if pallet.delivery_slip_id != delivery_slip_id:
            raise DocumentLinkValidationError(
                "The pallet does not belong to the provided delivery slip."
            )
        return pallet

    def _load_and_validate_split_transport(
        self,
        split_transport_id: int | None,
        delivery_slip_id: int,
    ) -> SplitTransport | None:
        if split_transport_id is None:
            return None

        split_transport = self._session.get(SplitTransport, split_transport_id)
        if split_transport is None:
            raise DocumentLinkValidationError(
                f"Split transport {split_transport_id} was not found."
            )
        if split_transport.delivery_slip_id != delivery_slip_id:
            raise DocumentLinkValidationError(
                "The split transport does not belong to the provided delivery slip."
            )
        return split_transport

    def _validate_combined_links(
        self,
        pallet: Pallet | None,
        split_transport: SplitTransport | None,
    ) -> None:
        if pallet is None or split_transport is None:
            return
        if pallet.split_transport_id is not None and pallet.split_transport_id != split_transport.id:
            raise DocumentLinkValidationError(
                "The pallet is linked to a different split transport than the document request."
            )

    def _build_storage_directory(
        self,
        delivery_slip: DeliverySlip,
        pallet: Pallet | None,
        split_transport: SplitTransport | None,
        document_type: DocumentType,
    ) -> Path:
        delivery_folder = self._safe_path_segment(delivery_slip.delivery_slip_number)
        path = self._settings.storage.documents_root / delivery_folder / document_type.value.lower()

        if split_transport is not None:
            path = path / f"split_{self._safe_path_segment(split_transport.split_code)}"

        if pallet is not None:
            path = path / f"pallet_{self._safe_path_segment(pallet.pallet_identifier)}"

        return path

    def _build_storage_filename(
        self,
        original_filename: str,
        document_type: DocumentType,
        version_number: int,
    ) -> str:
        extension = Path(original_filename).suffix.lower()
        safe_extension = extension if self._is_safe_extension(extension) else ""
        safe_stem = self._safe_path_segment(Path(original_filename).stem) or "document"
        unique_token = uuid4().hex
        return (
            f"{document_type.value.lower()}_v{version_number:03d}_"
            f"{safe_stem}_{unique_token}{safe_extension}"
        )

    def _copy_file_with_checksum(
        self,
        source_file_path: Path,
        destination_file_path: Path,
    ) -> str:
        digest = hashlib.sha256()
        with source_file_path.open("rb") as source_file:
            with destination_file_path.open("xb") as destination_file:
                while chunk := source_file.read(1024 * 1024):
                    destination_file.write(chunk)
                    digest.update(chunk)
        return digest.hexdigest()

    def _to_relative_storage_path(self, destination_file_path: Path) -> str:
        return str(destination_file_path.relative_to(self._settings.storage.documents_root))

    def _safe_path_segment(self, value: str) -> str:
        normalized_value = SAFE_FILENAME_PATTERN.sub("_", value.strip())
        return normalized_value.strip("._")[:120]

    def _is_safe_extension(self, extension: str) -> bool:
        return bool(extension) and len(extension) <= 10 and SAFE_FILENAME_PATTERN.sub("", extension) == extension
