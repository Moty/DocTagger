"""Output normalization for filenames and tags."""

import logging
import re
from pathlib import Path
from typing import List

from .config import Config, get_config

logger = logging.getLogger(__name__)


class Normalizer:
    """Normalizes output for safe filenames and controlled tags."""

    def __init__(self, config: Config = None):
        """Initialize normalizer."""
        self.config = config or get_config()

    def normalize_filename(self, filename: str, max_length: int = 200) -> str:
        """
        Normalize a filename to be safe for file systems.

        Args:
            filename: Original filename
            max_length: Maximum filename length

        Returns:
            Safe filename
        """
        # Remove extension if present
        name, ext = Path(filename).stem, Path(filename).suffix

        # Replace unsafe characters with underscores
        pattern = self.config.safe_filename_pattern
        safe_name = re.sub(pattern, "_", name)

        # Remove leading/trailing underscores and spaces
        safe_name = safe_name.strip("_").strip()

        # Collapse multiple underscores
        safe_name = re.sub(r"_+", "_", safe_name)

        # Ensure it's not empty
        if not safe_name:
            safe_name = "untitled"

        # Truncate if too long (leave room for extension and counter if needed)
        if len(safe_name) > max_length:
            safe_name = safe_name[:max_length]

        # Add extension back
        return f"{safe_name}{ext or '.pdf'}"

    def normalize_tag(self, tag: str) -> str:
        """
        Normalize a single tag.

        Args:
            tag: Raw tag

        Returns:
            Normalized tag
        """
        # Convert to lowercase
        normalized = tag.lower().strip()

        # Replace spaces with hyphens
        normalized = normalized.replace(" ", "-")

        # Remove special characters except hyphens
        normalized = re.sub(r"[^a-z0-9\-]", "", normalized)

        # Collapse multiple hyphens
        normalized = re.sub(r"-+", "-", normalized)

        # Remove leading/trailing hyphens
        normalized = normalized.strip("-")

        return normalized

    def normalize_tags(self, tags: List[str]) -> List[str]:
        """
        Normalize a list of tags.

        Args:
            tags: List of raw tags

        Returns:
            List of normalized, deduplicated tags
        """
        normalized = [self.normalize_tag(tag) for tag in tags]

        # Remove empty tags and duplicates while preserving order
        seen = set()
        result = []
        for tag in normalized:
            if tag and tag not in seen:
                seen.add(tag)
                result.append(tag)

        return result

    def create_archive_path(
        self,
        original_filename: str,
        document_type: str,
        date: str = None,
    ) -> Path:
        """
        Create an archive path based on the configured structure.

        Args:
            original_filename: Original filename
            document_type: Type of document
            date: Document date (YYYY-MM-DD format)

        Returns:
            Path within the archive folder
        """
        from datetime import datetime

        # Parse date or use current date
        if date:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Invalid date format: {date}, using current date")
                dt = datetime.now()
        else:
            dt = datetime.now()

        # Normalize the filename
        safe_filename = self.normalize_filename(original_filename)

        # Build path using template
        template = self.config.archive_structure
        path_parts = template.format(
            year=dt.year,
            month=f"{dt.month:02d}",
            day=f"{dt.day:02d}",
            document_type=self.normalize_tag(document_type) or "other",
        )

        # Combine with archive folder
        archive_path = self.config.archive_folder / path_parts / safe_filename

        # Handle duplicate filenames
        if archive_path.exists():
            counter = 1
            stem = archive_path.stem
            ext = archive_path.suffix

            while archive_path.exists():
                new_name = f"{stem}_{counter}{ext}"
                archive_path = archive_path.parent / new_name
                counter += 1

        return archive_path

    def sanitize_title(self, title: str, max_length: int = 100) -> str:
        """
        Sanitize a document title.

        Args:
            title: Raw title
            max_length: Maximum length

        Returns:
            Sanitized title
        """
        # Remove extra whitespace
        sanitized = " ".join(title.split())

        # Truncate if needed
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rsplit(" ", 1)[0] + "..."

        return sanitized
