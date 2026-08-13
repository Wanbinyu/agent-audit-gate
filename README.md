# agent-audit-gate

[![CI](https://github.com/Wanbinyu/agent-audit-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/Wanbinyu/agent-audit-gate/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![Status](https://img.shields.io/badge/status-v0.3.0-blue)

**Sidecar completion audit for coding agents.**  
Evidence decides `completed` vs `blocked`. Model claims never upgrade a run alone.

> 旁路审计门：不替代 Claude Code / Cursor / Codex，只根据真实工具轨迹判定「能不能算做完」。

English + 中文说明见下文。详细上手：[docs/QUICKSTART.md](docs/QUICKSTART.md) · [docs/QUICKSTART.zh-CN.md](docs/QUICKSTART.zh-CN.md)

---

## Why

Coding agents often say “done” when:

- no tests were run,
- tests failed,
- or only prose claims exist.

**agent-audit-gate** is a tiny, local, deterministic gate you can run after an agent turn (or in CI). It does **not** call LLMs, does **not** proxy APIs, and does **not** modify your repo.

| Does | Does not |
|------|----------|
| Read a run trajectory / tool-event log | Route or intercept model requests |
| Emit `completed` / `partial` / `blocked` | Manage API keys or providers |
| Exit codes for scripts & CI | Replace your coding agent |
| Auto-detect common test commands in logs | Sandbox the agent |

Orthogonal to **Claude Code Router** / **CC Switch** (they manage *where* requests go). This tool manages *whether a result is trustworthy*.

---

## Install

Requires **Python 3.11+**.

### From this folder (development)

```bash
cd agent-audit-gate
python -m pip install -e ".[test]"
audit-gate --version
```

### With pipx (recommended for daily use)

```bash
# After you publish the GitHub repo:
pipx install git+https://github.com/Wanbinyu/agent-audit-gate.git

# Or install from a local checkout:
pipx install G:\skill\agent-audit-gate
```

Upgrade / uninstall:

```bash
pipx upgrade agent-audit-gate
pipx uninstall agent-audit-gate
```

---

## 60-second demo

```bash
# 1) Starter file you can edit
audit-gate init run.trajectory.json

# 2) Check examples shipped with the package (from repo root)
audit-gate check examples/run_completed.json --pretty
audit-gate check examples/run_blocked_no_test.json --pretty

# 3) From tool-event logs (JSONL) — common path for “export then audit”
audit-gate from-events examples/tool_events_ok.jsonl --claimed completed --pretty
audit-gate from-events examples/tool_events_blocked.jsonl --claimed completed --pretty

# 4) Replay a Claude Code usage-gate session (after cc-usage-gate is installed)
audit-gate from-session --pretty
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | `completed` |
| `2` | `partial` |
| `3` | `blocked` |
| `1` | bad input / usage |

```bash
audit-gate check examples/run_blocked_no_test.json --quiet
echo $?   # 3 on Unix
# PowerShell: echo $LASTEXITCODE
```

---

## Two ways to feed data

### A. Full trajectory JSON (schema v1)

See [examples/SCHEMA.md](examples/SCHEMA.md) and `audit-gate schema`.

```bash
audit-gate check path/to/run.trajectory.json
audit-gate check - < run.trajectory.json          # stdin
audit-gate validate path/to/run.trajectory.json   # schema only
```

### B. Tool-event log → audit (`from-events`)

One JSON object per line (JSONL), or a JSON array. Minimal fields:

```json
{"name": "edit_file", "ok": true, "path": "src/a.py"}
{"name": "run_command", "command": ["python", "-m", "pytest", "-q"], "exit_code": 0}
```

- `category` is inferred when omitted (`edit_file` → write, `run_command` → command, …).
- `verification` is auto-set for common test/build commands (`pytest`, `npm test`, …) unless `--no-auto-verify`.
- `ok` is inferred from `exit_code` when omitted.

```bash
audit-gate from-events tools.jsonl \
  --claimed completed \
  --summary "fix login bug" \
  --claim "all green" \
  --write-trajectory run.trajectory.json \
  --pretty
```

**Claude Code:** install [`cc-usage-gate`](../cc-usage-gate) so hooks write
`.claude/usage-gate/<session>.events.jsonl`, then:

```bash
audit-gate from-session --pretty
audit-gate from-session <session-id> --dir .claude/usage-gate --quiet
```

`--claimed` defaults to `completed` (same as the plugin Stop hook). Use
`--claimed unknown` if the run is still in progress and you want `partial`
instead of `blocked`.

Hand-authored trajectories and harness JSONL still work. Adapters stay thin;
core rules stay on schema v1.

---

## Rules (v1)

Print anytime:

```bash
audit-gate rules
```

1. **Claims never enough** — `model_claims` alone ⇒ not `completed`.
2. **Writes need verification** — write activity + verification required ⇒ need a green verification tool.
3. **Failed verification vetoes** — any failed verification ⇒ `blocked`.
4. **Claim conflict** — `claimed_status=completed` without evidence ⇒ `blocked` + risk flag.
5. **Read-only path** — successful read/search without writes can complete when verification is not required.
6. **Partial progress** — writes without a green test, and not claimed completed ⇒ `partial` (exit 2).

---

## Library API

```python
from pathlib import Path
from agent_audit_gate import audit_run, load_run, adapt_events_file

report = audit_run(load_run("run.trajectory.json"))
assert report.status in {"completed", "partial", "blocked"}

report2 = audit_run(
    adapt_events_file("tools.jsonl", claimed_status="completed")
)
print(report2.model_dump_json(indent=2))
```

---

## CI

Example workflow: [examples/github-action-audit.yml](examples/github-action-audit.yml).

```yaml
- run: audit-gate check artifacts/run.trajectory.json --pretty
```

Treat exit code `3` as hard failure for merge gates.

---

## Security & privacy

- **Fully offline.** No network calls, no telemetry.
- You control what goes into the trajectory; **do not paste API keys or secrets** into logs you share.
- See [SECURITY.md](SECURITY.md).

---

## Project layout

```
agent-audit-gate/
├── src/agent_audit_gate/   # library + CLI
├── examples/               # trajectories, JSONL, CI sample
├── tests/
├── docs/
├── README.md
└── pyproject.toml
```

In-IDE sibling: **cc-usage-gate** (Claude Code plugin) — same `audit_core` rules.
Optional sibling: **agent-cost-ledger** for token/cost accounting.

---

## Version

**0.3.0** — shared tagging with the plugin, real `partial`, `from-session` replay.

## License

MIT — see [LICENSE](LICENSE).
