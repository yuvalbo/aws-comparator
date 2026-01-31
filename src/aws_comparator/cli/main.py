"""
CLI entry point for AWS Comparator.

This module provides the main entry point for the CLI tool,
referenced in pyproject.toml as aws_comparator.cli.main:cli.
"""

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

from aws_comparator.cli.commands import cli

# Initialize Rich console for shared use
console = Console()


def setup_logging(verbose: int = 0, quiet: bool = False) -> None:
    """
    Configure logging for the CLI application.

    Args:
        verbose: Verbosity level (0-3). Higher values show more detail.
        quiet: If True, suppress non-error output.
    """
    if quiet:
        level = logging.ERROR
    elif verbose >= 3:
        level = logging.DEBUG
    elif verbose >= 2:
        level = logging.DEBUG
    elif verbose >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    # Configure root logger with Rich handler
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=verbose >= 3,
                show_time=verbose >= 2,
                show_path=verbose >= 2,
            )
        ],
    )


def main() -> None:
    """
    Main entry point for the CLI.

    This function is called when running the CLI from the command line.
    It handles top-level exception catching and exit codes.
    """
    try:
        cli(standalone_mode=True)  # type: ignore[call-arg]
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


# Export the cli group for use as entry point
__all__ = ["cli", "console", "main", "setup_logging"]


if __name__ == "__main__":
    main()
