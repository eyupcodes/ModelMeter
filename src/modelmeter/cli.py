"""Typer CLI entrypoint.

IO layer only — argument parsing, file loading, output rendering.
Core logic lives in the package modules it calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from modelmeter import __version__
from modelmeter.config import load_benchmark_config
from modelmeter.dataset import load_tasks
from modelmeter.export import export_csv, export_json
from modelmeter.runner import run_benchmark
from modelmeter.scoring import ProviderSummary

app = typer.Typer(
    name="modelmeter",
    help="Compare LLMs on quality, latency, token usage and cost.",
    no_args_is_help=True,
)
console = Console(width=160)


def print_leaderboard(summaries: list[ProviderSummary]) -> None:
    """Render a Rich leaderboard table sorted by weighted score."""
    table = Table(title="🏆 ModelMeter Benchmark Leaderboard", header_style="bold cyan")
    table.add_column("Rank", justify="center", style="dim")
    table.add_column("Provider", style="bold")
    table.add_column("Score", justify="right", style="green bold")
    table.add_column("Avg Quality", justify="right")
    table.add_column("p50 Latency", justify="right")
    table.add_column("p95 Latency", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Cost / Test", justify="right")
    table.add_column("Failure Rate", justify="right")

    for idx, s in enumerate(summaries, start=1):
        fail_style = "red" if s.failure_rate > 0 else "dim"
        table.add_row(
            str(idx),
            s.provider_name,
            f"{s.weighted_score:.2f}",
            f"{s.avg_quality * 100:.1f}%",
            f"{s.p50_latency_ms:.1f}ms",
            f"{s.p95_latency_ms:.1f}ms",
            f"{s.total_tokens:,}",
            f"${s.cost_per_test:.5f}",
            f"[{fail_style}]{s.failure_rate * 100:.1f}%[/{fail_style}]",
        )
    console.print(table)


def print_failure_reasons(summaries: list[ProviderSummary]) -> None:
    """List the first error of each provider that had failed calls."""
    failed = [s for s in summaries if s.failure_rate > 0 and s.first_error]
    if not failed:
        return
    console.print()
    console.print("[red]Failures[/]")
    for s in failed:
        failures = s.total_calls - s.successful_calls
        console.print(
            f"  [bold]{escape(s.provider_name)}[/]: {failures}/{s.total_calls} "
            f"calls failed, first error: {escape(s.first_error or '')}",
            soft_wrap=True,
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


def _check_export_path(path: Path | None) -> None:
    """Exit with an error if ``path`` cannot be written, before any provider is called."""
    if path is None:
        return
    if path.is_dir():
        problem = "is a directory"
    elif not path.parent.is_dir():
        problem = f"directory does not exist: {path.parent}"
    else:
        return
    typer.secho(f"error: cannot write export {path}: {problem}", fg=typer.colors.RED)
    raise typer.Exit(code=1)


@app.command()
def run(
    config: Annotated[
        Path, typer.Option("--config", "-c", help="Path to benchmark config JSON.")
    ],
    export_json_path: Annotated[
        Path | None, typer.Option("--json", help="Path to export results as JSON.")
    ] = None,
    export_csv_path: Annotated[
        Path | None, typer.Option("--csv", help="Path to export results as CSV.")
    ] = None,
) -> None:
    """Execute a benchmark across all configured providers and show leaderboard."""
    if not config.is_file():
        typer.secho(f"error: config file not found: {config}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    _check_export_path(export_json_path)
    _check_export_path(export_csv_path)

    try:
        bench_cfg = load_benchmark_config(config)
    except Exception as exc:  # noqa: BLE001
        typer.secho(f"error: invalid config: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    # Resolve dataset relative to config file if not absolute
    dataset_path = bench_cfg.dataset
    if not dataset_path.is_absolute():
        dataset_path = config.parent / dataset_path

    if not dataset_path.is_file():
        typer.secho(
            f"error: dataset file not found: {dataset_path}", fg=typer.colors.RED
        )
        raise typer.Exit(code=1)

    try:
        tasks = load_tasks(dataset_path)
    except Exception as exc:  # noqa: BLE001
        typer.secho(f"error: failed loading dataset: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if not tasks:
        typer.secho("error: dataset is empty", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    console.print(
        f"[cyan]Starting benchmark:[/] {len(bench_cfg.providers)} provider(s), "
        f"{len(tasks)} task(s), {bench_cfg.repeats} repeat(s)"
    )

    summaries = run_benchmark(bench_cfg, tasks)

    console.print()
    print_leaderboard(summaries)
    print_failure_reasons(summaries)

    try:
        if export_json_path:
            export_json(summaries, export_json_path)
            console.print(f"[dim]Exported JSON -> {export_json_path}[/]")

        if export_csv_path:
            export_csv(summaries, export_csv_path)
            console.print(f"[dim]Exported CSV -> {export_csv_path}[/]")
    except OSError as exc:
        typer.secho(f"error: cannot write export: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
