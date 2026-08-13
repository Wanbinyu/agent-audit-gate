from __future__ import annotations

from pathlib import Path

import pytest


def test_vendor_matches_sibling_when_present() -> None:
    here = Path(__file__).resolve()
    vendor = here.parents[1] / "src" / "agent_audit_gate" / "_vendor_audit_core.py"
    sibling = here.parents[2] / "cc-usage-gate" / "scripts" / "audit_core.py"
    if not sibling.is_file():
        pytest.skip("sibling cc-usage-gate not present")
    assert vendor.read_text(encoding="utf-8") == sibling.read_text(encoding="utf-8")
