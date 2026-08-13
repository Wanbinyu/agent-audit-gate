"""Load shared audit_core used by the Claude Code plugin.

Resolution order:
  1. USAGE_GATE_CORE env → directory containing audit_core.py
  2. Sibling repo G:/skill/cc-usage-gate/scripts (dev layout)
  3. Packaged fallback: agent_audit_gate/_vendor_audit_core.py
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType


def _load_from_path(path: Path) -> ModuleType | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("usage_gate_audit_core", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_cached: ModuleType | None = None


def load_audit_core() -> ModuleType:
    global _cached
    if _cached is not None:
        return _cached
    env = os.environ.get("USAGE_GATE_CORE", "").strip()
    candidates: list[Path] = []
    if env:
        p = Path(env)
        candidates.append(p if p.suffix == ".py" else p / "audit_core.py")

    # Dev monorepo layout: agent-audit-gate next to cc-usage-gate
    here = Path(__file__).resolve()
    skill_root = here.parents[3]  # .../skill/agent-audit-gate/src/agent_audit_gate
    # parents: 0=agent_audit_gate, 1=src, 2=agent-audit-gate, 3=skill
    candidates.append(skill_root / "cc-usage-gate" / "scripts" / "audit_core.py")
    candidates.append(here.parent / "_vendor_audit_core.py")

    for path in candidates:
        mod = _load_from_path(path)
        if mod is not None and hasattr(mod, "audit_events"):
            _cached = mod
            return mod

    raise ImportError(
        "Could not load shared audit_core. Set USAGE_GATE_CORE to the directory "
        "containing audit_core.py (from cc-usage-gate/scripts), or keep the "
        "vendored copy at agent_audit_gate/_vendor_audit_core.py."
    )
