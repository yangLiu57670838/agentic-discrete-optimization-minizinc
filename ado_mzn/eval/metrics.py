# Compare cheap vs expensive on one seed: outcome, objective, solve time (MiniZinc is the oracle).

from __future__ import annotations

from typing import Any, Optional

from ado_mzn.schemas.results import ModelAttempt
from ado_mzn.toolchain.minizinc import (
    OUTCOME_OPTIMAL,
    OUTCOME_SATISFIED,
    OUTCOME_UNSAT,
    VALID_TERMINATION,
)

TIME_TIE_S = 0.1


def finished_search(outcome: str, is_optimisation: bool) -> bool:
    """Solver proved its answer: optimum (or UNSAT) for optimisation, any solution for SAT problems."""
    if is_optimisation:
        return outcome in {OUTCOME_OPTIMAL, OUTCOME_UNSAT}
    return outcome in {OUTCOME_SATISFIED, OUTCOME_UNSAT}


def _better(a: Optional[float], b: Optional[float], lower_is_better: bool) -> str:
    if a is None or b is None:
        return "NA"
    if a == b:
        return "tie"
    a_wins = a < b if lower_is_better else a > b
    return "cheap" if a_wins else "expensive"


def compare(
    cheap: ModelAttempt,
    expensive: ModelAttempt,
    *,
    is_optimisation: bool,
    objective_sense: Optional[str],
) -> dict[str, Any]:
    """Solver-side comparison only. Objective and time are meaningful only if both
    models are faithful to the NL — that is the human review, not this function."""
    c_out, e_out = cheap.outcome, expensive.outcome
    c_solve, e_solve = cheap.solve or {}, expensive.solve or {}

    objective_better = "NA"
    if is_optimisation and objective_sense and c_out in VALID_TERMINATION and e_out in VALID_TERMINATION:
        objective_better = _better(
            c_solve.get("objective"),
            e_solve.get("objective"),
            lower_is_better=objective_sense == "minimize",
        )

    faster = "NA"
    time_ratio = None
    c_done = finished_search(c_out, is_optimisation)
    e_done = finished_search(e_out, is_optimisation)
    if c_done and e_done:
        c_t, e_t = c_solve.get("solve_time_s"), e_solve.get("solve_time_s")
        if c_t is not None and e_t is not None:
            faster = "tie" if abs(c_t - e_t) < TIME_TIE_S else _better(c_t, e_t, lower_is_better=True)
            time_ratio = round(c_t / e_t, 3) if e_t > 0 else None
    elif c_done != e_done:
        faster = "cheap" if c_done else "expensive"

    return {
        "outcome": {"cheap": c_out, "expensive": e_out},
        "solver_success": {"cheap": c_out in VALID_TERMINATION, "expensive": e_out in VALID_TERMINATION},
        "finished_search": {"cheap": c_done, "expensive": e_done},
        "objective_better": objective_better,
        "faster_to_finish": faster,
        "solve_time_ratio_cheap_over_expensive": time_ratio,
    }
