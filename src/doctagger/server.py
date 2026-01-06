"""FastAPI HTTP service for DocTagger."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import __version__
from .config import Config, get_config
from .models import (
    BatchFileStatus,
    BatchStatusResponse,
    BatchUploadResponse,
    CustomPrompt,
    DocumentListItem,
    ProcessingRequest,
    ProcessingResult,
    ProcessingStatus,
    ProcessingStatusResponse,
    SystemStatus,
)
from .processor import DocumentProcessor
from .watcher import FolderWatcher

logger = logging.getLogger(__name__)

# Global state
config: Config = get_config()
processor: DocumentProcessor = DocumentProcessor(config)
watcher: Optional[FolderWatcher] = None
processing_tasks: Dict[str, ProcessingResult] = {}
batch_tasks: Dict[str, Dict[str, any]] = {}  # batch_id -> {files: [...], status: {...}}
custom_prompts: Dict[str, CustomPrompt] = {}  # id -> CustomPrompt
websocket_connections: List[WebSocket] = []


# Create FastAPI app
app = FastAPI(
    title="DocTagger API",
    description="Automatically tag and organize PDF documents using local LLM",
    version=__version__,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadResponse(BaseModel):
    """Response for file upload."""

    request_id: str
    filename: str
    message: str


async def notify_websockets(message: dict) -> None:
    """Notify all connected websockets."""
    for ws in websocket_connections[:]:
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send to websocket: {e}")
            websocket_connections.remove(ws)


async def process_document_task(request_id: str, file_path: Path) -> None:
    """Background task to process a document."""
    try:
        logger.info(f"Starting background processing for {file_path.name}")

        # Update status
        processing_tasks[request_id] = ProcessingResult(
            status=ProcessingStatus.PROCESSING,
            original_path=file_path,
        )

        await notify_websockets(
            {
                "type": "status_update",
                "request_id": request_id,
                "status": "processing",
            }
        )

        # Process the document
        result = await asyncio.to_thread(processor.process, file_path)

        # Update result
        processing_tasks[request_id] = result

        # Notify via websockets
        await notify_websockets(
            {
                "type": "completed",
                "request_id": request_id,
                "status": result.status.value,
                "result": {
                    "title": result.tagging.title if result.tagging else None,
                    "document_type": result.tagging.document_type if result.tagging else None,
                    "tags": result.metadata.keywords if result.metadata else [],
                    "archive_path": str(result.archive_path) if result.archive_path else None,
                },
            }
        )

        logger.info(f"Background processing completed for {file_path.name}")

    except Exception as e:
        logger.error(f"Background processing failed: {e}", exc_info=True)
        processing_tasks[request_id] = ProcessingResult(
            status=ProcessingStatus.FAILED,
            original_path=file_path,
            error=str(e),
        )

        await notify_websockets(
            {
                "type": "error",
                "request_id": request_id,
                "error": str(e),
            }
        )


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": "DocTagger API",
        "version": __version__,
        "status": "running",
    }


@app.get("/api/status", response_model=SystemStatus)
async def get_status() -> SystemStatus:
    """Get system status."""
    system_status = processor.check_system()

    return SystemStatus(
        llm_available=system_status["llm_available"],
        llm_provider=system_status.get("llm_provider"),
        llm_model=system_status.get("llm_model"),
        ollama_available=system_status.get("ollama_available"),
        ollama_model=system_status.get("ollama_model"),
        inbox_folder=str(config.inbox_folder),
        archive_folder=str(config.archive_folder),
        watching=watcher.is_running() if watcher else False,
        processed_count=len([r for r in processing_tasks.values() if r.status == ProcessingStatus.COMPLETED]),
        failed_count=len([r for r in processing_tasks.values() if r.status == ProcessingStatus.FAILED]),
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadResponse:
    """
    Upload a PDF file for processing.

    Args:
        file: PDF file to process
        background_tasks: FastAPI background tasks

    Returns:
        UploadResponse with request ID
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Generate request ID
    request_id = str(uuid4())

    # Save to inbox
    file_path = config.inbox_folder / file.filename

    # Handle duplicates
    if file_path.exists():
        counter = 1
        stem = file_path.stem
        while file_path.exists():
            file_path = config.inbox_folder / f"{stem}_{counter}.pdf"
            counter += 1

    try:
        # Save uploaded file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Add background task
        background_tasks.add_task(process_document_task, request_id, file_path)

        return UploadResponse(
            request_id=request_id,
            filename=file_path.name,
            message="File uploaded successfully, processing started",
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@app.get("/api/process/{request_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(request_id: str) -> ProcessingStatusResponse:
    """
    Get processing status for a request.

    Args:
        request_id: Request ID

    Returns:
        ProcessingStatusResponse
    """
    if request_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Request not found")

    result = processing_tasks[request_id]

    return ProcessingStatusResponse(
        request_id=request_id,
        status=result.status,
        result=result if result.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED] else None,
        message=result.error if result.error else None,
    )


@app.get("/api/documents", response_model=List[DocumentListItem])
async def list_documents(limit: int = 100) -> List[DocumentListItem]:
    """
    List processed documents.

    Args:
        limit: Maximum number of documents to return

    Returns:
        List of DocumentListItem
    """
    documents = []

    # List files in archive
    archive_folder = config.archive_folder

    if not archive_folder.exists():
        return documents

    # Find all PDFs in archive
    pdf_files = list(archive_folder.rglob("*.pdf"))[:limit]

    for pdf_file in pdf_files:
        try:
            # Try to read sidecar JSON
            sidecar_path = pdf_file.with_suffix(pdf_file.suffix + ".json")

            if sidecar_path.exists():
                import json

                with open(sidecar_path) as f:
                    data = json.load(f)

                tagging = data.get("tagging", {})

                documents.append(
                    DocumentListItem(
                        path=str(pdf_file.relative_to(archive_folder)),
                        title=tagging.get("title"),
                        document_type=tagging.get("document_type"),
                        tags=tagging.get("tags", []),
                        processed_at=data.get("timestamp"),
                        size_bytes=pdf_file.stat().st_size,
                    )
                )
            else:
                # No sidecar, just include basic info
                documents.append(
                    DocumentListItem(
                        path=str(pdf_file.relative_to(archive_folder)),
                        title=pdf_file.stem,
                        document_type=None,
                        tags=[],
                        processed_at=pdf_file.stat().st_mtime,
                        size_bytes=pdf_file.stat().st_size,
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to read document info for {pdf_file}: {e}")
            continue

    return documents


@app.post("/api/watcher/start")
async def start_watcher() -> dict:
    """Start the folder watcher."""
    global watcher

    if watcher and watcher.is_running():
        return {"message": "Watcher is already running"}

    try:
        watcher = FolderWatcher(config)

        # Start in background thread
        import threading

        thread = threading.Thread(target=watcher.start, kwargs={"blocking": True})
        thread.daemon = True
        thread.start()

        return {"message": "Watcher started successfully"}

    except Exception as e:
        logger.error(f"Failed to start watcher: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start watcher: {e}")


@app.post("/api/watcher/stop")
async def stop_watcher() -> dict:
    """Stop the folder watcher."""
    global watcher

    if not watcher or not watcher.is_running():
        return {"message": "Watcher is not running"}

    try:
        watcher.stop()
        return {"message": "Watcher stopped successfully"}

    except Exception as e:
        logger.error(f"Failed to stop watcher: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop watcher: {e}")


@app.post("/api/watcher/process-existing")
async def process_existing_files(
    skip_processed: bool = True,
) -> dict:
    """
    Process all existing PDF files in the inbox folder.
    
    NOTE: This endpoint now redirects to the batch processor.
    Use /api/inbox/batch/start for new implementations.

    Args:
        skip_processed: If True (default), skip files that have already been processed

    Returns:
        Processing stats and batch progress
    """
    global watcher

    try:
        # Create watcher if not exists
        if not watcher:
            watcher = FolderWatcher(config)

        # Use the batch processor instead of the old method
        success = watcher.batch_processor.start(skip_processed=skip_processed)
        progress = watcher.batch_processor.get_progress()
        
        if success:
            return {
                "message": f"Started processing {progress['total_files']} files",
                "total": progress["total_files"],
                "to_process": progress["total_files"] - progress["skipped"],
                "skipped": progress["skipped"],
                "skipped_files": [],
            }
        else:
            return {
                "message": f"Batch processing already {progress['status']}",
                "total": progress["total_files"],
                "to_process": progress["total_files"] - progress["skipped"],
                "skipped": progress["skipped"],
                "skipped_files": [],
            }

    except Exception as e:
        logger.error(f"Failed to process existing files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process existing files: {e}")


# ============ Inbox Batch Processing Endpoints ============


@app.get("/api/inbox/files")
async def list_inbox_files(skip_processed: bool = True) -> dict:
    """
    List all PDF files in the inbox folder with their processing status.
    
    Args:
        skip_processed: If True, mark already processed files in the response
        
    Returns:
        List of files with status information
    """
    global watcher
    
    try:
        if not watcher:
            watcher = FolderWatcher(config)
        
        files = watcher.batch_processor.scan_files(skip_processed=False)
        
        return {
            "files": files,
            "total": len(files),
            "pending": len([f for f in files if f["status"] == "pending"]),
            "processed": len([f for f in files if f["status"] == "already_processed"]),
        }
        
    except Exception as e:
        logger.error(f"Failed to list inbox files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/inbox/batch/progress")
async def get_batch_progress() -> dict:
    """Get current batch processing progress."""
    global watcher
    
    if not watcher:
        return {
            "status": "idle",
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "current_file": None,
            "percent_complete": 0,
            "files_to_process": [],
            "processed_files": [],
        }
    
    return watcher.batch_processor.get_progress()


@app.post("/api/inbox/batch/start")
async def start_batch_processing(
    skip_processed: bool = True,
    force_reprocess: bool = False
) -> dict:
    """
    Start batch processing of inbox files.

    Args:
        skip_processed: If True, skip already processed files
        force_reprocess: If True, force reprocessing of all files (disables deduplication)
    """
    global watcher

    try:
        if not watcher:
            watcher = FolderWatcher(config)

        success = watcher.batch_processor.start(
            skip_processed=skip_processed,
            force_reprocess=force_reprocess
        )

        if success:
            return {
                "message": "Batch processing started",
                "progress": watcher.batch_processor.get_progress(),
            }
        else:
            progress = watcher.batch_processor.get_progress()
            return {
                "message": f"Cannot start: batch is currently {progress['status']}",
                "progress": progress,
            }

    except Exception as e:
        logger.error(f"Failed to start batch processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/inbox/batch/pause")
async def pause_batch_processing() -> dict:
    """Pause the current batch processing."""
    global watcher
    
    if not watcher:
        raise HTTPException(status_code=400, detail="Watcher not initialized")
    
    success = watcher.batch_processor.pause()
    
    return {
        "success": success,
        "progress": watcher.batch_processor.get_progress(),
    }


@app.post("/api/inbox/batch/resume")
async def resume_batch_processing() -> dict:
    """Resume paused batch processing."""
    global watcher
    
    if not watcher:
        raise HTTPException(status_code=400, detail="Watcher not initialized")
    
    success = watcher.batch_processor.resume()
    
    return {
        "success": success,
        "progress": watcher.batch_processor.get_progress(),
    }


@app.post("/api/inbox/batch/stop")
async def stop_batch_processing() -> dict:
    """Stop the current batch processing."""
    global watcher
    
    if not watcher:
        raise HTTPException(status_code=400, detail="Watcher not initialized")
    
    success = watcher.batch_processor.stop()
    
    return {
        "success": success,
        "progress": watcher.batch_processor.get_progress(),
    }


# ============ Batch Upload Processing Endpoints ============


@app.post("/api/batch/upload", response_model=BatchUploadResponse)
async def upload_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
) -> BatchUploadResponse:
    """
    Upload multiple PDF files for batch processing.

    Args:
        files: List of PDF files to process
        background_tasks: FastAPI background tasks

    Returns:
        BatchUploadResponse with batch ID and file info
    """
    batch_id = str(uuid4())
    file_info = []

    for file in files:
        if not file.filename.endswith(".pdf"):
            continue

        request_id = str(uuid4())
        file_path = config.inbox_folder / file.filename

        # Handle duplicates
        if file_path.exists():
            counter = 1
            stem = file_path.stem
            while file_path.exists():
                file_path = config.inbox_folder / f"{stem}_{counter}.pdf"
                counter += 1

        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            file_info.append({
                "request_id": request_id,
                "filename": file_path.name,
            })

            # Initialize processing status
            processing_tasks[request_id] = ProcessingResult(
                status=ProcessingStatus.PENDING,
                original_path=file_path,
            )

            # Add background task
            background_tasks.add_task(
                process_batch_document, batch_id, request_id, file_path
            )

        except Exception as e:
            logger.error(f"Failed to save file {file.filename}: {e}")
            continue

    # Initialize batch tracking
    batch_tasks[batch_id] = {
        "files": file_info,
        "total": len(file_info),
        "completed": 0,
        "failed": 0,
    }

    return BatchUploadResponse(
        batch_id=batch_id,
        files=file_info,
        message=f"Batch upload started with {len(file_info)} files",
    )


async def process_batch_document(batch_id: str, request_id: str, file_path: Path) -> None:
    """Background task to process a document in a batch."""
    try:
        await process_document_task(request_id, file_path)

        # Update batch status
        if batch_id in batch_tasks:
            result = processing_tasks.get(request_id)
            if result and result.status == ProcessingStatus.COMPLETED:
                batch_tasks[batch_id]["completed"] += 1
            elif result and result.status == ProcessingStatus.FAILED:
                batch_tasks[batch_id]["failed"] += 1

            # Notify batch progress
            await notify_websockets({
                "type": "batch_progress",
                "batch_id": batch_id,
                "progress": {
                    "completed": batch_tasks[batch_id]["completed"],
                    "total": batch_tasks[batch_id]["total"],
                },
            })

    except Exception as e:
        logger.error(f"Batch document processing failed: {e}")
        if batch_id in batch_tasks:
            batch_tasks[batch_id]["failed"] += 1


@app.get("/api/batch/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str) -> BatchStatusResponse:
    """
    Get status of a batch processing job.

    Args:
        batch_id: Batch ID

    Returns:
        BatchStatusResponse with detailed status
    """
    if batch_id not in batch_tasks:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch = batch_tasks[batch_id]
    files_status = []

    for file_info in batch["files"]:
        request_id = file_info["request_id"]
        result = processing_tasks.get(request_id)

        files_status.append(BatchFileStatus(
            request_id=request_id,
            filename=file_info["filename"],
            status=result.status if result else ProcessingStatus.PENDING,
            error=result.error if result else None,
        ))

    pending = sum(1 for f in files_status if f.status in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING])

    return BatchStatusResponse(
        batch_id=batch_id,
        total=batch["total"],
        completed=batch["completed"],
        failed=batch["failed"],
        pending=pending,
        files=files_status,
    )


# ============ Custom Prompts Endpoints ============


@app.get("/api/prompts", response_model=List[CustomPrompt])
async def list_prompts() -> List[CustomPrompt]:
    """List all custom prompts."""
    return list(custom_prompts.values())


@app.post("/api/prompts", response_model=CustomPrompt)
async def create_prompt(prompt: CustomPrompt) -> CustomPrompt:
    """
    Create a new custom prompt.

    Args:
        prompt: CustomPrompt data

    Returns:
        Created CustomPrompt
    """
    if not prompt.id:
        prompt.id = str(uuid4())

    if prompt.id in custom_prompts:
        raise HTTPException(status_code=400, detail="Prompt with this ID already exists")

    custom_prompts[prompt.id] = prompt
    return prompt


@app.get("/api/prompts/{prompt_id}", response_model=CustomPrompt)
async def get_prompt(prompt_id: str) -> CustomPrompt:
    """Get a specific prompt by ID."""
    if prompt_id not in custom_prompts:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return custom_prompts[prompt_id]


@app.put("/api/prompts/{prompt_id}", response_model=CustomPrompt)
async def update_prompt(prompt_id: str, prompt: CustomPrompt) -> CustomPrompt:
    """
    Update an existing prompt.

    Args:
        prompt_id: Prompt ID
        prompt: Updated CustomPrompt data

    Returns:
        Updated CustomPrompt
    """
    if prompt_id not in custom_prompts:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt.id = prompt_id
    custom_prompts[prompt_id] = prompt
    return prompt


@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str) -> dict:
    """Delete a prompt."""
    if prompt_id not in custom_prompts:
        raise HTTPException(status_code=404, detail="Prompt not found")

    del custom_prompts[prompt_id]
    return {"message": "Prompt deleted successfully"}


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    websocket_connections.append(websocket)

    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()

    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
        logger.info("WebSocket disconnected")


def main() -> None:
    """Main entry point for the server."""
    import sys

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger.info(f"Starting DocTagger server v{__version__}")
    logger.info(f"Inbox: {config.inbox_folder}")
    logger.info(f"Archive: {config.archive_folder}")

    uvicorn.run(
        app,
        host=config.server_host,
        port=config.server_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
