# Quick start

## Install

```bash
pipx install git+https://github.com/Wanbinyu/agent-audit-gate.git@v0.3.2
audit-gate --version
```

## Use

```bash
audit-gate demo
audit-gate init run.trajectory.json
# edit tools / commands / exit codes
audit-gate check run.trajectory.json --pretty
```

Tool-event JSONL:

```bash
audit-gate from-events tools.jsonl --claimed completed --pretty
```

CI / scripts:

```bash
audit-gate check run.trajectory.json --quiet
# exit 3 => blocked
```

Optional: if `.claude/usage-gate/*.events.jsonl` already exists:

```bash
audit-gate from-session --pretty
```

## Status meanings

| status | exit | meaning |
|--------|------|---------|
| completed | 0 | enough evidence |
| partial | 2 | required verification missing, not claimed completed |
| blocked | 3 | missing/failed evidence or false completion claim |

Model prose alone is never enough.
