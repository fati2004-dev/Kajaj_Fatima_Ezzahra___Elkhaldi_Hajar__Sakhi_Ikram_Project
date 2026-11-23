"""Modèles Pydantic : entrées de l'API, diagnostic, incident."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Action = Literal["none", "rerun_job", "open_pr", "rollback"]
Status = Literal["resolved_auto", "awaiting_approval", "no_action", "executed", "rejected"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AnalyzeRequest(BaseModel):
    log_text: str | None = Field(default=None, max_length=1_000_000)
    run_id: str | None = None
    environment: Literal["dev", "staging", "production"] = "staging"

    @model_validator(mode="after")
    def check_source(self):
        if self.log_text is None and not self.run_id:
            raise ValueError("fournir 'log_text' ou 'run_id'")
        if self.log_text is not None and not self.log_text.strip():
            raise ValueError("le log est vide")
        return self


class Diagnosis(BaseModel):
    category: str
    stage: str
    confidence: float
    explanation: str
    proposed_fix: str
    recommended_action: Action
    evidence: list[str] = []
    abstained: bool = False


class Decision(BaseModel):
    risk: Literal["none", "low", "medium", "high"]
    auto_allowed: bool
    requires_approval: bool
    reason: str


class Incident(BaseModel):
    id: str
    created_at: str = Field(default_factory=now_iso)
    run_id: str | None = None
    environment: str = "staging"
    diagnosis: Diagnosis
    decision: Decision
    status: Status
    llm_explanation: str | None = None
    trace: list[dict] = []
    action_result: dict | None = None
    retries: int = 0
