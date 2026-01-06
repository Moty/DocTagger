# Installation Guide

## Prerequisites

### Required

1. **Python 3.9+**
   ```bash
   python3 --version
   ```

2. **LLM Provider** - Choose one:
   
   **Option A: Ollama** (Local LLM server)
   - Download from [ollama.ai](https://ollama.ai)
   - Install and start the service:
     ```bash
     ollama serve
     ```
   - Pull a model (e.g., llama2):
     ```bash
     ollama pull llama2
     ```
   
   **Option B: LM Studio** (OpenAI-compatible)
   - Download from [lmstudio.ai](https://lmstudio.ai)
   - Load a model (e.g., GLM-4, Llama 3, Mistral)
   - Start the local server (default: `http://localhost:1234`)
   
   **Option C: Other OpenAI-compatible servers**
   - vLLM, text-generation-webui, or any OpenAI API compatible endpoint

3. **Tesseract OCR** (for OCRmyPDF)
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install tesseract-ocr
   ```
   
   **macOS:**
   ```bash
   brew install tesseract
   ```
   
   **Windows:**
   - Download from [GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)

### Optional (for macOS Finder tags)

- **pyobjc** (macOS only)
  ```bash
  pip install 'doctagger[macos]'
  ```

## Installation

### Option 1: Install from source (Development)

```bash
# Clone the repository
git clone https://github.com/Moty/DocTagger.git
cd DocTagger

# Install in development mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"

# Or with macOS support
pip install -e ".[macos]"
```

### Option 2: Install with Cloud Storage Support

```bash
# AWS S3 support
pip install -e ".[s3]"

# Google Cloud Storage support
pip install -e ".[gcs]"

# Azure Blob Storage support
pip install -e ".[azure]"

# All cloud providers
pip install -e ".[cloud]"

# Combine with other options
pip install -e ".[dev,s3,macos]"
```

### Option 3: Install from PyPI (When published)

```bash
pip install doctagger
```

## Configuration

### Environment Variables

Create a `.env` file in your working directory:

```bash
cp examples/.env.example .env
```

Edit `.env` with your settings:

```env
# Folder paths
INBOX_FOLDER=/path/to/inbox
ARCHIVE_FOLDER=/path/to/archive

# LLM Provider: 'ollama' or 'openai'
LLM_PROVIDER=ollama
LLM_MODEL=llama2

# Ollama settings (if LLM_PROVIDER=ollama)
LLM_OLLAMA_URL=http://localhost:11434

# OpenAI-compatible settings (if LLM_PROVIDER=openai)
# For LM Studio, vLLM, or other OpenAI API compatible servers
LLM_OPENAI_BASE_URL=http://localhost:1234/v1
LLM_OPENAI_API_KEY=not-needed

# OCR settings
OCR__ENABLED=true
OCR__LANGUAGE=eng

# Archive structure
ARCHIVE_STRUCTURE={year}/{month}/{document_type}
```

### Example: LM Studio Configuration

```env
LLM_PROVIDER=openai
LLM_MODEL=your-model-name
LLM_OPENAI_BASE_URL=http://localhost:1234/v1
LLM_OPENAI_API_KEY=not-needed
```

### Example: Cloud Storage Configuration

```env
# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Google Cloud Storage
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
```

### Configuration File

Alternatively, you can use the configuration programmatically:

```python
from doctagger.config import Config

config = Config(
    inbox_folder="/path/to/inbox",
    archive_folder="/path/to/archive",
    ollama__model="llama2"
)
```

## Verify Installation

```bash
# Check CLI is installed
doctagger --version

# Check system status
doctagger status

# Start the server
doctagger-server
```

## Frontend Setup (Optional)

### Install Node.js Dependencies

```bash
cd frontend
npm install
```

### Configure API URL

```bash
cp .env.example .env.local
```

Edit `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Run Development Server

```bash
npm run dev
```

Visit http://localhost:3000

### Build for Production

```bash
npm run build
npm start
```

## Running as a Service

### systemd (Linux)

1. Copy the service file:
   ```bash
   sudo cp examples/doctagger.service /etc/systemd/system/
   ```

2. Edit the service file with your paths:
   ```bash
   sudo nano /etc/systemd/system/doctagger.service
   ```

3. Enable and start:
   ```bash
   sudo systemctl enable doctagger
   sudo systemctl start doctagger
   ```

### launchd (macOS)

Create `~/Library/LaunchAgents/com.doctagger.watcher.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.doctagger.watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/doctagger</string>
        <string>watch</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.doctagger.watcher.plist
```

## Troubleshooting

### LLM Connection Issues

**For Ollama:**
- Ensure Ollama is running: `ollama list`
- Check the URL in config: `LLM_OLLAMA_URL=http://localhost:11434`
- Test connectivity: `curl http://localhost:11434/api/tags`

**For LM Studio:**
- Ensure LM Studio server is running (check the "Server" tab)
- Verify the model is loaded
- Test connectivity: `curl http://localhost:1234/v1/models`
- Check your `.env` settings: `LLM_PROVIDER=openai`

### OCR Failures

- Install Tesseract: See prerequisites above
- Check language support: `tesseract --list-langs`
- Try disabling OCR: `OCR__ENABLED=false`

### Permission Issues

- Ensure inbox/archive folders are writable
- Check file permissions on PDFs
- Run with appropriate user permissions

### Import Errors

- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python3 --version` (should be 3.9+)

## Next Steps

- Read the [User Guide](USER_GUIDE.md)
- Check out [API Documentation](API.md)
- See [Examples](examples/)
