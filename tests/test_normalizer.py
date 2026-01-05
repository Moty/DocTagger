"""Test normalizer functionality."""

import pytest

from doctagger.normalizer import Normalizer
from doctagger.config import Config


@pytest.fixture
def normalizer():
    """Create normalizer instance."""
    return Normalizer()


def test_normalize_filename(normalizer):
    """Test filename normalization."""
    assert normalizer.normalize_filename("Invoice #123.pdf") == "Invoice_123.pdf"
    # Path separators are stripped, leaving only the filename part
    assert normalizer.normalize_filename("Test/File\\Name.pdf") == "File_Name.pdf"
    assert normalizer.normalize_filename("Multiple___Underscores.pdf") == "Multiple_Underscores.pdf"


def test_normalize_tag(normalizer):
    """Test tag normalization."""
    assert normalizer.normalize_tag("Invoice") == "invoice"
    assert normalizer.normalize_tag("Tax Forms") == "tax-forms"
    assert normalizer.normalize_tag("2023 Receipts!") == "2023-receipts"


def test_normalize_tags(normalizer):
    """Test tag list normalization."""
    tags = ["Invoice", "invoice", "Tax Forms", "2023"]
    normalized = normalizer.normalize_tags(tags)

    assert "invoice" in normalized
    assert "tax-forms" in normalized
    assert "2023" in normalized
    # Check deduplication
    assert normalized.count("invoice") == 1


def test_sanitize_title(normalizer):
    """Test title sanitization."""
    long_title = "A" * 150
    sanitized = normalizer.sanitize_title(long_title, max_length=100)

    assert len(sanitized) <= 103  # 100 + "..."
    assert sanitized.endswith("...")
