"""Pydantic models for DocTagger."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProcessingStatus(str, Enum):
    """Status of document processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DocumentType(str, Enum):
    """Common document types."""

    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    LETTER = "letter"
    REPORT = "report"
    FORM = "form"
    OTHER = "other"


class TaggingResult(BaseModel):
    """Result from LLM tagging."""

    title: str = Field(..., description="Document title")
    document_type: str = Field(..., description="Type of document")
    tags: List[str] = Field(default_factory=list, description="List of tags")
    summary: Optional[str] = Field(None, description="Brief summary")
    date: Optional[str] = Field(None, description="Document date if found")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Ensure tags are normalized."""
        return [tag.strip().lower() for tag in v if tag.strip()]


class DocumentMetadata(BaseModel):
    """PDF metadata to be written."""

    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    creator: str = "DocTagger"
    producer: str = "DocTagger"


class ProcessingResult(BaseModel):
    """Result of processing a document."""

    status: ProcessingStatus
    original_path: Path
    archive_path: Optional[Path] = None
    sidecar_path: Optional[Path] = None
    metadata: Optional[DocumentMetadata] = None
    tagging: Optional[TaggingResult] = None
    ocr_applied: bool = False
    error: Optional[str] = None
    processing_time: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    content_hash: Optional[str] = Field(None, description="SHA-256 hash of file content for deduplication")

    model_config = ConfigDict(
        json_encoders={
            Path: str,
            datetime: lambda v: v.isoformat(),
        }
    )


class ProcessingRequest(BaseModel):
    """Request to process a document."""

    file_path: str
    skip_ocr: bool = False
    skip_archive: bool = False
    custom_tags: Optional[List[str]] = None


class ProcessingStatusResponse(BaseModel):
    """Status response for document processing."""

    request_id: str
    status: ProcessingStatus
    result: Optional[ProcessingResult] = None
    message: Optional[str] = None


class DocumentListItem(BaseModel):
    """Summary item for document list."""

    path: str
    title: Optional[str] = None
    document_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    document_date: Optional[str] = None  # Date extracted from document content
    summary: Optional[str] = None
    processed_at: datetime
    size_bytes: int

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class SystemStatus(BaseModel):
    """System status information."""

    llm_available: bool
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    # Deprecated fields for backward compatibility
    ollama_available: Optional[bool] = None
    ollama_model: Optional[str] = None
    inbox_folder: Optional[str] = None
    archive_folder: Optional[str] = None
    watching: bool = False
    processed_count: int = 0
    failed_count: int = 0


class BatchFileStatus(BaseModel):
    """Status of a single file in a batch."""

    request_id: str
    filename: str
    status: ProcessingStatus
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """Response for batch file upload."""

    batch_id: str
    files: List[Dict[str, str]]
    message: str


class BatchStatusResponse(BaseModel):
    """Status response for batch processing."""

    batch_id: str
    total: int
    completed: int
    failed: int
    pending: int
    files: List[BatchFileStatus]


class CustomPrompt(BaseModel):
    """Custom LLM prompt template."""

    id: str
    name: str
    description: str
    prompt_template: str
    document_types: List[str] = Field(default_factory=list)
    is_default: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "invoice-detailed",
                "name": "Detailed Invoice Analysis",
                "description": "Extract detailed line items from invoices",
                "prompt_template": "Analyze this invoice document...",
                "document_types": ["invoice", "receipt"],
                "is_default": False,
            }
        }
    )
