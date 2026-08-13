"""Shared deterministic completion-audit rules (stdlib only).

Used by:
  - Claude Code plugin Stop hook (cc-usage-gate)
  - agent-audit-gate CLI (imports this module by path)

Rule set v1 — model claims never upgrade completion alone.
"""
from __future__ import annotations

import re
from typing import Any

RULE_SET_VERSION = "1"

VERIFICATION_RE = re.compile(
    r"(pytest|python\s+-m\s+pytest|npm\s+test|npx\s+vitest|yarn\s+test|"
    r"pnpm\s+test|cargo\s+test|go\s+test|mvn\s+test|gradlew?\s+test|"
    r"make\s+test|tox|nox|playwright\s+test|eslint|mypy|ruff\s+check|"
    r"tsc\b.*--noEmit|vitest|jest\b|dotnet\s+test|flutter\s+test)",
    re.I,
)

WRITE_TOOLS = {
    "Write",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
    "create_file",
    "edit_file",
    "write_file",
    "str_replace",
    "search_replace",
}


def is_verification_command(command: str | None) -> bool:
    return bool(command and VERIFICATION_RE.search(str(command)))


def tool_category(tool_name: str, tool_input: dict[str, Any] | None = None) -> str:
    tool_input = tool_input or {}
    name = tool_name or ""
    if name in WRITE_TOOLS or name.endswith("Write") or name.endswith("Edit"):
        return "write"
    if name in {"Read", "read_file"}:
        return "read"
    if name in {"Glob", "Grep", "Search", "grep", "search_files", "codebase_search"}:
        return "search"
    if name in {"Bash", "Shell", "run_command", "PowerShell", "BashTool"}:
        return "command"
    if "command" in tool_input or "cmd" in tool_input:
        return "command"
    if "file_path" in tool_input and (
        "content" in tool_input
        or "new_string" in tool_input
        or "old_string" in tool_input
    ):
        return "write"
    # Loose names used by agent-audit-gate / generic JSONL
    key = name.strip().lower().replace("-", "_")
    if "write" in key or "edit" in key:
        return "write"
    if key.startswith("read"):
        return "read"
    if "grep" in key or "search" in key or "glob" in key:
        return "search"
    if "command" in key or "shell" in key or "bash" in key or key in {"run"}:
        return "command"
    return "other"


def summarize_events(events: list[dict[str, Any]]) -> dict[str, int]:
    writes = 0
    writes_ok = 0
    verif_ok = 0
    verif_fail = 0
    tools = 0
    tools_ok = 0
    commands = 0
    for e in events:
        tools += 1
        ok = bool(e.get("ok"))
        if ok:
            tools_ok += 1
        cat = e.get("category") or "other"
        if cat == "write":
            writes += 1
            if ok:
                writes_ok += 1
        if cat == "command":
            commands += 1
        if e.get("verification"):
            if ok and _exit_ok(e):
                verif_ok += 1
            else:
                verif_fail += 1
    return {
        "tools": tools,
        "tools_ok": tools_ok,
        "writes": writes,
        "writes_ok": writes_ok,
        "commands": commands,
        "verification_ok": verif_ok,
        "verification_failed": verif_fail,
    }


def _exit_ok(event: dict[str, Any]) -> bool:
    code = event.get("exit_code")
    if code is None:
        return True
    try:
        return int(code) == 0
    except (TypeError, ValueError):
        return True


def audit_events(
    events: list[dict[str, Any]],
    *,
    claimed_status: str = "unknown",
    model_claims: list[str] | None = None,
    requires_verification: bool | None = None,
    files_changed: list[str] | None = None,
) -> dict[str, Any]:
    """Audit a list of tool event dicts.

    Each event may include:
      name, ok, category, path, command, exit_code, verification
    """
    model_claims = model_claims or []
    files_changed = files_changed or []
    summary = summarize_events(events)

    has_write = summary["writes_ok"] > 0 or bool(files_changed)
    if requires_verification is None:
        needs_verify = has_write
    else:
        needs_verify = requires_verification

    missing: list[str] = []
    risks: list[str] = []
    findings: list[dict[str, str]] = []

    successful = [e for e in events if e.get("ok")]

    # R1: claims alone never enough
    if not successful and model_claims:
        findings.append(
            {
                "code": "claims_without_tools",
                "severity": "error",
                "message": "Only model_claims present; no successful tool evidence.",
            }
        )
        missing.append("at_least_one_successful_tool")

    if not successful and not model_claims and not events:
        findings.append(
            {
                "code": "empty_run",
                "severity": "error",
                "message": "No tools and no claims; nothing to audit as completed.",
            }
        )
        missing.append("at_least_one_successful_tool")

    # R3: failed verification veto
    if summary["verification_failed"] > 0:
        findings.append(
            {
                "code": "verification_failed",
                "severity": "error",
                "message": "At least one verification command failed.",
            }
        )
        missing.append("green_verification_command")
        risks.append("verification_command_failed")

    # R2: writes need green verification.
    # Claiming completed without a green test is a hard block.
    # Progress without that claim is partial (not a fake "done").
    write_without_verify = (
        needs_verify
        and has_write
        and summary["verification_ok"] == 0
    )
    if write_without_verify:
        findings.append(
            {
                "code": "write_without_verification",
                "severity": "error" if claimed_status == "completed" else "warn",
                "message": (
                    "Write activity observed but no successful verification "
                    "command (verification=true, ok, exit_code 0)."
                ),
            }
        )
        if claimed_status == "completed":
            if "green_verification_command" not in missing:
                missing.append("green_verification_command")

    # Readonly path info
    if not has_write and not needs_verify and successful:
        findings.append(
            {
                "code": "readonly_evidence_ok",
                "severity": "info",
                "message": "Read-only style task with successful tool evidence.",
            }
        )

    # R4: claim conflict
    if claimed_status == "completed" and missing:
        findings.append(
            {
                "code": "claim_conflict",
                "severity": "error",
                "message": "claimed_status is completed but required evidence is missing.",
            }
        )
        risks.append("agent_claimed_completed_without_evidence")

    # Dedup missing
    seen: set[str] = set()
    missing_unique: list[str] = []
    for item in missing:
        if item not in seen:
            seen.add(item)
            missing_unique.append(item)

    hard_block = bool(missing_unique) or summary["verification_failed"] > 0
    if hard_block:
        status = "blocked"
        message = "Blocked: missing or failed evidence; model claims cannot override."
    elif has_write and summary["verification_ok"] > 0:
        status = "completed"
        message = "Completed: writes backed by green verification evidence."
    elif not has_write and successful:
        status = "completed"
        message = "Completed: non-write task with successful tool evidence."
    elif write_without_verify and successful:
        status = "partial"
        message = (
            "Partial: writes observed without green verification "
            "(not claimed completed)."
        )
    elif successful:
        status = "completed"
        message = "Completed: tools succeeded and verification was not required."
    else:
        status = "blocked"
        message = "Blocked: insufficient evidence."

    if status == "completed" and claimed_status == "blocked":
        findings.append(
            {
                "code": "evidence_overrides_blocked_claim",
                "severity": "info",
                "message": "Evidence supports completed despite claimed_status=blocked.",
            }
        )

    return {
        "schema_version": "1",
        "rule_set_version": RULE_SET_VERSION,
        "status": status,
        "claimed_status": claimed_status,
        "message": message,
        "summary": message,
        "missing_evidence": missing_unique,
        "risks": list(dict.fromkeys(risks)),
        "findings": findings,
        "stats": {
            "tools_total": summary["tools"],
            "tools_ok": summary["tools_ok"],
            "writes_ok": summary["writes_ok"],
            "verifications_ok": summary["verification_ok"],
            "verifications_failed": summary["verification_failed"],
            "model_claims": len(model_claims),
            "files_changed": len(files_changed),
            # plugin-friendly aliases
            "tools": summary["tools"],
            "writes": summary["writes"],
            "writes_ok": summary["writes_ok"],
            "commands": summary["commands"],
            "verification_ok": summary["verification_ok"],
            "verification_failed": summary["verification_failed"],
        },
    }


def exit_code_for_status(status: str) -> int:
    if status == "completed":
        return 0
    if status == "partial":
        return 2
    return 3
