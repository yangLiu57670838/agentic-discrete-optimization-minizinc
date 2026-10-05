# Schema for per-seed cheap vs expensive result records in results.json.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

OUTCOME_LLM_ERROR = "LLM_ERROR"


@dataclass
class ModelAttempt:
    """One model's single .mzn for one seed, plus its one compile/solve."""

    label: str
    requested_model_id: str
    resolved_model_id: Optional[str] = None
    mzn_path: Optional[str] = None
    mzn_lines: Optional[int] = None
    llm: dict[str, Any] = field(default_factory=dict)
    llm_error: Optional[str] = None
    solve: Optional[dict[str, Any]] = None

    @property
    def outcome(self) -> str:
        if self.solve is None:
            return OUTCOME_LLM_ERROR
        return self.solve["outcome"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "requested_model_id": self.requested_model_id,
            "resolved_model_id": self.resolved_model_id,
            "outcome": self.outcome,
            "mzn_path": self.mzn_path,
            "mzn_lines": self.mzn_lines,
            "llm": self.llm,
            "llm_error": self.llm_error,
            "solve": self.solve,
        }


@dataclass
class SeedResult:
    seed_id: str
    title: str
    objective_sense: Optional[str]
    constraint_ids: list[str]
    attempts: dict[str, ModelAttempt]
    comparison: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_id": self.seed_id,
            "title": self.title,
            "objective_sense": self.objective_sense,
            "constraint_ids": self.constraint_ids,
            "attempts": {label: a.to_dict() for label, a in self.attempts.items()},
            "comparison": self.comparison,
        }
