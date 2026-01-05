# DocTagger

Automatically tag and organize PDF documents using local LLM (Ollama).

## Features

- 📂 **Folder Watching**: Automatically processes new PDFs added to an inbox folder
- 🔍 **OCR Support**: Ensures OCR text exists using OCRmyPDF
- 🤖 **LLM Tagging**: Uses local Ollama LLM to intelligently tag and categorize documents
- 📝 **Metadata Management**: Applies PDF metadata (keywords, title) in a portable way
- 🏷️ **macOS Tags**: Optional Finder tags support for macOS users
- 📦 **Auto-Organization**: Moves processed PDFs to organized archive structure
- 📋 **Traceability**: Writes sidecar JSON files for complete processing history
- 🌐 **HTTP API**: Optional FastAPI service for remote/web access
- 💻 **React UI**: Modern web interface for managing documents

## Quick Start

### Prerequisites

- Python 3.9+
- [Ollama](https://ollama.ai/) installed and running locally
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

# Configure settings
doctagger config --set ollama.model=llama2 --set ollama.url=http://localhost:11434
```

#### Server Mode

```bash
# Start the HTTP API server
doctagger-server

# Server will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Configuration

Create a `.env` file or `config.yaml` in your project directory:

```yaml
# Folder paths
inbox_folder: /path/to/inbox
archive_folder: /path/to/archive

# Ollama settings
ollama:
  url: http://localhost:11434
  model: llama2
  timeout: 60

# OCR settings
ocr:
  enabled: true
  language: eng
  skip_if_exists: true

# Tagging settings
tags:
  max_tags: 10
  custom_categories:
    - Invoice
    - Contract
    - Receipt
    - Letter

# macOS Finder tags (optional)
macos_tags:
  enabled: false
  color_mapping: true
```

## Architecture

```
DocTagger/
├── src/doctagger/           # Core Python package
│   ├── cli.py              # CLI entry point
│   ├── server.py           # FastAPI server
│   ├── watcher.py          # Folder watcher
│   ├── ocr.py              # OCR processing
│   ├── extractor.py        # Text extraction
│   ├── llm.py              # LLM integration
│   ├── normalizer.py       # Output normalization
│   ├── metadata.py         # PDF metadata handling
│   ├── organizer.py        # File organization
│   ├── config.py           # Configuration management
│   └── models.py           # Pydantic models
├── frontend/               # React frontend
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
- [ ] React frontend
- [ ] Batch processing
- [ ] Custom LLM prompts
- [ ] Plugin system
- [ ] Cloud storage support
