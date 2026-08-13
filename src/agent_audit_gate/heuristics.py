from __future__ import annotations

from typing import Any

from .audit_core_bridge import load_audit_core
from .models import ToolCategory


def command_to_text(command: list[str] | str | None) -> str:
    if command is None:
        return ""
    if isinstance(command, list):
        return " ".join(str(x) for x in command)
    return str(command)


def looks_like_verification(command: list[str] | str | None, name: str = "") -> bool:
    """Same detector as cc-usage-gate PostToolUse (is_verification_command)."""
    text = command_to_text(command).strip()
    if not text and name:
        text = name
    core = load_audit_core()
    return bool(core.is_verification_command(text))


def infer_category(name: str, raw: dict[str, Any] | None = None) -> ToolCategory:
    """Same categories as cc-usage-gate tool_category."""
    raw = raw or {}
    explicit = raw.get("category")
    if explicit in ("read", "write", "command", "search", "other"):
        return explicit  # type: ignore[return-value]

    tool_input: dict[str, Any] = {}
    if raw.get("command") is not None:
        tool_input["command"] = raw["command"]
    elif raw.get("cmd") is not None:
        tool_input["cmd"] = raw["cmd"]
    elif raw.get("argv") is not None:
        tool_input["command"] = raw["argv"]
    path = raw.get("path") or raw.get("file") or raw.get("file_path")
    if path is not None:
        tool_input["file_path"] = path
    for key in ("content", "new_string", "old_string"):
        if key in raw:
            tool_input[key] = raw[key]

    core = load_audit_core()
    category = core.tool_category(name or "", tool_input)
    if category in ("read", "write", "command", "search", "other"):
        return category  # type: ignore[return-value]
    return "other"


def coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "ok", "success", "passed"}
    return default


def coerce_exit_code(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
