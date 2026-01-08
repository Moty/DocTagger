"""Folder watcher for monitoring inbox."""

import logging
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any
from enum import Enum

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import Config, get_config
from .processor import DocumentProcessor
from .utils import calculate_file_hash, find_duplicate_by_hash

logger = logging.getLogger(__name__)


class BatchProcessingStatus(str, Enum):
    """Status of batch processing job."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BatchProcessor:
    """Manages batch processing of existing files with progress tracking."""

    def __init__(self, watcher: "FolderWatcher"):
        self.watcher = watcher
        self.status = BatchProcessingStatus.IDLE
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused by default

        # Progress tracking
        self.total_files = 0
        self.processed_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.current_file = ""
        self.files_to_process: List[Dict[str, Any]] = []
        self.processed_files: List[Dict[str, Any]] = []

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress of batch processing."""
        with self._lock:
            total_done = self.processed_count + self.skipped_count + self.failed_count
            return {
                "status": self.status.value,
                "total_files": self.total_files,
                "processed": self.processed_count,
                "skipped": self.skipped_count,
                "failed": self.failed_count,
                "current_file": self.current_file if self.current_file else None,
                "percent_complete": round(total_done / max(self.total_files, 1) * 100, 1),
                "files_to_process": [
                    {
                        "name": f["name"],
                        "path": f["path"],
                        "size": f["size"],
                        "modified": "",
                        "status": f["status"],
                    }
                    for f in self.files_to_process
                ],
                "processed_files": [
                    {
                        "name": f["name"],
                        "status": "success" if f.get("status") == "completed" else ("failed" if f.get("status") == "failed" else "skipped"),
                        "error": f.get("error"),
                        "result": f.get("result"),
                    }
                    for f in self.processed_files
                ],
            }

    def scan_files(self, skip_processed: bool = True, check_content_duplicates: bool = True) -> List[Dict[str, Any]]:
        """
        Scan inbox for files and categorize them.

        Args:
            skip_processed: Skip files that have already been processed
            check_content_duplicates: Check for content-based duplicates (slower but catches renamed duplicates)

        Returns:
            List of file info dicts with status
        """
        inbox = self.watcher.config.inbox_folder
        pdf_files = list(inbox.glob("*.pdf"))

        files = []
        for pdf_file in pdf_files:
            is_processed = self.watcher.is_already_processed(
                pdf_file, check_content=check_content_duplicates
            ) if skip_processed else False
            stat = pdf_file.stat()
            files.append({
                "name": pdf_file.name,
                "path": str(pdf_file),
                "size": stat.st_size,
                "modified": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(stat.st_mtime)),
                "status": "already_processed" if is_processed else "pending",
            })

        return files

    def start(self, skip_processed: bool = True, force_reprocess: bool = False) -> bool:
        """
        Start batch processing.

        Args:
            skip_processed: Skip files that have been processed before
            force_reprocess: Force reprocessing of all files (disables deduplication)

        Returns:
            True if batch started, False if already running
        """
        with self._lock:
            if self.status == BatchProcessingStatus.RUNNING:
                return False

            # Reset state
            self._stop_event.clear()
            self._pause_event.set()
            self.status = BatchProcessingStatus.RUNNING
            self.processed_count = 0
            self.failed_count = 0
            self.skipped_count = 0
            self.current_file = ""
            self.processed_files = []

            # Scan files
            # When force_reprocess=True, we set skip_processed=False to process everything
            # and disable content duplicate checking
            check_content = not force_reprocess
            all_files = self.scan_files(
                skip_processed=skip_processed and not force_reprocess,
                check_content_duplicates=check_content
            )
            self.files_to_process = [f for f in all_files if f["status"] == "pending"]
            self.skipped_count = len([f for f in all_files if f["status"] == "already_processed"])
            self.total_files = len(all_files)

        # Start processing thread
        thread = threading.Thread(target=self._process_files, daemon=True)
        thread.start()
        return True

    def pause(self) -> bool:
        """Pause batch processing."""
        with self._lock:
            if self.status != BatchProcessingStatus.RUNNING:
                return False
            self._pause_event.clear()
            self.status = BatchProcessingStatus.PAUSED
        return True

    def resume(self) -> bool:
        """Resume batch processing."""
        with self._lock:
            if self.status != BatchProcessingStatus.PAUSED:
                return False
            self._pause_event.set()
            self.status = BatchProcessingStatus.RUNNING
        return True

    def stop(self) -> bool:
        """Stop batch processing."""
        with self._lock:
            if self.status not in (BatchProcessingStatus.RUNNING, BatchProcessingStatus.PAUSED):
                return False
            self.status = BatchProcessingStatus.STOPPING
            self._stop_event.set()
            self._pause_event.set()  # Unpause to allow thread to exit
        return True

    def _process_files(self):
        """Background thread for processing files."""
        try:
            for file_info in self.files_to_process:
                # Check for stop signal
                if self._stop_event.is_set():
                    with self._lock:
                        self.status = BatchProcessingStatus.CANCELLED
                    logger.info("Batch processing cancelled")
                    return

                # Wait if paused
                self._pause_event.wait()

                # Check stop again after unpause
                if self._stop_event.is_set():
                    with self._lock:
                        self.status = BatchProcessingStatus.CANCELLED
                    return

                pdf_path = Path(file_info["path"])

                with self._lock:
                    self.current_file = file_info["name"]
                    file_info["status"] = "processing"

                try:
                    logger.info(f"Batch processing: {pdf_path.name}")
                    result = self.watcher.processor.process(pdf_path)

                    with self._lock:
                        if result.status.value == "completed":
                            self.processed_count += 1
                            file_info["status"] = "completed"
                            file_info["result"] = {
                                "title": result.tagging.title if result.tagging else None,
                                "document_type": result.tagging.document_type if result.tagging else None,
                                "tags": result.tagging.tags if result.tagging else [],
                                "date": result.tagging.date if result.tagging else None,
                                "summary": result.tagging.summary if result.tagging else None,
                                "entities": result.tagging.entities if result.tagging else [],
                            }
                        elif result.status.value == "skipped":
                            self.skipped_count += 1
                            file_info["status"] = "skipped"
                        else:
                            self.failed_count += 1
                            file_info["status"] = "failed"
                            file_info["error"] = result.error
                        self.processed_files.append(file_info.copy())
                        logger.info(f"Progress: {self.processed_count}/{self.total_files} processed, {self.failed_count} failed")

                except Exception as e:
                    logger.error(f"Error processing {pdf_path.name}: {e}")
                    with self._lock:
                        self.failed_count += 1
                        file_info["status"] = "failed"
                        file_info["error"] = str(e)
                        self.processed_files.append(file_info.copy())

            with self._lock:
                self.status = BatchProcessingStatus.COMPLETED
                self.current_file = ""
            logger.info(f"Batch processing completed: {self.processed_count} processed, {self.failed_count} failed, {self.skipped_count} skipped")

        except Exception as e:
            logger.error(f"Batch processing error: {e}", exc_info=True)
            with self._lock:
                self.status = BatchProcessingStatus.IDLE


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
        # Batch processor for handling existing files
        self.batch_processor = BatchProcessor(self)

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

    def is_already_processed(self, pdf_path: Path, check_content: bool = True) -> bool:
        """
        Check if a PDF has already been processed.

        A file is considered processed if:
        1. A sidecar JSON exists next to it, OR
        2. A file with same name exists in the archive folder, OR
        3. (if check_content=True) A file with same content hash exists anywhere

        Args:
            pdf_path: Path to the PDF file
            check_content: If True, also check for content-based duplicates

        Returns:
            True if already processed, False otherwise
        """
        # Check for sidecar JSON file
        sidecar_path = pdf_path.with_suffix(".pdf.json")
        if sidecar_path.exists():
            logger.debug(f"Sidecar exists for {pdf_path.name}, skipping")
            return True

        # Check if file exists in archive (check all subdirectories)
        archive = self.config.archive_folder
        if archive.exists():
            # Search archive for file with same name
            for archived_file in archive.rglob(pdf_path.name):
                if archived_file.is_file():
                    logger.debug(f"File {pdf_path.name} already in archive, skipping")
                    return True

        # Check for content-based duplicates
        if check_content:
            try:
                file_hash = calculate_file_hash(pdf_path)
                # Search inbox and archive for duplicates
                search_dirs = [self.config.inbox_folder]
                if archive.exists():
                    search_dirs.append(archive)

                duplicate = find_duplicate_by_hash(file_hash, search_dirs, exclude_path=pdf_path)
                if duplicate:
                    logger.info(
                        f"Content duplicate detected: {pdf_path.name} has same content as {duplicate.name}"
                    )
                    return True
            except Exception as e:
                logger.warning(f"Failed to check content duplicate for {pdf_path.name}: {e}")

        return False

    def process_existing(self, skip_processed: bool = True) -> dict:
        """
        Process all existing PDF files in the inbox.

        Args:
            skip_processed: If True, skip files that have already been processed

        Returns:
            Dict with counts: total, processed, skipped, failed
        """
        inbox = self.config.inbox_folder

        if not inbox.exists():
            raise RuntimeError(f"Inbox folder does not exist: {inbox}")

        pdf_files = list(inbox.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} existing PDF files")

        stats = {
            "total": len(pdf_files),
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "files": []
        }

        for pdf_file in pdf_files:
            # Check if already processed
            if skip_processed and self.is_already_processed(pdf_file):
                logger.info(f"Skipping already processed: {pdf_file.name}")
                stats["skipped"] += 1
                stats["files"].append({"name": pdf_file.name, "status": "skipped"})
                continue

            try:
                logger.info(f"Processing existing file: {pdf_file.name}")
                result = self.processor.process(pdf_file)

                if result.status.value == "completed":
                    stats["processed"] += 1
                    stats["files"].append({"name": pdf_file.name, "status": "completed"})
                    logger.info(f"Successfully processed: {pdf_file.name}")
                else:
                    stats["failed"] += 1
                    stats["files"].append({"name": pdf_file.name, "status": "failed", "error": result.error})
                    logger.error(f"Failed to process {pdf_file.name}: {result.error}")

            except Exception as e:
                stats["failed"] += 1
                stats["files"].append({"name": pdf_file.name, "status": "failed", "error": str(e)})
                logger.error(f"Error processing {pdf_file.name}: {e}", exc_info=True)

        logger.info(f"Processed {stats['processed']}, skipped {stats['skipped']}, failed {stats['failed']} of {stats['total']} files")
        return stats
