"""Configuration management for DocTagger."""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    OPENAI = "openai"  # OpenAI-compatible APIs (LM Studio, vLLM, etc.)


class LLMSettings(BaseSettings):
    """LLM settings supporting multiple providers."""

    # Provider selection
    provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        alias="provider",
        description="LLM provider: 'ollama' or 'openai' (for OpenAI-compatible APIs like LM Studio)",
    )

    # Common settings
    model: str = Field(
        default="qwen/qwen3-vl-4b",
        alias="model",
        description="Model to use for tagging"
    )
    timeout: int = Field(default=60, alias="timeout", description="Request timeout in seconds")
    temperature: float = Field(default=0.1, alias="temperature", description="Temperature for generation")
    max_tokens: int = Field(default=500, alias="max_tokens", description="Maximum tokens in response")

    # Ollama-specific
    ollama_url: str = Field(
        default="http://localhost:11434",
        alias="ollama_url",
        description="Ollama API URL"
    )

    # OpenAI-compatible settings (LM Studio, vLLM, etc.)
    openai_base_url: str = Field(
        default="http://localhost:1234/v1",
        alias="openai_base_url",
        description="OpenAI-compatible API base URL (LM Studio default: http://localhost:1234/v1)",
    )
    openai_api_key: str = Field(
        default="lm-studio",
        alias="openai_api_key",
        description="API key (use 'lm-studio' for LM Studio, or your actual key for OpenAI)",
    )

    # Vision model settings
    vision_enabled: bool = Field(
        default=False,
        description="Enable vision mode - send PDF pages as images to vision LLM instead of text",
    )
    vision_max_pages: int = Field(
        default=3,
        description="Maximum number of pages to send as images (for vision models)",
    )
    vision_dpi: int = Field(
        default=150,
        description="DPI for rendering PDF pages to images (higher = better quality but slower)",
    )

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Keep OllamaSettings as an alias for backward compatibility
class OllamaSettings(BaseSettings):
    """Ollama LLM settings (deprecated, use LLMSettings instead)."""

    url: str = Field(default="http://localhost:11434", description="Ollama API URL")
    model: str = Field(default="llama2", description="Model to use for tagging")
    timeout: int = Field(default=60, description="Request timeout in seconds")
    temperature: float = Field(default=0.1, description="Temperature for generation")

    model_config = SettingsConfigDict(env_prefix="OLLAMA_")


class OCRSettings(BaseSettings):
    """OCR processing settings."""

    enabled: bool = Field(default=True, description="Enable OCR processing")
    language: str = Field(default="eng", description="OCR language")
    skip_if_exists: bool = Field(
        default=True, description="Skip OCR if text already exists"
    )
    deskew: bool = Field(default=True, description="Deskew pages")
    force_ocr: bool = Field(default=False, description="Force OCR even if text exists")

    model_config = SettingsConfigDict(env_prefix="OCR_")


class EmbeddingSettings(BaseSettings):
    """Embedding generation settings for RAG and semantic search."""

    enabled: bool = Field(default=True, description="Enable embedding generation")
    model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence-transformers model for embeddings"
    )
    max_chars: int = Field(
        default=8000,
        description="Maximum characters to use for embedding"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include title/entities/tags in embedding context"
    )

    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class TagsSettings(BaseSettings):
    """Tagging configuration."""

    max_tags: int = Field(default=10, description="Maximum number of tags")
    custom_categories: List[str] = Field(
        default_factory=lambda: [
            "Invoice",
            "Receipt",
            "Contract",
            "Letter",
            "Report",
            "Form",
        ],
        description="Custom document categories",
    )
    min_confidence: float = Field(
        default=0.5, description="Minimum confidence for tags"
    )

    model_config = SettingsConfigDict(env_prefix="TAGS_")


class MacOSTagsSettings(BaseSettings):
    """macOS Finder tags settings."""

    enabled: bool = Field(default=False, description="Enable macOS Finder tags")
    color_mapping: bool = Field(
        default=True, description="Use color mapping for tag categories"
    )

    model_config = SettingsConfigDict(env_prefix="MACOS_TAGS_")


class Config(BaseSettings):
    """Main configuration for DocTagger."""

    # Folder paths
    inbox_folder: Path = Field(
        default=Path("./inbox"), description="Folder to watch for new PDFs"
    )
    archive_folder: Path = Field(
        default=Path("./archive"), description="Folder to store processed PDFs"
    )
    temp_folder: Path = Field(
        default=Path("/tmp/doctagger"), description="Temporary processing folder"
    )

    # Sub-configurations
    llm: LLMSettings = Field(default_factory=LLMSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)  # Deprecated
    ocr: OCRSettings = Field(default_factory=OCRSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    tags: TagsSettings = Field(default_factory=TagsSettings)
    macos_tags: MacOSTagsSettings = Field(default_factory=MacOSTagsSettings)

    # Processing settings
    archive_structure: str = Field(
        default="{year}/{month}/{document_type}",
        description="Archive folder structure template",
    )
    sidecar_enabled: bool = Field(
        default=True, description="Write sidecar JSON files"
    )
    safe_filename_pattern: str = Field(
        default=r"[^a-zA-Z0-9\-_\.]",
        description="Pattern for unsafe filename characters",
    )

    # Server settings
    server_host: str = Field(default="0.0.0.0", description="API server host")
    server_port: int = Field(default=8000, description="API server port")
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="CORS allowed origins",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[Path] = Field(None, description="Log file path")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    def __init__(self, **kwargs: Any):
        """Initialize config and create necessary directories."""
        super().__init__(**kwargs)
        self.inbox_folder.mkdir(parents=True, exist_ok=True)
        self.archive_folder.mkdir(parents=True, exist_ok=True)
        self.temp_folder.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> "Config":
        """Load configuration from file or environment."""
        if config_file and config_file.exists():
            # Support for YAML config files could be added here
            pass
        return cls()


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def set_config(config: Config) -> None:
    """Set global config instance."""
    global _config
    _config = config
