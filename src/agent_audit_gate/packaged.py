from __future__ import annotations

from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path
from typing import Iterator


def packaged_example_names() -> tuple[str, ...]:
    return (
        "run_completed.json",
        "run_readonly_ok.json",
        "run_partial.json",
        "run_blocked_no_test.json",
        "run_blocked_failed_test.json",
    )


@contextmanager
def packaged_example(name: str) -> Iterator[Path]:
    ref = files("agent_audit_gate").joinpath("data").joinpath(name)
    with as_file(ref) as path:
        yield Path(path)
