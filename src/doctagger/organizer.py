"""File organization and archiving."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import Config, get_config
from .models import ProcessingResult

logger = logging.getLogger(__name__)


class FileOrganizer:
    """Handles file organization and archiving."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize file organizer."""
        self.config = config or get_config()

    def move_to_archive(
        self, source_path: Path, archive_path: Path
    ) -> Path:
        """
        Move a file to the archive location.

        Args:
            source_path: Source file path
            archive_path: Destination path in archive

        Returns:
            Path to archived file

        Raises:
            RuntimeError: If move fails
        """
        try:
            # Create parent directories
            archive_path.parent.mkdir(parents=True, exist_ok=True)

            # Move the file
            logger.info(f"Moving {source_path.name} to {archive_path}")
            shutil.move(str(source_path), str(archive_path))

            return archive_path

        except Exception as e:
            error_msg = f"Failed to move file to archive: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def write_sidecar(
        self, pdf_path: Path, result: ProcessingResult
    ) -> Optional[Path]:
        """
        Write a sidecar JSON file with processing information.

        Args:
            pdf_path: Path to the PDF file
            result: Processing result

        Returns:
            Path to sidecar file, or None if disabled

        Raises:
            RuntimeError: If writing fails
        """
        if not self.config.sidecar_enabled:
            return None

        sidecar_path = pdf_path.with_suffix(pdf_path.suffix + ".json")

        try:
            # Convert result to dict
            data = {
                "status": result.status.value,
                "original_path": str(result.original_path),
                "archive_path": str(result.archive_path) if result.archive_path else None,
                "ocr_applied": result.ocr_applied,
                "processing_time": result.processing_time,
                "timestamp": result.timestamp.isoformat(),
                "content_hash": result.content_hash,
                "metadata": result.metadata.dict() if result.metadata else None,
                "tagging": result.tagging.dict() if result.tagging else None,
                "error": result.error,
            }

            # Write JSON
            with open(sidecar_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Wrote sidecar file: {sidecar_path.name}")
            return sidecar_path

        except Exception as e:
            error_msg = f"Failed to write sidecar file: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def apply_macos_tags(self, file_path: Path, tags: List[str]) -> bool:
        """
        Apply macOS Finder tags to a file.

        Args:
            file_path: Path to the file
            tags: List of tag names

        Returns:
            True if successful, False otherwise
        """
        if not self.config.macos_tags.enabled:
            return False

        try:
            import sys

            if sys.platform != "darwin":
                logger.warning("macOS tags are only supported on macOS")
                return False

            # Import macOS-specific modules
            try:
                import Cocoa
                from Foundation import NSURL

                # Convert tags to NSArray
                url = NSURL.fileURLWithPath_(str(file_path))

                # Get existing tags
                existing_tags, error = url.resourceValuesForKeys_error_(
                    [Cocoa.NSURLTagNamesKey], None
                )

                if error:
                    logger.warning(f"Could not read existing tags: {error}")
                    existing_tags = {}

                # Merge with new tags
                current_tags = list(existing_tags.get(Cocoa.NSURLTagNamesKey, []))
                all_tags = list(set(current_tags + tags))

                # Set tags
                success, error = url.setResourceValue_forKey_error_(
                    all_tags, Cocoa.NSURLTagNamesKey, None
                )

                if success:
                    logger.info(f"Applied macOS tags to {file_path.name}: {tags}")
                    return True
                else:
                    logger.warning(f"Failed to set tags: {error}")
                    return False

            except ImportError:
                logger.warning(
                    "pyobjc not installed. Install with: pip install 'doctagger[macos]'"
                )
                return False

        except Exception as e:
            logger.warning(f"Failed to apply macOS tags: {e}")
            return False

    def cleanup_temp_files(self, temp_path: Path) -> None:
        """
        Clean up temporary files.

        Args:
            temp_path: Path to temporary file or directory
        """
        try:
            if temp_path.exists():
                if temp_path.is_file():
                    temp_path.unlink()
                    logger.debug(f"Deleted temp file: {temp_path}")
                elif temp_path.is_dir():
                    shutil.rmtree(temp_path)
                    logger.debug(f"Deleted temp directory: {temp_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")
