"""Text extraction from PDF files."""

import logging
from pathlib import Path
from typing import Optional

import pdfplumber

logger = logging.getLogger(__name__)


class TextExtractor:
    """Extracts text from PDF files."""

    def __init__(self, max_pages: Optional[int] = None):
        """
        Initialize text extractor.

        Args:
            max_pages: Maximum number of pages to extract (None for all)
        """
        self.max_pages = max_pages

    def extract(self, pdf_path: Path) -> str:
        """
        Extract text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text

        Raises:
            RuntimeError: If extraction fails
        """
        logger.info(f"Extracting text from {pdf_path.name}")

        try:
            text_parts = []

            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                pages_to_process = (
                    min(total_pages, self.max_pages)
                    if self.max_pages
                    else total_pages
                )

                logger.info(
                    f"Processing {pages_to_process} of {total_pages} pages"
                )

                for page_num, page in enumerate(pdf.pages[:pages_to_process], 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                            logger.debug(
                                f"Extracted {len(page_text)} chars from page {page_num}"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {e}")
                        continue

            full_text = "\n\n".join(text_parts)

            if not full_text.strip():
                logger.warning(f"No text extracted from {pdf_path.name}")
                return ""

            logger.info(
                f"Successfully extracted {len(full_text)} characters from {pdf_path.name}"
            )
            return full_text

        except Exception as e:
            error_msg = f"Text extraction failed: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def extract_metadata(self, pdf_path: Path) -> dict:
        """
        Extract PDF metadata.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary of metadata

        Raises:
            RuntimeError: If metadata extraction fails
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                metadata = pdf.metadata or {}
                return {
                    "title": metadata.get("Title"),
                    "author": metadata.get("Author"),
                    "subject": metadata.get("Subject"),
                    "keywords": metadata.get("Keywords"),
                    "creator": metadata.get("Creator"),
                    "producer": metadata.get("Producer"),
                    "creation_date": metadata.get("CreationDate"),
                    "modification_date": metadata.get("ModDate"),
                    "page_count": len(pdf.pages),
                }
        except Exception as e:
            error_msg = f"Metadata extraction failed: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
