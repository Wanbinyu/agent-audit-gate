# Security

## Threat model

`agent-audit-gate` is a **local, offline** CLI/library. It:

- reads JSON you provide,
- applies deterministic rules,
- writes only paths you pass to `--output` / `init` / `--write-trajectory`.

It does **not**:

- open network connections,
- execute shell commands from the trajectory,
- upload telemetry.

`USAGE_GATE_CORE` (if set) loads that `audit_core.py` by path so local plugin and CLI stay in sync. Only point it at a file you trust.

## What you should not put in trajectories

- API keys, tokens, cookies  
- private customer data you cannot share  
- full `.env` contents  

Prefer redacted command lines (`python -m pytest` without secrets in argv).

## Supply chain

- Install from a git URL or path you trust.
- Pin a tag/commit in production CI when possible.
- Review releases before upgrading.

## Reporting issues

If you find a security issue (e.g. unexpected file write outside requested paths), open a private security advisory on the GitHub repository or contact the maintainer. Do not file a public issue with exploit details.
