from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .models import RunTrajectory


def read_text_source(source: str | Path) -> str:
    """Read file path or stdin when source is '-'."""
    text_path = str(source)
    if text_path == "-":
        return sys.stdin.read()
    path = Path(text_path)
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")
    return path.read_text(encoding="utf-8")


def load_json_source(source: str | Path) -> Any:
    raw = read_text_source(source)
    if not raw.strip():
        raise ValueError("empty input")
    return json.loads(raw)


def load_run(source: str | Path) -> RunTrajectory:
    data = load_json_source(source)
    if not isinstance(data, dict):
        raise ValueError("trajectory root must be a JSON object")
    return RunTrajectory.model_validate(data)


def load_run_from_data(data: dict[str, Any]) -> RunTrajectory:
    return RunTrajectory.model_validate(data)
