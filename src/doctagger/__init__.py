"""DocTagger - Automatically tag and organize PDF documents using local LLM.

Supports multiple LLM providers:
- Ollama (default)
- OpenAI-compatible APIs (LM Studio, vLLM, etc.)

Features:
- PDF processing with OCR
- Intelligent tagging via LLM
- Document embeddings for RAG/semantic search
- Batch processing
- Plugin system for extensibility
- Cloud storage support (S3, GCS, Azure)
"""

__version__ = "0.1.0"
__author__ = "DocTagger Contributors"
__license__ = "MIT"

from .models import (
    DocumentMetadata,
    ProcessingResult,
    TaggingResult,
    SystemStatus,
    BatchStatusResponse,
    CustomPrompt,
)
from .config import Config, LLMSettings, LLMProvider, EmbeddingSettings

__all__ = [
    # Models
    "DocumentMetadata",
    "ProcessingResult",
    "TaggingResult",
    "SystemStatus",
    "BatchStatusResponse",
    "CustomPrompt",
    # Config
    "Config",
    "LLMSettings",
    "LLMProvider",
    "EmbeddingSettings",
]
