# Run trajectory schema v1

Stable contract for `audit-gate check` and the library.

## Top-level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Must be `"1"` |
| `run_id` | string | yes | Stable id for this run |
| `claimed_status` | string | no | `completed` \| `partial` \| `blocked` \| `unknown` |
| `task` | object | no | Task metadata |
| `tools` | array | yes | Tool / command evidence (may be empty) |
| `files_changed` | string[] | no | Paths reported as written |
| `model_claims` | string[] | no | Free-text claims (never sufficient alone) |
| `notes` | string | no | Optional human notes |
| `source` | string | no | Provenance, e.g. `tool-events-jsonl` |

Print machine-readable schema: `audit-gate schema`.

## `task`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `summary` | string | `""` | Short description |
| `requires_verification` | bool \| null | auto | Default: `true` if writes exist |
| `risk` | string | `"standard"` | `low` \| `standard` \| `high` (reserved) |

## `tools[]`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Tool name |
| `ok` | bool | yes | Whether the tool call succeeded |
| `category` | string | yes | `read` \| `write` \| `command` \| `search` \| `other` |
| `path` | string | no | File path if applicable |
| `command` | string[] \| string | no | Command argv or string |
| `exit_code` | int | no | Process exit code |
| `verification` | bool | no | Marks verification evidence |
| `summary` | string | no | Short result summary |

## Tool-event JSONL (input to `from-events`)

Looser than full trajectory. Per line (or JSON array element):

| Field | Required | Notes |
|-------|----------|--------|
| `name` or `tool` | yes | Tool name |
| `ok` / `success` / `exit_code` | recommended | `exit_code` implies `ok`; missing outcome is **not** success |
| `category` | no | Inferred from name |
| `path` / `file` | no | |
| `command` / `cmd` / `argv` | no | string or string[] |
| `verification` | no | Auto for pytest/npm test/… |

## Compatibility

Claude Code / Cursor do not emit this schema natively. Use `from-events`, hand-authored trajectories, or a thin exporter in your harness. Core rules stay on schema v1.
