"""OCR processing using OCRmyPDF."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from .config import Config, get_config

logger = logging.getLogger(__name__)


class OCRProcessor:
    """Handles OCR processing of PDF files."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize OCR processor."""
        self.config = config or get_config()

    def needs_ocr(self, pdf_path: Path) -> bool:
        """
        Check if a PDF needs OCR processing.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            True if OCR is needed, False otherwise
        """
        if not self.config.ocr.enabled:
            return False

        if self.config.ocr.force_ocr:
            return True

        if not self.config.ocr.skip_if_exists:
            return True

        # Check if PDF already has text using pdfplumber
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                # Check first few pages for text
                for page_num, page in enumerate(pdf.pages[:3], 1):
                    text = page.extract_text()
                    if text and len(text.strip()) > 50:
                        logger.info(
                            f"PDF already has text content (page {page_num}), skipping OCR"
                        )
                        return False
            return True
        except Exception as e:
            logger.warning(f"Error checking PDF text content: {e}")
            return True

    def process(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Process a PDF with OCR.

        Args:
            input_path: Path to input PDF
            output_path: Path for output PDF (if None, overwrites input)

        Returns:
            Path to processed PDF

        Raises:
            RuntimeError: If OCR processing fails
        """
        if output_path is None:
            output_path = input_path

        if not self.needs_ocr(input_path):
            logger.info(f"Skipping OCR for {input_path.name}")
            if output_path != input_path:
                import shutil

                shutil.copy2(input_path, output_path)
            return output_path

        logger.info(f"Starting OCR processing for {input_path.name}")

        # Build OCRmyPDF command
        cmd = [
            "ocrmypdf",
            "--skip-text" if self.config.ocr.skip_if_exists else "--force-ocr",
            "-l",
            self.config.ocr.language,
        ]

        if self.config.ocr.deskew:
            cmd.append("--deskew")

        # Add optimization for faster processing
        cmd.extend(["--optimize", "1"])

        # Add input and output paths
        cmd.extend([str(input_path), str(output_path)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=False,
            )

            if result.returncode == 0:
                logger.info(f"OCR completed successfully for {input_path.name}")
                return output_path
            elif result.returncode == 6:
                # OCRmyPDF returns 6 if the PDF already has text and --skip-text is used
                logger.info(f"PDF already has text, no OCR needed: {input_path.name}")
                if output_path != input_path:
                    import shutil

                    shutil.copy2(input_path, output_path)
                return output_path
            else:
                error_msg = f"OCR failed with code {result.returncode}: {result.stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        except subprocess.TimeoutExpired:
            error_msg = f"OCR timeout for {input_path.name}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except FileNotFoundError:
            error_msg = "ocrmypdf not found. Please install: pip install ocrmypdf"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"OCR processing error: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
