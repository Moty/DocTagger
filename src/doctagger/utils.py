"""Utility functions for DocTagger."""

import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Calculate hash of file content for deduplication.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, md5, etc.)

    Returns:
        Hex digest of file hash

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    hash_obj = hashlib.new(algorithm)

    # Read file in chunks to handle large files efficiently
    chunk_size = 65536  # 64KB chunks

    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hash_obj.update(chunk)

        file_hash = hash_obj.hexdigest()
        logger.debug(f"Calculated {algorithm} hash for {file_path.name}: {file_hash}")
        return file_hash

    except IOError as e:
        logger.error(f"Failed to read file for hashing: {file_path}")
        raise IOError(f"Cannot read file {file_path}: {e}")


def find_duplicate_by_hash(
    file_hash: str,
    search_dirs: list[Path],
    exclude_path: Optional[Path] = None
) -> Optional[Path]:
    """
    Find if a file with the same hash exists in the given directories.

    Searches for sidecar JSON files containing the hash and returns the
    corresponding PDF path if found.

    Args:
        file_hash: SHA-256 hash to search for
        search_dirs: List of directories to search in
        exclude_path: Optional path to exclude from search (e.g., current file)

    Returns:
        Path to duplicate file if found, None otherwise
    """
    import json

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        # Search for .pdf.json sidecar files
        for sidecar_path in search_dir.rglob("*.pdf.json"):
            if exclude_path and sidecar_path == exclude_path.with_suffix(".pdf.json"):
                continue

            try:
                with open(sidecar_path, "r") as f:
                    data = json.load(f)

                # Check if hash matches
                if data.get("content_hash") == file_hash:
                    # Return corresponding PDF path
                    pdf_path = sidecar_path.with_suffix("")  # Remove .json extension
                    if pdf_path.exists():
                        logger.info(f"Found duplicate: {pdf_path} has same hash as {exclude_path.name if exclude_path else 'file'}")
                        return pdf_path

            except (json.JSONDecodeError, IOError) as e:
                logger.debug(f"Skipping {sidecar_path}: {e}")
                continue

    return None
