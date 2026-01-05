"""Command-line interface for DocTagger."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .config import Config, get_config, set_config
from .processor import DocumentProcessor
from .watcher import FolderWatcher


def setup_logging(verbose: bool = False, log_file: Optional[Path] = None) -> None:
    """
    Setup logging configuration.

    Args:
        verbose: Enable verbose (DEBUG) logging
        log_file: Optional log file path
    """
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=handlers,
    )


@click.group()
@click.version_option(version=__version__)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--log-file", type=click.Path(), help="Log file path")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, log_file: Optional[str]) -> None:
    """DocTagger - Automatically tag and organize PDF documents using local LLM."""
    ctx.ensure_object(dict)

    log_path = Path(log_file) if log_file else None
    setup_logging(verbose, log_path)

    # Store config in context
    ctx.obj["config"] = get_config()


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--skip-ocr", is_flag=True, help="Skip OCR processing")
@click.option("--skip-archive", is_flag=True, help="Skip archiving")
@click.pass_context
def process(
    ctx: click.Context, pdf_path: str, skip_ocr: bool, skip_archive: bool
) -> None:
    """Process a single PDF file."""
    config = ctx.obj["config"]
    processor = DocumentProcessor(config)

    pdf_file = Path(pdf_path)
    click.echo(f"Processing: {pdf_file.name}")

    result = processor.process(pdf_file, skip_ocr=skip_ocr, skip_archive=skip_archive)

    if result.status.value == "completed":
        click.echo(click.style("✓ Success!", fg="green"))
        click.echo(f"  Title: {result.tagging.title if result.tagging else 'N/A'}")
        click.echo(
            f"  Type: {result.tagging.document_type if result.tagging else 'N/A'}"
        )
        click.echo(
            f"  Tags: {', '.join(result.metadata.keywords) if result.metadata else 'N/A'}"
        )
        if result.archive_path:
            click.echo(f"  Archived to: {result.archive_path}")
        click.echo(f"  Processing time: {result.processing_time:.2f}s")
    else:
        click.echo(click.style("✗ Failed!", fg="red"))
        click.echo(f"  Error: {result.error}")
        sys.exit(1)


@cli.command()
@click.option(
    "--inbox",
    type=click.Path(file_okay=False),
    help="Inbox folder to watch (overrides config)",
)
@click.option(
    "--archive",
    type=click.Path(file_okay=False),
    help="Archive folder (overrides config)",
)
@click.option("--process-existing", is_flag=True, help="Process existing files first")
@click.pass_context
def watch(
    ctx: click.Context,
    inbox: Optional[str],
    archive: Optional[str],
    process_existing: bool,
) -> None:
    """Watch inbox folder for new PDF files."""
    config = ctx.obj["config"]

    # Override config if provided
    if inbox:
        config.inbox_folder = Path(inbox)
    if archive:
        config.archive_folder = Path(archive)

    # Update global config
    set_config(config)

    watcher = FolderWatcher(config)

    click.echo(f"Watching folder: {config.inbox_folder}")
    click.echo(f"Archive folder: {config.archive_folder}")
    click.echo("Press Ctrl+C to stop...")

    try:
        # Process existing files if requested
        if process_existing:
            click.echo("\nProcessing existing files...")
            count = watcher.process_existing()
            click.echo(f"Processed {count} existing files\n")

        # Start watching
        watcher.start(blocking=True)

    except KeyboardInterrupt:
        click.echo("\nStopping watcher...")
        watcher.stop()
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Check system status and configuration."""
    config = ctx.obj["config"]
    processor = DocumentProcessor(config)

    click.echo("DocTagger Status\n")

    # Check system
    system_status = processor.check_system()

    # Ollama
    if system_status["ollama_available"]:
        click.echo(click.style("✓ Ollama available", fg="green"))
        click.echo(f"  Model: {system_status['ollama_model']}")
    else:
        click.echo(click.style("✗ Ollama not available", fg="red"))
        click.echo("  Make sure Ollama is running: ollama serve")

    # Folders
    click.echo(f"\nInbox folder: {system_status['inbox_folder']}")
    click.echo(f"Archive folder: {system_status['archive_folder']}")

    # Features
    click.echo(f"\nOCR enabled: {system_status['ocr_enabled']}")
    click.echo(f"macOS tags enabled: {system_status['macos_tags_enabled']}")


@cli.command()
@click.option("--inbox", type=click.Path(file_okay=False), help="Set inbox folder")
@click.option("--archive", type=click.Path(file_okay=False), help="Set archive folder")
@click.option("--ollama-url", help="Set Ollama URL")
@click.option("--ollama-model", help="Set Ollama model")
@click.pass_context
def config(
    ctx: click.Context,
    inbox: Optional[str],
    archive: Optional[str],
    ollama_url: Optional[str],
    ollama_model: Optional[str],
) -> None:
    """Configure DocTagger settings."""
    cfg = ctx.obj["config"]

    if inbox:
        cfg.inbox_folder = Path(inbox)
        click.echo(f"Set inbox folder: {inbox}")

    if archive:
        cfg.archive_folder = Path(archive)
        click.echo(f"Set archive folder: {archive}")

    if ollama_url:
        cfg.ollama.url = ollama_url
        click.echo(f"Set Ollama URL: {ollama_url}")

    if ollama_model:
        cfg.ollama.model = ollama_model
        click.echo(f"Set Ollama model: {ollama_model}")

    if not any([inbox, archive, ollama_url, ollama_model]):
        # Show current config
        click.echo("Current Configuration:\n")
        click.echo(f"Inbox folder: {cfg.inbox_folder}")
        click.echo(f"Archive folder: {cfg.archive_folder}")
        click.echo(f"Ollama URL: {cfg.ollama.url}")
        click.echo(f"Ollama model: {cfg.ollama.model}")


def main() -> None:
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
