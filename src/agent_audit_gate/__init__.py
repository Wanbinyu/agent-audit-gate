"""Sidecar completion audit: evidence decides completed vs blocked."""

from .adapters import adapt_events_file, events_to_trajectory
from .audit import audit_run
from .io_util import load_run
from .models import AuditReport, RunTrajectory, ToolEvent
from .session_import import resolve_usage_gate_events
from .version import __version__

__all__ = [
    "__version__",
    "AuditReport",
    "RunTrajectory",
    "ToolEvent",
    "adapt_events_file",
    "audit_run",
    "events_to_trajectory",
    "load_run",
    "resolve_usage_gate_events",
]
