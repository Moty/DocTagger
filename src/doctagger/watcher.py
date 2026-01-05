"""Folder watcher for monitoring inbox."""

import logging
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import Config, get_config
from .processor import DocumentProcessor

logger = logging.getLogger(__name__)


class PDFHandler(FileSystemEventHandler):
    """Handles PDF file events."""

    def __init__(
        self,
        processor: DocumentProcessor,
        callback: Optional[Callable[[Path], None]] = None,
        debounce_seconds: float = 2.0,
    ):
        """
        Initialize PDF handler.

        Args:
            processor: DocumentProcessor instance
            callback: Optional callback to call after processing
            debounce_seconds: Seconds to wait before processing (for file copying)
        """
        super().__init__()
        self.processor = processor
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._processing = set()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation event."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process PDF files
        if file_path.suffix.lower() != ".pdf":
            return

        # Avoid processing the same file multiple times
        if file_path in self._processing:
            return

        logger.info(f"New PDF detected: {file_path.name}")

        # Wait for file to be fully written
        time.sleep(self.debounce_seconds)

        # Check if file still exists and is readable
        if not file_path.exists():
            logger.warning(f"File disappeared: {file_path.name}")
            return

        try:
            # Mark as processing
            self._processing.add(file_path)

            # Process the PDF
            result = self.processor.process(file_path)

            if result.status.value == "completed":
                logger.info(f"Successfully processed: {file_path.name}")
            else:
                logger.error(f"Processing failed for {file_path.name}: {result.error}")

            # Call callback if provided
            if self.callback:
                self.callback(file_path)

        except Exception as e:
            logger.error(f"Unexpected error processing {file_path.name}: {e}", exc_info=True)

        finally:
            # Remove from processing set
            self._processing.discard(file_path)


class FolderWatcher:
    """Watches a folder for new PDF files."""

    def __init__(
        self,
        config: Optional[Config] = None,
        callback: Optional[Callable[[Path], None]] = None,
    ):
        """
        Initialize folder watcher.

        Args:
            config: Configuration instance
            callback: Optional callback to call after processing each file
        """
        self.config = config or get_config()
        self.callback = callback
        self.processor = DocumentProcessor(self.config)
        self.observer: Optional[Observer] = None
        self._running = False

    def start(self, blocking: bool = True) -> None:
        """
        Start watching the inbox folder.

        Args:
            blocking: If True, blocks until stopped. If False, runs in background.
        """
        if self._running:
            logger.warning("Watcher is already running")
            return

        inbox = self.config.inbox_folder

        if not inbox.exists():
            raise RuntimeError(f"Inbox folder does not exist: {inbox}")

        logger.info(f"Starting folder watcher on: {inbox}")

        # Create event handler
        event_handler = PDFHandler(
            processor=self.processor,
            callback=self.callback,
        )

        # Create observer
        self.observer = Observer()
        self.observer.schedule(event_handler, str(inbox), recursive=False)
        self.observer.start()
        self._running = True

        logger.info("Folder watcher started successfully")

        if blocking:
            try:
                while self._running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                self.stop()

    def stop(self) -> None:
        """Stop watching the folder."""
        if not self._running:
            logger.warning("Watcher is not running")
            return

        logger.info("Stopping folder watcher...")

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None

        self._running = False
        logger.info("Folder watcher stopped")

    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running

    def process_existing(self) -> int:
        """
        Process all existing PDF files in the inbox.

        Returns:
            Number of files processed
        """
        inbox = self.config.inbox_folder

        if not inbox.exists():
            raise RuntimeError(f"Inbox folder does not exist: {inbox}")

        pdf_files = list(inbox.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} existing PDF files")

        processed_count = 0

        for pdf_file in pdf_files:
            try:
                logger.info(f"Processing existing file: {pdf_file.name}")
                result = self.processor.process(pdf_file)

                if result.status.value == "completed":
                    processed_count += 1
                    logger.info(f"Successfully processed: {pdf_file.name}")
                else:
                    logger.error(f"Failed to process {pdf_file.name}: {result.error}")

            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}", exc_info=True)

        logger.info(f"Processed {processed_count} of {len(pdf_files)} files")
        return processed_count
