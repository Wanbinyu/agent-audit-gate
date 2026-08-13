# agent-audit-gate

[![CI](https://github.com/Wanbinyu/agent-audit-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/Wanbinyu/agent-audit-gate/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![Status](https://img.shields.io/badge/status-v0.3.2-blue)

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

Requires **Python 3.11+** and [pipx](https://pipx.pypa.io/).

```bash
pipx install git+https://github.com/Wanbinyu/agent-audit-gate.git@v0.3.2
audit-gate --version
```

From a clone (development):

```bash
git clone https://github.com/Wanbinyu/agent-audit-gate.git
cd agent-audit-gate
python -m pip install -e ".[test]"
```

Upgrade / uninstall:

```bash
pipx upgrade --pip-args='--force-reinstall' agent-audit-gate
pipx uninstall agent-audit-gate
```

---

## Use (after install, no clone needed)

```bash
audit-gate demo
audit-gate init run.trajectory.json
audit-gate check run.trajectory.json --pretty
```

`demo` runs packaged examples (write+tests → completed, no tests → blocked, etc.).

Then edit `run.trajectory.json` to match a real run and check again.

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | `completed` |
| `2` | `partial` |
| `3` | `blocked` |
| `1` | bad input / usage |

```bash
audit-gate check run.trajectory.json --quiet
echo $?   # 3 on Unix when blocked
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

If you already have `.claude/usage-gate/<session>.events.jsonl` (from a
Claude Code usage-gate hook):

```bash
audit-gate from-session --pretty
audit-gate from-session <session-id> --dir .claude/usage-gate --quiet
```

`--claimed` defaults to `completed`. Use `--claimed unknown` for in-progress
runs if you want `partial` instead of `blocked`.

This CLI does not require that plugin. Hand-authored trajectories and harness
JSONL always work.

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
5. **Read-only path** — successful read/search without writes can complete when verification is not required. If `requires_verification=true`, a green test is still required.
6. **Partial progress** — required verification missing, and not claimed completed ⇒ `partial` (exit 2).

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

Optional sibling: **[agent-cost-ledger](https://github.com/Wanbinyu/agent-cost-ledger)** for token/cost accounting.

---

## Version

**0.3.2** — `audit-gate demo` works after pipx (packaged examples).

## License

MIT — see [LICENSE](LICENSE).
