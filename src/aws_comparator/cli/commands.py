"""
CLI commands for AWS Comparator.

This module contains the Click command implementations for the CLI.
"""

import logging
import re
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from aws_comparator.core.config import AccountConfig, ComparisonConfig, OutputFormat
from aws_comparator.core.exceptions import (
    AuthenticationError,
    AWSComparatorError,
    InvalidAccountIdError,
    InvalidConfigError,
    ServiceNotSupportedError,
)
from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.orchestration.engine import ComparisonOrchestrator
from aws_comparator.output.formatters import get_formatter

# Initialize Rich console
console = Console()

# Version constant
VERSION = "0.1.0"


def validate_account_id(
    ctx: click.Context, param: click.Parameter, value: Optional[str]
) -> Optional[str]:
    """Validate AWS account ID is exactly 12 digits."""
    if not value:
        return value

    if not re.match(r"^\d{12}$", value):
        raise click.BadParameter(
            f"Account ID must be exactly 12 digits. Got: {value}"
        )
    return value


def parse_services(services_str: Optional[str]) -> Optional[list[str]]:
    """Parse comma-separated services string into list."""
    if not services_str:
        return None

    services = [s.strip().lower() for s in services_str.split(",") if s.strip()]
    return services if services else None


def setup_logging(verbose: int, quiet: bool) -> None:
    """Configure logging based on verbosity settings."""
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

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@click.group()
@click.version_option(version=VERSION, prog_name="aws-comparator")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """AWS Account Comparator - Compare AWS resources across accounts."""
    ctx.ensure_object(dict)


@cli.command("compare")
@click.option(
    "--account1", "-a1",
    required=True,
    callback=validate_account_id,
    help="First AWS account ID (12 digits).",
)
@click.option(
    "--account2", "-a2",
    required=True,
    callback=validate_account_id,
    help="Second AWS account ID (12 digits).",
)
@click.option(
    "--profile1", "-p1",
    default=None,
    help="AWS profile name for account1.",
)
@click.option(
    "--profile2", "-p2",
    default=None,
    help="AWS profile name for account2.",
)
@click.option(
    "--role1",
    default=None,
    help="IAM role ARN to assume for account1.",
)
@click.option(
    "--role2",
    default=None,
    help="IAM role ARN to assume for account2.",
)
@click.option(
    "--region", "-r",
    default="us-east-1",
    help="AWS region to compare (default: us-east-1).",
)
@click.option(
    "--services", "-s",
    default=None,
    help="Comma-separated list of services to compare (default: all).",
)
@click.option(
    "--output-format", "-f",
    type=click.Choice(["json", "yaml", "table"], case_sensitive=False),
    default="table",
    help="Output format (default: table).",
)
@click.option(
    "--output-file", "-o",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Output file path (default: stdout).",
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    default=None,
    help="Path to configuration file.",
)
@click.option(
    "--verbose", "-v",
    count=True,
    help="Increase verbosity (can be used multiple times).",
)
@click.option(
    "--quiet", "-q",
    is_flag=True,
    default=False,
    help="Suppress non-error output.",
)
@click.option(
    "--no-color",
    is_flag=True,
    default=False,
    help="Disable colored output.",
)
@click.pass_context
def compare(  # noqa: C901
    ctx: click.Context,
    account1: str,
    account2: str,
    profile1: Optional[str],
    profile2: Optional[str],
    role1: Optional[str],
    role2: Optional[str],
    region: str,
    services: Optional[str],
    output_format: str,
    output_file: Optional[str],
    config: Optional[str],
    verbose: int,
    quiet: bool,
    no_color: bool,
) -> None:
    """Compare resources between two AWS accounts."""
    # Mark config as used (reserved for future config file loading)
    _ = config

    # Setup logging
    setup_logging(verbose, quiet)

    # Create console with color settings
    output_console = Console(force_terminal=not no_color, no_color=no_color)

    try:
        # Parse services
        services_list = parse_services(services)

        # Validate services if specified
        if services_list:
            valid_services, invalid_services = ServiceRegistry.validate_services(
                services_list
            )
            if invalid_services:
                output_console.print(
                    f"[yellow]Warning: Unknown services will be ignored: "
                    f"{', '.join(invalid_services)}[/yellow]"
                )
            if not valid_services:
                raise ServiceNotSupportedError(
                    f"None of the specified services are supported: {services}"
                )
            services_list = valid_services

        # Build account configurations
        account1_config = AccountConfig(
            account_id=account1,
            profile=profile1,
            role_arn=role1,
            region=region,
        )

        account2_config = AccountConfig(
            account_id=account2,
            profile=profile2,
            role_arn=role2,
            region=region,
        )

        # Build comparison configuration
        comparison_config = ComparisonConfig(
            account1=account1_config,
            account2=account2_config,
            services=services_list,
            output_format=OutputFormat(output_format.lower()),
            output_file=Path(output_file) if output_file else None,
            no_color=no_color,
            verbose=verbose,
            quiet=quiet,
        )

        # Show startup info
        if not quiet:
            output_console.print(
                f"[bold]Comparing AWS accounts:[/bold] {account1} vs {account2}"
            )
            output_console.print(f"[bold]Region:[/bold] {region}")
            if services_list:
                output_console.print(
                    f"[bold]Services:[/bold] {', '.join(services_list)}"
                )
            else:
                output_console.print("[bold]Services:[/bold] all available")
            output_console.print()

        # Create orchestrator and run comparison
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=output_console,
            disable=quiet,
        ) as progress:
            task = progress.add_task("Comparing accounts...", total=None)

            def progress_callback(service_name: str, current: int, total: int) -> None:
                progress.update(
                    task,
                    description=f"Comparing {service_name} ({current}/{total})...",
                )

            orchestrator = ComparisonOrchestrator(
                config=comparison_config,
                progress_callback=progress_callback,
            )

            report = orchestrator.compare_accounts()

        # Format output
        formatter = get_formatter(output_format.lower(), use_colors=not no_color)

        if output_file:
            formatter.write_to_file(report, Path(output_file))
            if not quiet:
                output_console.print(
                    f"[green]Report written to: {output_file}[/green]"
                )
        else:
            output = formatter.format(report)
            # Write directly to stdout to avoid Rich re-processing ANSI codes
            sys.stdout.write(output)
            sys.stdout.write("\n")
            sys.stdout.flush()

        # Show summary
        if not quiet:
            output_console.print()
            summary = report.summary
            output_console.print(
                f"[bold]Summary:[/bold] {summary.total_changes} changes found "
                f"across {summary.total_services_with_changes}/"
                f"{summary.total_services_compared} services "
                f"in {summary.execution_time_seconds:.2f}s"
            )

            if summary.services_with_errors:
                output_console.print(
                    f"[yellow]Services with errors: "
                    f"{', '.join(summary.services_with_errors)}[/yellow]"
                )

        # Exit with appropriate code
        sys.exit(0)

    except KeyboardInterrupt:
        output_console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(130)
    except AuthenticationError as e:
        output_console.print(f"[red]Authentication error: {e.message}[/red]")
        if e.details.get("suggestion"):
            output_console.print(f"[yellow]Suggestion: {e.details['suggestion']}[/yellow]")
        sys.exit(1)
    except InvalidAccountIdError as e:
        output_console.print(f"[red]Invalid account ID: {e.message}[/red]")
        sys.exit(1)
    except InvalidConfigError as e:
        output_console.print(f"[red]Configuration error: {e.message}[/red]")
        sys.exit(1)
    except ServiceNotSupportedError as e:
        output_console.print(f"[red]Service error: {e.message}[/red]")
        output_console.print(
            "[yellow]Run 'aws-comparator list-services' to see available services.[/yellow]"
        )
        sys.exit(1)
    except AWSComparatorError as e:
        output_console.print(f"[red]Error: {e.message}[/red]")
        if e.details.get("suggestion"):
            output_console.print(f"[yellow]Suggestion: {e.details['suggestion']}[/yellow]")
        sys.exit(1)
    except Exception as e:
        output_console.print(f"[red]Unexpected error: {e}[/red]")
        if verbose >= 2:
            output_console.print_exception()
        sys.exit(1)


@cli.command("list-services")
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show detailed service information.",
)
@click.pass_context
def list_services(ctx: click.Context, verbose: bool) -> None:
    """List all supported AWS services."""
    # Mark ctx as used
    _ = ctx

    # Get all service info
    all_services = ServiceRegistry.get_all_service_info()

    if not all_services:
        console.print("[yellow]No services registered.[/yellow]")
        return

    # Create table
    table = Table(title="Supported AWS Services")
    table.add_column("Service Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    if verbose:
        table.add_column("Resource Types", style="green")

    # Sort services alphabetically
    for service_name in sorted(all_services.keys()):
        info = all_services[service_name]
        description = info.get("description", "")
        resource_types = info.get("resource_types", [])

        if verbose:
            resource_types_str = ", ".join(resource_types) if resource_types else "-"
            table.add_row(service_name, description, resource_types_str)
        else:
            table.add_row(service_name, description)

    console.print(table)
    console.print(f"\n[bold]Total services:[/bold] {len(all_services)}")


@cli.command("version")
def version() -> None:
    """Show version information."""
    console.print(f"[bold]aws-comparator[/bold] version {VERSION}")
