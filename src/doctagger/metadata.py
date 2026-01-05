"""PDF metadata handling."""

import logging
from pathlib import Path
from typing import Optional

from PyPDF2 import PdfReader, PdfWriter

from .models import DocumentMetadata

logger = logging.getLogger(__name__)


class MetadataWriter:
    """Writes metadata to PDF files."""

    def __init__(self):
        """Initialize metadata writer."""
        pass

    def write_metadata(
        self, pdf_path: Path, metadata: DocumentMetadata, output_path: Optional[Path] = None
    ) -> Path:
        """
        Write metadata to a PDF file.

        Args:
            pdf_path: Path to the PDF file
            metadata: Metadata to write
            output_path: Output path (if None, overwrites input)

        Returns:
            Path to the output PDF

        Raises:
            RuntimeError: If writing fails
        """
        if output_path is None:
            output_path = pdf_path

        logger.info(f"Writing metadata to {pdf_path.name}")

        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            # Copy all pages
            for page in reader.pages:
                writer.add_page(page)

            # Set metadata
            metadata_dict = {}

            if metadata.title:
                metadata_dict["/Title"] = metadata.title
            if metadata.author:
                metadata_dict["/Author"] = metadata.author
            if metadata.subject:
                metadata_dict["/Subject"] = metadata.subject
            if metadata.keywords:
                # Join keywords with semicolons (PDF standard)
                metadata_dict["/Keywords"] = "; ".join(metadata.keywords)
            if metadata.creator:
                metadata_dict["/Creator"] = metadata.creator
            if metadata.producer:
                metadata_dict["/Producer"] = metadata.producer

            writer.add_metadata(metadata_dict)

            # Write to output
            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            logger.info(f"Successfully wrote metadata to {output_path.name}")
            return output_path

        except Exception as e:
            error_msg = f"Failed to write metadata: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def read_metadata(self, pdf_path: Path) -> DocumentMetadata:
        """
        Read metadata from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            DocumentMetadata

        Raises:
            RuntimeError: If reading fails
        """
        try:
            reader = PdfReader(pdf_path)
            meta = reader.metadata or {}

            # Extract keywords
            keywords = []
            if "/Keywords" in meta:
                keywords_str = meta["/Keywords"]
                # Split by semicolon or comma
                keywords = [
                    k.strip()
                    for k in keywords_str.replace(";", ",").split(",")
                    if k.strip()
                ]

            return DocumentMetadata(
                title=meta.get("/Title"),
                author=meta.get("/Author"),
                subject=meta.get("/Subject"),
                keywords=keywords,
                creator=meta.get("/Creator"),
                producer=meta.get("/Producer"),
            )

        except Exception as e:
            error_msg = f"Failed to read metadata: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
