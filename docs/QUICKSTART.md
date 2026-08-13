# Quick start

## Install

```bash
python -m pip install -e .
# or: pipx install /path/to/agent-audit-gate
audit-gate --version
```

## Three workflows

### 1. Edit a template

```bash
audit-gate init run.trajectory.json
# fill real tools / commands / exit codes
audit-gate check run.trajectory.json --pretty
```

### 2. Tool-event JSONL

```bash
audit-gate from-events tools.jsonl --claimed completed --pretty
```

### 3. CI / scripts

```bash
audit-gate check run.trajectory.json --quiet
# exit 3 => blocked
```

### 4. Replay a Claude Code session

Install [`cc-usage-gate`](../../cc-usage-gate), use Claude Code as usual, then:

```bash
audit-gate from-session --pretty
```

## Status meanings

| status | exit | meaning |
|--------|------|---------|
| completed | 0 | enough evidence |
| partial | 2 | writes without a green test, and not claimed completed |
| blocked | 3 | missing/failed evidence or false completion claim |

Model prose alone is never enough.
