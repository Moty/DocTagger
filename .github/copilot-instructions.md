# GitHub Copilot Instructions for DocTagger

## Project Overview
DocTagger is a Python project for using local LLMs to mass tag OCR PDF documents. Code should be optimized for document processing, OCR handling, and LLM integration.

## Code Style and Standards

### Python Style
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Use descriptive variable and function names
- Maximum line length: 88 characters (Black formatter standard)
- Use f-strings for string formatting
- Organize imports using isort standard (standard library, third-party, local)

### Documentation
- Include docstrings for all public modules, classes, and functions
- Use Google-style docstrings format
- Keep README.md updated with setup instructions and usage examples
- Document any PDF processing requirements or limitations

## Security Best Practices

### General Security
- Never commit API keys, tokens, or credentials to the repository
- Use environment variables for sensitive configuration
- Validate all user inputs, especially file paths and PDF inputs
- Sanitize file names and paths to prevent directory traversal attacks

### PDF and OCR Security
- Validate PDF files before processing to prevent malicious file execution
- Set reasonable limits on PDF file sizes
- Handle OCR text extraction errors gracefully
- Be cautious with temporary file handling and cleanup

### LLM Integration Security
- Never send sensitive or PII data to external LLM APIs without explicit consent
- Implement rate limiting for LLM API calls
- Handle LLM API errors and timeouts appropriately
- Validate and sanitize LLM responses before using them

## Testing Requirements

### Test Coverage
- Aim for at least 80% code coverage
- Use pytest for unit and integration tests
- Test edge cases, especially for PDF parsing and OCR failures
- Mock external LLM API calls in tests

### Test Organization
- Place tests in a `tests/` directory
- Mirror the source code structure in test files
- Use descriptive test function names (test_<feature>_<scenario>)
- Use fixtures for common test setup

## Dependencies and Libraries

### Preferred Libraries
- Use standard library solutions when possible
- For PDF processing: consider PyPDF2, pdfplumber, or pypdf
- For OCR: pytesseract or similar OCR libraries
- For LLM integration: use well-maintained libraries (e.g., langchain, openai, anthropic)
- Always specify exact versions in requirements.txt or pyproject.toml

### Adding New Dependencies
- Justify new dependencies in PR descriptions
- Check for security vulnerabilities before adding
- Prefer actively maintained libraries with good documentation
- Avoid dependencies with restrictive licenses

## Error Handling

### Error Messages
- Provide clear, actionable error messages
- Log errors with appropriate context
- Use Python's logging module instead of print statements
- Include file names, line numbers, or document IDs in error context

### Exception Handling
- Catch specific exceptions rather than bare except clauses
- Re-raise exceptions with additional context when appropriate
- Clean up resources (files, connections) in finally blocks or use context managers
- Handle PDF processing errors gracefully (corrupt files, missing pages, etc.)

## Performance Considerations

### PDF Processing
- Process PDFs in batches when possible
- Consider memory usage for large PDF files
- Implement progress indicators for long-running operations
- Clean up temporary files and resources promptly

### LLM Integration
- Implement caching for repeated LLM queries
- Use batch processing for multiple documents when supported
- Handle rate limits and implement exponential backoff
- Consider costs of LLM API calls in design decisions

## Git and Version Control

### Commit Messages
- Use clear, descriptive commit messages
- Start with a verb in imperative mood (Add, Fix, Update, etc.)
- Reference issue numbers when applicable

### Branch Strategy
- Follow the repository's branching conventions
- Keep changes focused and atomic
- Update .gitignore for any new build artifacts or cache files
