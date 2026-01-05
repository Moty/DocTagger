"""Test configuration."""

import pytest

from doctagger.config import Config


def test_config_defaults():
    """Test default configuration values."""
    config = Config()

    assert config.inbox_folder.name == "inbox"
    assert config.archive_folder.name == "archive"
    assert config.ollama.url == "http://localhost:11434"
    assert config.ollama.model == "llama2"
    assert config.ocr.enabled is True


def test_config_folders_created(tmp_path):
    """Test that configuration creates folders."""
    inbox = tmp_path / "test_inbox"
    archive = tmp_path / "test_archive"

    config = Config(inbox_folder=inbox, archive_folder=archive)

    assert inbox.exists()
    assert archive.exists()
