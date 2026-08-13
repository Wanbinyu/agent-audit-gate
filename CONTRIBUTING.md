# Contributing

Thanks for helping. Keep the product small.

## Principles

1. **Deterministic rules** — no LLM calls inside the gate.
2. **Evidence over prose** — model claims never override failed/missing verification.
3. **Adapters stay thin** — normalize vendor logs into schema v1; do not fork the rule engine.
4. **Offline by default** — no telemetry.

## Dev setup

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

## Pull requests

- Add/adjust tests for rule or adapter changes.
- Update `CHANGELOG.md` and `examples/` if user-visible.
- Do not expand scope into request routing, provider config, or full agents.

## Release checklist

1. `pytest -q` green on 3.11+  
2. If `audit_core.py` changed: copy `cc-usage-gate/scripts/audit_core.py` → `src/agent_audit_gate/_vendor_audit_core.py`  
3. Bump version in `pyproject.toml` and `src/agent_audit_gate/version.py`  
4. Update CHANGELOG  
5. Tag `vX.Y.Z` after push  
