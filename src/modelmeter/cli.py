"""Typer CLI entrypoint.

IO layer only — argument parsing, file loading, output rendering.
Core logic lives in the package modules it calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from modelmeter import __version__
from modelmeter.config import load_benchmark_config

app = typer.Typer(
    name="modelmeter",
    help="Compare LLMs on quality, latency, token usage and cost.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(f"modelmeter {__version__}")


@app.command()
def check(
    config: Annotated[
        Path, typer.Option(help="Path to benchmark config JSON to validate.")
    ],
) -> None:
    """Validate a benchmark config file and report problems."""
    if not config.is_file():
        typer.secho(f"error: config file not found: {config}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    try:
        parsed = load_benchmark_config(config)
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports all parse errors
        typer.secho(f"error: invalid config: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"ok: {len(parsed.providers)} provider(s), "
        f"repeats={parsed.repeats}, dataset={parsed.dataset}"
    )


if __name__ == "__main__":
    app()
