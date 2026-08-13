from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .adapters import adapt_events_file, trajectory_template
from .audit import audit_run
from .io_util import load_run
from .models import AuditReport, RunTrajectory
from .rules_doc import rules_as_text
from .session_import import resolve_usage_gate_events
from .version import __version__

app = typer.Typer(
    name="audit-gate",
    help=(
        "Sidecar completion audit for coding agents.\n"
        "Evidence decides completed vs blocked — model claims never upgrade alone."
    ),
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()
err_console = Console(stderr=True)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        is_eager=True,
    ),
) -> None:
    if version:
        typer.echo(f"agent-audit-gate {__version__}")
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@app.command("check")
def check(
    trajectory: str = typer.Argument(
        ...,
        help="Trajectory JSON path, or '-' for stdin",
    ),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        "-p",
        help="Human-readable output instead of JSON.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="No stdout report; only exit code.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write full report JSON to this file.",
    ),
) -> None:
    """Audit one run trajectory (schema v1).

    Exit codes: [green]0[/green] completed · [yellow]2[/yellow] partial ·
    [red]3[/red] blocked · [red]1[/red] input error.
    """
    try:
        run = load_run(trajectory)
        report = audit_run(run)
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(1) from exc

    _emit_report(report, pretty=pretty, quiet=quiet, output=output)
    raise typer.Exit(report.exit_code())


@app.command("from-events")
def from_events(
    events: str = typer.Argument(
        ...,
        help="Tool events as JSONL or JSON array path, or '-' for stdin",
    ),
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Override run id"),
    claimed: str = typer.Option(
        "completed",
        "--claimed",
        help="What the agent claimed: completed|partial|blocked|unknown",
    ),
    summary: str = typer.Option("", "--summary", help="Task summary"),
    require_verify: Optional[bool] = typer.Option(
        None,
        "--require-verify/--no-require-verify",
        help="Force whether verification is required (default: auto from writes)",
    ),
    claim: Optional[list[str]] = typer.Option(
        None,
        "--claim",
        help="Model claim text (repeatable)",
    ),
    no_auto_verify: bool = typer.Option(
        False,
        "--no-auto-verify",
        help="Do not auto-mark pytest/npm test/etc. as verification",
    ),
    write_trajectory: Optional[Path] = typer.Option(
        None,
        "--write-trajectory",
        help="Also save normalized trajectory JSON",
    ),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
    quiet: bool = typer.Option(False, "--quiet", "-q"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
) -> None:
    """Build a trajectory from tool-event logs and audit it.

    Each event is a JSON object, one per line (JSONL) or a JSON array.

    Minimal event fields: name, ok (or exit_code). Optional: category, path,
    command, verification, summary.
    """
    if claimed not in {"completed", "partial", "blocked", "unknown"}:
        err_console.print(f"[red]error:[/red] invalid --claimed {claimed!r}")
        raise typer.Exit(1)

    try:
        run = adapt_events_file(
            events,
            run_id=run_id,
            claimed_status=claimed,
            summary=summary,
            requires_verification=require_verify,
            model_claims=list(claim or []),
            auto_verify=not no_auto_verify,
        )
        if write_trajectory is not None:
            write_trajectory.parent.mkdir(parents=True, exist_ok=True)
            write_trajectory.write_text(
                run.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )
        report = audit_run(run)
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(1) from exc

    _emit_report(report, pretty=pretty, quiet=quiet, output=output)
    raise typer.Exit(report.exit_code())


@app.command("from-session")
def from_session(
    session: Optional[str] = typer.Argument(
        None,
        help="usage-gate session id (omit to use latest_session.json)",
    ),
    events_dir: Optional[Path] = typer.Option(
        None,
        "--dir",
        help="Directory with *.events.jsonl (default: ./.claude/usage-gate then ~/.claude/usage-gate)",
    ),
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Override run id"),
    claimed: str = typer.Option(
        "completed",
        "--claimed",
        help="What the agent claimed: completed|partial|blocked|unknown",
    ),
    summary: str = typer.Option("", "--summary", help="Task summary"),
    require_verify: Optional[bool] = typer.Option(
        None,
        "--require-verify/--no-require-verify",
        help="Force whether verification is required (default: auto from writes)",
    ),
    claim: Optional[list[str]] = typer.Option(
        None,
        "--claim",
        help="Model claim text (repeatable)",
    ),
    no_auto_verify: bool = typer.Option(
        False,
        "--no-auto-verify",
        help="Do not auto-mark pytest/npm test/etc. as verification",
    ),
    write_trajectory: Optional[Path] = typer.Option(
        None,
        "--write-trajectory",
        help="Also save normalized trajectory JSON",
    ),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
    quiet: bool = typer.Option(False, "--quiet", "-q"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
) -> None:
    """Audit the latest (or named) cc-usage-gate session log.

    Plugin writes `.claude/usage-gate/<session>.events.jsonl`. This is the
    CI/replay path — same tagging and rules as the Stop hook.
    """
    if claimed not in {"completed", "partial", "blocked", "unknown"}:
        err_console.print(f"[red]error:[/red] invalid --claimed {claimed!r}")
        raise typer.Exit(1)

    try:
        events_path = resolve_usage_gate_events(session=session, events_dir=events_dir)
        run = adapt_events_file(
            events_path,
            run_id=run_id or session,
            claimed_status=claimed,
            summary=summary,
            requires_verification=require_verify,
            model_claims=list(claim or []),
            auto_verify=not no_auto_verify,
            source=f"usage-gate:{events_path}",
        )
        if write_trajectory is not None:
            write_trajectory.parent.mkdir(parents=True, exist_ok=True)
            write_trajectory.write_text(
                run.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )
        report = audit_run(run)
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(1) from exc

    _emit_report(report, pretty=pretty, quiet=quiet, output=output)
    raise typer.Exit(report.exit_code())


@app.command("validate")
def validate(
    trajectory: str = typer.Argument(..., help="Trajectory JSON path or '-'"),
) -> None:
    """Validate trajectory schema only (no audit rules). Exit 0 if valid."""
    try:
        run = load_run(trajectory)
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[red]invalid:[/red] {exc}")
        raise typer.Exit(1) from exc
    typer.echo(
        json.dumps(
            {
                "ok": True,
                "run_id": run.run_id,
                "tools": len(run.tools),
                "schema_version": run.schema_version,
            },
            indent=2,
        )
    )


@app.command("init")
def init(
    path: Path = typer.Argument(
        Path("run.trajectory.json"),
        help="Where to write a starter trajectory",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing file"),
    run_id: str = typer.Option("my-run-1", "--run-id"),
    summary: str = typer.Option("Describe the task here", "--summary"),
) -> None:
    """Write a starter trajectory JSON you can edit."""
    if path.exists() and not force:
        err_console.print(
            f"[red]error:[/red] {path} exists (use --force to overwrite)"
        )
        raise typer.Exit(1)
    data = trajectory_template(run_id=run_id, summary=summary)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    typer.echo(f"wrote {path}")
    typer.echo("Edit tools/evidence, then: audit-gate check " + str(path))


@app.command("rules")
def rules() -> None:
    """Print the deterministic rule set."""
    typer.echo(rules_as_text())


@app.command("schema")
def schema() -> None:
    """Print trajectory JSON Schema (draft 2020-12 subset as object)."""
    # Keep inline so the wheel has no extra package-data packaging footguns.
    schema_obj = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://local/agent-audit-gate/trajectory-v1.json",
        "title": "agent-audit-gate RunTrajectory v1",
        "type": "object",
        "required": ["schema_version", "run_id", "tools"],
        "properties": {
            "schema_version": {"const": "1"},
            "run_id": {"type": "string", "minLength": 1},
            "claimed_status": {
                "type": "string",
                "enum": ["completed", "partial", "blocked", "unknown"],
            },
            "task": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "requires_verification": {"type": ["boolean", "null"]},
                    "risk": {"type": "string", "enum": ["low", "standard", "high"]},
                },
            },
            "tools": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "ok", "category"],
                    "properties": {
                        "name": {"type": "string"},
                        "ok": {"type": "boolean"},
                        "category": {
                            "type": "string",
                            "enum": ["read", "write", "command", "search", "other"],
                        },
                        "path": {"type": ["string", "null"]},
                        "command": {
                            "type": ["array", "string", "null"],
                            "items": {"type": "string"},
                        },
                        "exit_code": {"type": ["integer", "null"]},
                        "verification": {"type": "boolean"},
                        "summary": {"type": ["string", "null"]},
                    },
                },
            },
            "files_changed": {"type": "array", "items": {"type": "string"}},
            "model_claims": {"type": "array", "items": {"type": "string"}},
            "notes": {"type": ["string", "null"]},
            "source": {"type": ["string", "null"]},
        },
    }
    typer.echo(json.dumps(schema_obj, indent=2))


def _emit_report(
    report: AuditReport,
    *,
    pretty: bool,
    quiet: bool,
    output: Path | None,
) -> None:
    payload = report.model_dump_json(indent=2)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    if quiet:
        return
    if pretty:
        _print_pretty(report)
    else:
        # Avoid breaking pipes on Windows shells
        try:
            typer.echo(payload)
        except BrokenPipeError:
            pass


def _print_pretty(report: AuditReport) -> None:
    color = {"completed": "green", "partial": "yellow", "blocked": "red"}[report.status]
    subtitle = f"gate {report.gate_version}"
    if report.source:
        subtitle += f" · source={report.source}"
    console.print(
        Panel.fit(
            f"[{color}]{report.status.upper()}[/{color}]\n{report.summary}",
            title=f"audit-gate · {report.run_id}",
            subtitle=subtitle,
        )
    )
    if report.missing_evidence:
        console.print("[bold]missing_evidence[/bold]:")
        for item in report.missing_evidence:
            console.print(f"  • {item}")
    if report.risks:
        console.print("[bold]risks[/bold]:")
        for item in report.risks:
            console.print(f"  • {item}")
    if report.findings:
        table = Table(title="findings")
        table.add_column("code")
        table.add_column("severity")
        table.add_column("message")
        for finding in report.findings:
            table.add_row(finding.code, finding.severity, finding.message)
        console.print(table)
    if report.stats:
        console.print(
            "[dim]"
            + ", ".join(f"{k}={v}" for k, v in report.stats.items())
            + "[/dim]"
        )


if __name__ == "__main__":
    app()
