# Schema for per seed×instance cheap vs expensive result records.

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from ado_mzn.toolchain.minizinc import SolveResult


@dataclass
class ModelRunResult:
    role: str
    model_id: str
    mzn_path: str
    outcome: str
    compile_success: bool
    solver_success: bool
    objective: Optional[float]
    solve_time_s: Optional[float]
    diagnostics: str = ""
    statistics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "model_id": self.model_id,
            "mzn_path": self.mzn_path,
            "outcome": self.outcome,
            "compile_success": self.compile_success,
            "solver_success": self.solver_success,
            "objective": self.objective,
            "solve_time_s": self.solve_time_s,
            "diagnostics": self.diagnostics,
            "statistics": dict(self.statistics),
        }


@dataclass
class CompareResult:
    both_compile: bool
    both_solver_success: bool
    faster: Optional[str]
    solve_time_delta_s: Optional[float]
    objective_equal: Optional[bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "both_compile": self.both_compile,
            "both_solver_success": self.both_solver_success,
            "faster": self.faster,
            "solve_time_delta_s": self.solve_time_delta_s,
            "objective_equal": self.objective_equal,
        }


@dataclass
class PairResult:
    seed_id: str
    instance_id: str
    cheap: ModelRunResult
    expensive: ModelRunResult
    compare: CompareResult
    human_notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_id": self.seed_id,
            "instance_id": self.instance_id,
            "cheap": self.cheap.to_dict(),
            "expensive": self.expensive.to_dict(),
            "compare": self.compare.to_dict(),
            "human_notes": self.human_notes,
        }


@dataclass
class RunResults:
    run_config_path: str
    pairs: list[PairResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_config_path": self.run_config_path,
            "pairs": [pair.to_dict() for pair in self.pairs],
        }

    def write_json(self, path: Union[str, Path]) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        return out


def model_run_from_solve(
    *,
    role: str,
    model_id: str,
    mzn_path: str,
    result: SolveResult,
) -> ModelRunResult:
    return ModelRunResult(
        role=role,
        model_id=model_id,
        mzn_path=mzn_path,
        outcome=result.outcome,
        compile_success=result.compile_success,
        solver_success=result.solver_success,
        objective=result.objective,
        solve_time_s=result.solve_time_s,
        diagnostics=result.diagnostics,
        statistics=dict(result.statistics),
    )


def compare_runs(cheap: ModelRunResult, expensive: ModelRunResult) -> CompareResult:
    both_compile = cheap.compile_success and expensive.compile_success
    both_ok = cheap.solver_success and expensive.solver_success

    faster: Optional[str] = None
    delta: Optional[float] = None
    if (
        both_ok
        and cheap.solve_time_s is not None
        and expensive.solve_time_s is not None
    ):
        delta = abs(cheap.solve_time_s - expensive.solve_time_s)
        if abs(cheap.solve_time_s - expensive.solve_time_s) < 1e-9:
            faster = "tie"
        elif cheap.solve_time_s < expensive.solve_time_s:
            faster = "cheap"
        else:
            faster = "expensive"

    objective_equal: Optional[bool] = None
    if cheap.objective is not None and expensive.objective is not None:
        objective_equal = abs(cheap.objective - expensive.objective) < 1e-9

    return CompareResult(
        both_compile=both_compile,
        both_solver_success=both_ok,
        faster=faster,
        solve_time_delta_s=delta,
        objective_equal=objective_equal,
    )
