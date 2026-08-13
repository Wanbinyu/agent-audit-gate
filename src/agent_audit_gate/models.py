from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ClaimedStatus = Literal["completed", "partial", "blocked", "unknown"]
ReportStatus = Literal["completed", "partial", "blocked"]
ToolCategory = Literal["read", "write", "command", "search", "other"]
RiskLevel = Literal["low", "standard", "high"]


class TaskMeta(BaseModel):
    summary: str = ""
    requires_verification: bool | None = None
    risk: RiskLevel = "standard"


class ToolEvent(BaseModel):
    name: str
    ok: bool
    category: ToolCategory
    path: str | None = None
    command: list[str] | str | None = None
    exit_code: int | None = None
    verification: bool = False
    summary: str | None = None

    @field_validator("command", mode="before")
    @classmethod
    def _normalize_command(cls, value: Any) -> list[str] | str | None:
        return value


class RunTrajectory(BaseModel):
    schema_version: str
    run_id: str
    claimed_status: ClaimedStatus = "unknown"
    task: TaskMeta = Field(default_factory=TaskMeta)
    tools: list[ToolEvent] = Field(default_factory=list)
    files_changed: list[str] = Field(default_factory=list)
    model_claims: list[str] = Field(default_factory=list)
    notes: str | None = None
    source: str | None = None

    @field_validator("schema_version")
    @classmethod
    def _version_must_be_v1(cls, value: str) -> str:
        if value != "1":
            raise ValueError(f"unsupported schema_version: {value!r} (expected '1')")
        return value

    def has_write(self) -> bool:
        if self.files_changed:
            return True
        return any(t.category == "write" and t.ok for t in self.tools)

    def verification_required(self) -> bool:
        if self.task.requires_verification is not None:
            return self.task.requires_verification
        return self.has_write()


class AuditFinding(BaseModel):
    code: str
    severity: Literal["info", "warn", "error"]
    message: str


class AuditReport(BaseModel):
    schema_version: str = "1"
    gate_version: str = ""
    run_id: str
    status: ReportStatus
    claimed_status: ClaimedStatus
    missing_evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    findings: list[AuditFinding] = Field(default_factory=list)
    summary: str = ""
    stats: dict[str, int] = Field(default_factory=dict)
    source: str | None = None

    def exit_code(self) -> int:
        if self.status == "completed":
            return 0
        if self.status == "partial":
            return 2
        return 3
