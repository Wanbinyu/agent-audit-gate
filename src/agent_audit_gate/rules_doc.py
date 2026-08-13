from __future__ import annotations

RULES: list[dict[str, str]] = [
    {
        "id": "R1",
        "name": "claims_never_enough",
        "summary": "model_claims alone cannot produce status=completed.",
    },
    {
        "id": "R2",
        "name": "writes_need_verification",
        "summary": (
            "If there is write activity and verification is required "
            "(default when writes exist), need ≥1 verification tool with ok "
            "and exit_code 0 (or no exit_code)."
        ),
    },
    {
        "id": "R3",
        "name": "failed_verification_veto",
        "summary": "Any failed verification tool blocks completion.",
    },
    {
        "id": "R4",
        "name": "claim_conflict",
        "summary": "claimed_status=completed with missing evidence → blocked + risk flag.",
    },
    {
        "id": "R5",
        "name": "readonly_ok",
        "summary": (
            "Non-write tasks with successful read/search/other tools can complete "
            "without a verification command when verification is not required."
        ),
    },
    {
        "id": "R6",
        "name": "partial_progress",
        "summary": (
            "Required verification missing, and claimed_status is not "
            "completed → partial. Claiming completed stays blocked."
        ),
    },
]


def rules_as_text() -> str:
    lines = [
        "agent-audit-gate rule set v1 (deterministic)",
        "Model prose never overrides tool evidence.",
        "",
    ]
    for rule in RULES:
        lines.append(f"{rule['id']}  {rule['name']}")
        lines.append(f"    {rule['summary']}")
        lines.append("")
    lines.append("Exit codes: 0 completed · 2 partial · 3 blocked · 1 input error")
    return "\n".join(lines)
