"""DocTagger - Automatically tag and organize PDF documents using local LLM."""

__version__ = "0.1.0"
__author__ = "DocTagger Contributors"
__license__ = "MIT"

from .models import DocumentMetadata, ProcessingResult, TaggingResult
from .config import Config

__all__ = [
    "DocumentMetadata",
    "ProcessingResult",
    "TaggingResult",
    "Config",
]
