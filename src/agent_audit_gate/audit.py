from __future__ import annotations

from .audit_core_bridge import load_audit_core
from .models import AuditFinding, AuditReport, RunTrajectory, ToolEvent
from .version import __version__


def _tools_to_events(tools: list[ToolEvent]) -> list[dict]:
    events: list[dict] = []
    for t in tools:
        events.append(
            {
                "name": t.name,
                "ok": t.ok,
                "category": t.category,
                "path": t.path,
                "command": t.command,
                "exit_code": t.exit_code,
                "verification": t.verification,
                "summary": t.summary,
            }
        )
    return events


def audit_run(run: RunTrajectory) -> AuditReport:
    """Apply shared rule set v1 (same as Claude Code usage-gate plugin)."""
    core = load_audit_core()
    raw = core.audit_events(
        _tools_to_events(run.tools),
        claimed_status=run.claimed_status,
        model_claims=list(run.model_claims or []),
        requires_verification=run.task.requires_verification,
        files_changed=list(run.files_changed or []),
    )

    findings = [
        AuditFinding(
            code=str(f.get("code") or "unknown"),
            severity=f.get("severity") or "error",  # type: ignore[arg-type]
            message=str(f.get("message") or ""),
        )
        for f in (raw.get("findings") or [])
        if isinstance(f, dict)
    ]

    stats = raw.get("stats") or {}
    # Keep CLI-facing keys stable
    stats_out = {
        "tools_total": int(stats.get("tools_total") or stats.get("tools") or 0),
        "tools_ok": int(stats.get("tools_ok") or 0),
        "writes_ok": int(stats.get("writes_ok") or 0),
        "verifications_ok": int(
            stats.get("verifications_ok") or stats.get("verification_ok") or 0
        ),
        "verifications_failed": int(
            stats.get("verifications_failed")
            or stats.get("verification_failed")
            or 0
        ),
        "model_claims": int(stats.get("model_claims") or len(run.model_claims or [])),
        "files_changed": int(stats.get("files_changed") or len(run.files_changed or [])),
    }

    return AuditReport(
        gate_version=__version__,
        run_id=run.run_id,
        status=raw["status"],  # type: ignore[arg-type]
        claimed_status=run.claimed_status,
        missing_evidence=list(raw.get("missing_evidence") or []),
        risks=list(raw.get("risks") or []),
        findings=findings,
        summary=str(raw.get("summary") or raw.get("message") or ""),
        stats=stats_out,
        source=run.source,
    )


def load_run(path):  # type: ignore[no-untyped-def]
    from .io_util import load_run as _load

    return _load(path)
