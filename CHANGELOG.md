# Changelog

## 0.3.1 — 2026-08-13

- `requires_verification=true` on a read-only run now requires a green test
  (claimed completed → blocked; otherwise partial).
- CI smokes `run_partial` and `from-session`.
- Example GitHub Action installs from `Wanbinyu/agent-audit-gate`.

## 0.3.0 — 2026-08-13

- **Shared tagging** with `cc-usage-gate`: `from-events` uses the same
  `is_verification_command` / `tool_category` as the plugin. Generic
  `build` / `lint` / summary-text matches are no longer verification.
- Missing `ok` / `exit_code` is no longer treated as success.
- **`partial` is real:** writes without a green test are `partial` (exit 2)
  when `claimed_status` is not `completed`. Claiming completed stays `blocked`.
- **`audit-gate from-session`** reads `.claude/usage-gate/*.events.jsonl`
  (latest or named session) — CI/replay of the plugin log.
- Example: `examples/run_partial.json`.

## 0.2.1 — 2026-08-13

- Audit rules now share `audit_core` with Claude Code plugin `cc-usage-gate` (vendored + path bridge).
- Same completed/blocked semantics as plugin Stop hook.

## 0.2.0 — 2026-08-12

Shippable MVP for third-party use.

### Added

- `audit-gate from-events` — JSONL / JSON array tool logs → normalize → audit
- Auto-detect common verification commands (`pytest`, `npm test`, …)
- Infer tool `category` and `ok` from loose event fields
- `audit-gate init` starter trajectory
- `audit-gate validate` schema-only check
- `audit-gate rules` / `audit-gate schema`
- stdin support (`check -`, `from-events -`)
- `--quiet`, `--output`, `--write-trajectory`, `--pretty`
- Report field `gate_version`, optional trajectory `source`
- Docs: QUICKSTART (EN/中文), SECURITY, CI example workflow
- Tests for adapters and CLI (Typer CliRunner)

### Changed

- Version **0.2.0**; packaging metadata for public install
- Clearer error messages on missing verification

## 0.1.0 — 2026-08-12

- Initial trajectory schema v1 and `audit-gate check`
- Example trajectories and core unit tests
