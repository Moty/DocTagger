# DocTagger

Automatically tag and organize PDF documents using local LLMs (Ollama, LM Studio, or any OpenAI-compatible server).

## Features

- 📂 **Folder Watching**: Automatically processes new PDFs added to an inbox folder
- 🔍 **OCR Support**: Ensures OCR text exists using OCRmyPDF
- 🤖 **Multi-LLM Support**: Works with Ollama, LM Studio, vLLM, or any OpenAI-compatible API
- 📝 **Metadata Management**: Applies PDF metadata (keywords, title) in a portable way
- 🏷️ **macOS Tags**: Optional Finder tags support for macOS users
- 📦 **Auto-Organization**: Moves processed PDFs to organized archive structure
- 📋 **Traceability**: Writes sidecar JSON files for complete processing history
- 🌐 **HTTP API**: FastAPI service with batch processing and custom prompts
- 💻 **React UI**: Modern Next.js web interface for managing documents
- 🔌 **Plugin System**: Extensible architecture for custom processors and storage
- ☁️ **Cloud Storage**: Support for AWS S3, Google Cloud Storage, and Azure Blob

## Quick Start

### Prerequisites

- Python 3.9+
- **LLM Server** (choose one):
  - [Ollama](https://ollama.ai/) - Local LLM server
  - [LM Studio](https://lmstudio.ai/) - Desktop app with OpenAI-compatible API
  - Any OpenAI-compatible API endpoint
- Optional: Tesseract OCR for better OCR results

### Installation

```bash
# Clone the repository
git clone https://github.com/Moty/DocTagger.git
cd DocTagger

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

### Basic Usage

#### CLI Mode

```bash
# Watch a folder for new PDFs
doctagger watch /path/to/inbox --archive /path/to/archive

# Process a single PDF
doctagger process /path/to/document.pdf

# Batch process multiple PDFs
doctagger batch /path/to/folder --parallel 4

# Check system status
doctagger status
```

#### Server Mode

```bash
# Start the HTTP API server
doctagger-server

# Server will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Configuration

Create a `.env` file in your project directory:

```env
# Folder paths
INBOX_FOLDER=/path/to/inbox
ARCHIVE_FOLDER=/path/to/archive

# LLM Provider: 'ollama' or 'openai'
LLM_PROVIDER=ollama
LLM_MODEL=llama2

# Ollama settings (if using Ollama)
LLM_OLLAMA_URL=http://localhost:11434

# OpenAI-compatible settings (if using LM Studio, vLLM, etc.)
# LLM_PROVIDER=openai
# LLM_MODEL=your-model-name
# LLM_OPENAI_BASE_URL=http://localhost:1234/v1
# LLM_OPENAI_API_KEY=not-needed

# OCR settings
OCR__ENABLED=true
OCR__LANGUAGE=eng
OCR__SKIP_IF_EXISTS=true

# Tagging settings
TAGS__MAX_TAGS=10
TAGS__CUSTOM_CATEGORIES=Invoice,Contract,Receipt,Letter

# macOS Finder tags (optional)
MACOS_TAGS__ENABLED=false
MACOS_TAGS__COLOR_MAPPING=true
```

## Architecture

```
DocTagger/
├── src/doctagger/           # Core Python package
│   ├── cli.py              # CLI entry point (with batch processing)
│   ├── server.py           # FastAPI server (with batch & prompts API)
│   ├── watcher.py          # Folder watcher
│   ├── ocr.py              # OCR processing
│   ├── extractor.py        # Text extraction
│   ├── llm.py              # Multi-provider LLM integration
│   ├── normalizer.py       # Output normalization
│   ├── metadata.py         # PDF metadata handling
│   ├── organizer.py        # File organization
│   ├── config.py           # Configuration management
│   ├── models.py           # Pydantic models
│   ├── plugins.py          # Plugin system
│   └── storage.py          # Cloud storage backends
├── frontend/               # Next.js React frontend
│   └── ...
├── tests/                  # Test suite
├── examples/               # Example configs
└── docs/                   # Documentation
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
ruff check src/ tests/

# Type checking
mypy src/
```

## API Documentation

When running the server, visit `http://localhost:8000/docs` for interactive API documentation.

Key endpoints:
- `POST /api/process` - Process a single document
- `GET /api/status` - Get processing status
- `GET /api/documents` - List processed documents
- `WS /api/ws` - WebSocket for real-time updates

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please read our contributing guidelines first.

## Roadmap

- [x] Core PDF processing pipeline
- [x] CLI interface
- [x] FastAPI server
- [x] React frontend (Next.js with TypeScript)
- [x] Batch processing (CLI and API)
- [x] Custom LLM prompts
- [x] Plugin system
- [x] Cloud storage support (S3, GCS, Azure)
- [x] OpenAI-compatible LLM support (LM Studio, etc.)

## Cloud Storage

DocTagger supports multiple cloud storage backends. Install the optional dependencies:

```bash
# AWS S3
pip install "doctagger[s3]"

# Google Cloud Storage
pip install "doctagger[gcs]"

# Azure Blob Storage
pip install "doctagger[azure]"

# All cloud providers
pip install "doctagger[cloud]"
```

## LLM Providers

DocTagger supports multiple LLM backends:

- **Ollama** (default): Local LLM server
- **OpenAI-compatible**: LM Studio, vLLM, or any OpenAI API compatible server

Configure in `.env`:

```env
# For Ollama (default)
LLM_PROVIDER=ollama
LLM_MODEL=llama2
LLM_OLLAMA_URL=http://localhost:11434

# For LM Studio or OpenAI-compatible
LLM_PROVIDER=openai
LLM_MODEL=your-model-name
LLM_OPENAI_BASE_URL=http://localhost:1234/v1
LLM_OPENAI_API_KEY=not-needed
```
