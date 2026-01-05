# DocTagger User Guide

## Quick Start

### 1. Process a Single PDF

```bash
doctagger process /path/to/document.pdf
```

This will:
- Apply OCR if needed
- Extract text
- Tag using LLM
- Add metadata to PDF
- Move to archive folder
- Create sidecar JSON

### 2. Watch a Folder

```bash
doctagger watch
```

Or specify custom folders:

```bash
doctagger watch --inbox /path/to/inbox --archive /path/to/archive
```

### 3. Process Existing Files

```bash
doctagger watch --process-existing
```

## CLI Commands

### `doctagger process`

Process a single PDF file.

**Options:**
- `--skip-ocr` - Skip OCR processing
- `--skip-archive` - Don't move to archive (process in place)

**Examples:**

```bash
# Basic processing
doctagger process invoice.pdf

# Skip OCR for already-OCR'd PDFs
doctagger process --skip-ocr scanned-document.pdf

# Process without archiving
doctagger process --skip-archive --no-move document.pdf
```

### `doctagger watch`

Monitor inbox folder for new PDFs.

**Options:**
- `--inbox PATH` - Inbox folder (overrides config)
- `--archive PATH` - Archive folder (overrides config)
- `--process-existing` - Process existing files before watching

**Examples:**

```bash
# Start watching with default config
doctagger watch

# Watch custom folders
doctagger watch --inbox ~/Documents/Inbox --archive ~/Documents/Archive

# Process existing files first
doctagger watch --process-existing
```

### `doctagger status`

Check system status and configuration.

```bash
doctagger status
```

Shows:
- Ollama availability and model
- Folder paths
- Feature status (OCR, macOS tags)

### `doctagger config`

View or update configuration.

**Options:**
- `--inbox PATH` - Set inbox folder
- `--archive PATH` - Set archive folder
- `--ollama-url URL` - Set Ollama URL
- `--ollama-model MODEL` - Set Ollama model

**Examples:**

```bash
# View current config
doctagger config

# Set inbox folder
doctagger config --inbox /path/to/inbox

# Change Ollama model
doctagger config --ollama-model llama2
```

## HTTP API Server

### Starting the Server

```bash
doctagger-server
```

Server will start on `http://localhost:8000`

**Environment Variables:**
- `SERVER_HOST` - Host to bind to (default: 0.0.0.0)
- `SERVER_PORT` - Port to listen on (default: 8000)

### API Endpoints

#### GET `/api/status`

Get system status.

```bash
curl http://localhost:8000/api/status
```

Response:
```json
{
  "ollama_available": true,
  "ollama_model": "llama2",
  "inbox_folder": "/path/to/inbox",
  "archive_folder": "/path/to/archive",
  "watching": false,
  "processed_count": 42,
  "failed_count": 1
}
```

#### POST `/api/upload`

Upload a PDF for processing.

```bash
curl -X POST -F "file=@document.pdf" http://localhost:8000/api/upload
```

Response:
```json
{
  "request_id": "abc123",
  "filename": "document.pdf",
  "message": "File uploaded successfully, processing started"
}
```

#### GET `/api/process/{request_id}`

Check processing status.

```bash
curl http://localhost:8000/api/process/abc123
```

#### GET `/api/documents`

List processed documents.

```bash
curl http://localhost:8000/api/documents?limit=50
```

#### POST `/api/watcher/start`

Start folder watcher.

```bash
curl -X POST http://localhost:8000/api/watcher/start
```

#### POST `/api/watcher/stop`

Stop folder watcher.

```bash
curl -X POST http://localhost:8000/api/watcher/stop
```

#### WebSocket `/api/ws`

Real-time updates via WebSocket.

```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Update:', message);
};
```

## Configuration

### Archive Structure

Control how files are organized using the `ARCHIVE_STRUCTURE` setting:

```env
# Organize by year/month/type
ARCHIVE_STRUCTURE={year}/{month}/{document_type}

# Organize by type only
ARCHIVE_STRUCTURE={document_type}

# Organize by year and type
ARCHIVE_STRUCTURE={year}/{document_type}

# Include day
ARCHIVE_STRUCTURE={year}/{month}/{day}
```

Available variables:
- `{year}` - 4-digit year (e.g., 2024)
- `{month}` - 2-digit month (e.g., 01)
- `{day}` - 2-digit day (e.g., 15)
- `{document_type}` - Detected document type

### Custom Tags

Configure custom document categories:

```python
from doctagger.config import Config

config = Config()
config.tags.custom_categories = [
    "Invoice",
    "Receipt", 
    "Contract",
    "Letter",
    "Tax Document",
    "Medical Record"
]
```

Or via environment:

```env
TAGS__CUSTOM_CATEGORIES=Invoice,Receipt,Contract,Letter
```

### OCR Settings

```env
# Enable/disable OCR
OCR__ENABLED=true

# OCR language (use Tesseract language codes)
OCR__LANGUAGE=eng

# Skip OCR if text already exists
OCR__SKIP_IF_EXISTS=true

# Force OCR even if text exists
OCR__FORCE_OCR=false

# Deskew pages before OCR
OCR__DESKEW=true
```

### Ollama Settings

```env
# Ollama API URL
OLLAMA__URL=http://localhost:11434

# Model to use
OLLAMA__MODEL=llama2

# Request timeout (seconds)
OLLAMA__TIMEOUT=60

# Temperature for generation (0.0-1.0)
OLLAMA__TEMPERATURE=0.1
```

## macOS Finder Tags

Enable Finder tags on macOS:

```bash
pip install 'doctagger[macos]'
```

Configure:

```env
MACOS_TAGS__ENABLED=true
MACOS_TAGS__COLOR_MAPPING=true
```

Tags will be automatically applied to archived PDFs.

## Sidecar JSON Files

Each processed PDF gets a companion `.pdf.json` file containing:

```json
{
  "status": "completed",
  "original_path": "/path/to/inbox/document.pdf",
  "archive_path": "/path/to/archive/2024/01/invoice/document.pdf",
  "ocr_applied": true,
  "processing_time": 12.5,
  "timestamp": "2024-01-05T10:30:00",
  "metadata": {
    "title": "Invoice #12345",
    "keywords": ["invoice", "payment", "2024"]
  },
  "tagging": {
    "title": "Invoice #12345",
    "document_type": "invoice",
    "tags": ["invoice", "payment", "vendor"],
    "summary": "Invoice for services rendered",
    "date": "2024-01-15",
    "confidence": 0.95
  }
}
```

Disable sidecar files:

```env
SIDECAR_ENABLED=false
```

## Best Practices

### 1. Start with a Test Folder

Use a small test folder first:

```bash
mkdir -p ~/test-inbox ~/test-archive
doctagger watch --inbox ~/test-inbox --archive ~/test-archive
```

### 2. Choose the Right Model

- **llama2** - Good balance of speed and quality
- **mistral** - Faster, good for simple documents
- **llama3** - Better quality for complex documents

### 3. Organize by Use Case

For invoices:
```env
ARCHIVE_STRUCTURE={year}/{month}/Invoices
TAGS__CUSTOM_CATEGORIES=Invoice,Receipt,Bill
```

For general documents:
```env
ARCHIVE_STRUCTURE={year}/{document_type}
```

### 4. Monitor Performance

Check processing times:
```bash
doctagger status
```

Adjust OCR settings if slow:
```env
OCR__SKIP_IF_EXISTS=true
```

### 5. Backup Before Processing

Always backup your PDFs before mass processing:

```bash
cp -r ~/Documents/PDFs ~/Documents/PDFs.backup
```

## Troubleshooting

See [INSTALLATION.md](INSTALLATION.md#troubleshooting) for common issues.

## Examples

See the [examples/](../examples/) directory for:
- Configuration templates
- systemd service files
- Custom prompts
- Integration scripts
