"""Test models."""

import pytest
from pydantic import ValidationError

from doctagger.models import TaggingResult, DocumentMetadata, ProcessingStatus


def test_tagging_result_validation():
    """Test TaggingResult validation."""
    result = TaggingResult(
        title="Test Document",
        document_type="invoice",
        tags=["test", "document"],
    )

    assert result.title == "Test Document"
    assert result.document_type == "invoice"
    assert len(result.tags) == 2
    assert result.confidence == 1.0


def test_tagging_result_tag_normalization():
    """Test that tags are normalized."""
    result = TaggingResult(
        title="Test",
        document_type="invoice",
        tags=["  Tag1  ", "Tag2", "  ", "Tag3"],
    )

    # Empty and whitespace-only tags should be removed
    assert "" not in result.tags
    # Tags should be stripped and lowercased
    assert "tag1" in result.tags
    assert "tag2" in result.tags


def test_document_metadata():
    """Test DocumentMetadata model."""
    metadata = DocumentMetadata(
        title="Test Document",
        keywords=["test", "document"],
    )

    assert metadata.title == "Test Document"
    assert metadata.creator == "DocTagger"
    assert len(metadata.keywords) == 2


def test_processing_status_enum():
    """Test ProcessingStatus enum."""
    assert ProcessingStatus.PENDING.value == "pending"
    assert ProcessingStatus.PROCESSING.value == "processing"
    assert ProcessingStatus.COMPLETED.value == "completed"
    assert ProcessingStatus.FAILED.value == "failed"
