"""Main document processing pipeline."""

import logging
import time
from pathlib import Path
from typing import Optional

from .config import Config, get_config
from .extractor import TextExtractor
from .llm import LLMTagger
from .metadata import MetadataWriter
from .models import DocumentMetadata, ProcessingResult, ProcessingStatus, TaggingResult
from .normalizer import Normalizer
from .ocr import OCRProcessor
from .organizer import FileOrganizer
from .utils import calculate_file_hash

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Main pipeline for processing PDF documents."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize document processor."""
        self.config = config or get_config()
        self.ocr_processor = OCRProcessor(self.config)
        self.text_extractor = TextExtractor()
        self.llm_tagger = LLMTagger(self.config)
        self.normalizer = Normalizer(self.config)
        self.metadata_writer = MetadataWriter()
        self.file_organizer = FileOrganizer(self.config)

    def process(
        self,
        pdf_path: Path,
        skip_ocr: bool = False,
        skip_archive: bool = False,
        force_reprocess: bool = False,
    ) -> ProcessingResult:
        """
        Process a single PDF document.

        Args:
            pdf_path: Path to the PDF file
            skip_ocr: Skip OCR processing
            skip_archive: Skip archiving (keep in original location)
            force_reprocess: Force reprocessing even if already processed (ignores deduplication)

        Returns:
            ProcessingResult with processing details
        """
        start_time = time.time()
        original_path = pdf_path.resolve()

        logger.info(f"Starting processing: {pdf_path.name}")

        # Calculate content hash for deduplication
        try:
            content_hash = calculate_file_hash(original_path)
        except Exception as e:
            logger.warning(f"Failed to calculate file hash: {e}")
            content_hash = None

        result = ProcessingResult(
            status=ProcessingStatus.PROCESSING,
            original_path=original_path,
            content_hash=content_hash,
        )

        try:
            # Step 1: OCR Processing
            ocr_applied = False
            if not skip_ocr and self.config.ocr.enabled:
                try:
                    # Create temp file for OCR output
                    temp_path = self.config.temp_folder / f"ocr_{pdf_path.name}"
                    self.ocr_processor.process(pdf_path, temp_path)
                    ocr_applied = True
                    pdf_path = temp_path  # Use OCR'd version for subsequent steps
                    logger.info("OCR processing completed")
                except Exception as e:
                    logger.warning(f"OCR failed, continuing without OCR: {e}")

            result.ocr_applied = ocr_applied

            # Step 2: Text Extraction
            logger.info("Extracting text...")
            text = self.text_extractor.extract(pdf_path)

            if not text.strip():
                raise RuntimeError("No text could be extracted from the PDF")

            # Step 3: LLM Tagging
            logger.info("Tagging with LLM...")
            tagging: TaggingResult = self.llm_tagger.tag(text)
            result.tagging = tagging

            # Step 3.5: Generate Embedding (if enabled)
            if self.config.embedding.enabled:
                logger.info("Generating embedding...")
                try:
                    from .embedder import DocumentEmbedder
                    embedder = DocumentEmbedder(
                        config=self.config,
                        model_name=self.config.embedding.model,
                    )
                    
                    if self.config.embedding.include_metadata:
                        # Generate embedding with enriched context
                        embedding = embedder.embed_with_metadata(
                            text=text,
                            title=tagging.title,
                            entities=tagging.entities,
                            tags=tagging.tags,
                        )
                    else:
                        # Generate embedding from text only
                        embedding = embedder.embed_text(
                            text=text,
                            max_chars=self.config.embedding.max_chars,
                        )
                    
                    if embedding:
                        result.embedding = embedding
                        result.embedding_model = self.config.embedding.model
                        logger.info(f"Generated embedding ({len(embedding)} dimensions)")
                    else:
                        logger.warning("Embedding generation returned None")
                except ImportError as e:
                    logger.warning(f"Embedding skipped - sentence-transformers not installed: {e}")
                except Exception as e:
                    logger.warning(f"Embedding generation failed: {e}")

            # Step 4: Normalize Output
            logger.info("Normalizing output...")
            normalized_tags = self.normalizer.normalize_tags(tagging.tags)
            safe_title = self.normalizer.sanitize_title(tagging.title)

            # Create metadata
            metadata = DocumentMetadata(
                title=safe_title,
                subject=tagging.summary,
                keywords=normalized_tags,
            )
            result.metadata = metadata

            # Step 5: Apply Metadata to PDF
            logger.info("Writing metadata to PDF...")
            temp_with_metadata = self.config.temp_folder / f"meta_{pdf_path.name}"
            self.metadata_writer.write_metadata(pdf_path, metadata, temp_with_metadata)

            # Step 6: Determine Archive Path
            if not skip_archive:
                archive_path = self.normalizer.create_archive_path(
                    original_filename=original_path.name,
                    document_type=tagging.document_type,
                    date=tagging.date,
                )
                result.archive_path = archive_path

                # Step 7: Move to Archive
                logger.info(f"Moving to archive: {archive_path}")
                self.file_organizer.move_to_archive(temp_with_metadata, archive_path)

                # Step 8: Apply macOS Tags (optional)
                if self.config.macos_tags.enabled:
                    self.file_organizer.apply_macos_tags(archive_path, normalized_tags)

                # Step 9: Write Sidecar JSON
                sidecar_path = self.file_organizer.write_sidecar(archive_path, result)
                result.sidecar_path = sidecar_path

            else:
                # If not archiving, write back to original location
                self.metadata_writer.write_metadata(
                    temp_with_metadata, metadata, original_path
                )

            # Step 10: Cleanup
            if ocr_applied:
                temp_path = self.config.temp_folder / f"ocr_{original_path.name}"
                self.file_organizer.cleanup_temp_files(temp_path)
            self.file_organizer.cleanup_temp_files(temp_with_metadata)

            # Success
            result.status = ProcessingStatus.COMPLETED
            result.processing_time = time.time() - start_time

            logger.info(
                f"Processing completed successfully in {result.processing_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            result.status = ProcessingStatus.FAILED
            result.error = str(e)
            result.processing_time = time.time() - start_time
            return result

    def check_system(self) -> dict:
        """
        Check system dependencies and configuration.

        Returns:
            Dictionary with system status
        """
        status = {
            "llm_available": False,
            "llm_provider": str(self.config.llm.provider.value),
            "llm_model": self.config.llm.model,
            # Deprecated fields for backward compatibility
            "ollama_available": False,
            "ollama_model": None,
            "inbox_folder": str(self.config.inbox_folder),
            "archive_folder": str(self.config.archive_folder),
            "ocr_enabled": self.config.ocr.enabled,
            "macos_tags_enabled": self.config.macos_tags.enabled,
        }

        # Check LLM availability
        try:
            if self.llm_tagger.check_availability():
                status["llm_available"] = True
                status["ollama_available"] = True  # backward compat
                status["ollama_model"] = self.config.llm.model
        except Exception as e:
            logger.warning(f"LLM check failed: {e}")

        return status
