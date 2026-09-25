# Wrap MiniZinc Python: probe, check-minizinc smoke fixture, solve one .mzn, classify outcomes.

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import timedelta
from importlib.metadata import PackageNotFoundError, version as pkg_version
from pathlib import Path
from typing import Any, Optional, Union

DEFAULT_SOLVER_ID = "gecode"
DEFAULT_TIME_LIMIT_S = 10

OUTCOME_COMPILE_ERROR = "COMPILE_ERROR"
OUTCOME_SOLVER_ERROR = "SOLVER_ERROR"
OUTCOME_TIMEOUT_UNKNOWN = "TIMEOUT / UNKNOWN"
OUTCOME_SATISFIED = "SATISFIED"
OUTCOME_OPTIMAL = "OPTIMAL_SOLUTION"
OUTCOME_UNSAT = "UNSATISFIABLE"

VALID_TERMINATION = frozenset(
    {OUTCOME_SATISFIED, OUTCOME_OPTIMAL, OUTCOME_UNSAT}
)
REPAIRABLE = frozenset({OUTCOME_COMPILE_ERROR, OUTCOME_SOLVER_ERROR})


class MiniZincNotFoundError(RuntimeError):
    """Raised when the MiniZinc binary cannot be found (fail fast)."""


@dataclass(frozen=True)
class ProbeInfo:
    """Resolved MiniZinc install for run_config.json."""

    version: Optional[str]
    driver_path: Optional[str]
    python_package_version: Optional[str]
    solver_id: str
    time_limit_s: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "driver_path": self.driver_path,
            "python_package_version": self.python_package_version,
            "solver_id": self.solver_id,
            "time_limit_s": self.time_limit_s,
        }


@dataclass
class SolveResult:
    """One compile/solve of a single .mzn (no .dzn)."""

    outcome: str
    diagnostics: str = ""
    objective: Optional[float] = None
    solution: Optional[dict[str, Any]] = None
    raw_status: Optional[str] = None
    statistics: dict[str, Any] = field(default_factory=dict)
    solve_time_s: Optional[float] = None

    @property
    def compile_success(self) -> bool:
        return self.outcome != OUTCOME_COMPILE_ERROR

    @property
    def solver_success(self) -> bool:
        return self.outcome in VALID_TERMINATION

    @property
    def should_repair(self) -> bool:
        return self.outcome in REPAIRABLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "compile_success": self.compile_success,
            "solver_success": self.solver_success,
            "should_repair": self.should_repair,
            "diagnostics": self.diagnostics,
            "objective": self.objective,
            "raw_status": self.raw_status,
            "solve_time_s": self.solve_time_s,
        }


def _python_package_version() -> Optional[str]:
    try:
        return pkg_version("minizinc")
    except PackageNotFoundError:
        return None


def _search_paths() -> Optional[list[str]]:
    extra: list[str] = []
    env = os.environ.get("MINIZINC_DIR")
    if env:
        extra.append(env)
        extra.append(str(Path(env) / "bin"))
    return extra or None

# identify local minizinc executable and solver is ready to use
def probe(
    solver_id: str = DEFAULT_SOLVER_ID,
    time_limit_s: int = DEFAULT_TIME_LIMIT_S,
) -> ProbeInfo:
    """Locate MiniZinc, record version/path/solver. Raises if missing."""
    try:
        from minizinc import Solver
        from minizinc.driver import Driver
    except ImportError as exc:
        raise MiniZincNotFoundError(
            "Python package 'minizinc' is not installed. pip install minizinc"
        ) from exc

    driver = Driver.find(path=_search_paths())
    if driver is None:
        raise MiniZincNotFoundError(
            "MiniZinc binary not found. Install MiniZinc and put it on PATH, "
            "or set MINIZINC_DIR. The pip package does not include the compiler."
        )
    if hasattr(driver, "make_default"):
        driver.make_default()

    version: Optional[str] = None
    parsed = getattr(driver, "parsed_version", None)
    if parsed:
        version = ".".join(str(part) for part in parsed)
    elif hasattr(driver, "version"):
        version = str(driver.version)

    executable = getattr(driver, "executable", None)
    driver_path = str(executable) if executable is not None else None

    try:
        Solver.lookup(solver_id)
    except Exception as exc:
        raise MiniZincNotFoundError(
            f"MiniZinc solver '{solver_id}' not found. {exc}"
        ) from exc

    return ProbeInfo(
        version=version,
        driver_path=driver_path,
        python_package_version=_python_package_version(),
        solver_id=solver_id,
        time_limit_s=time_limit_s,
    )


def _format_exception(exc: BaseException) -> str:
    message = getattr(exc, "message", None) or str(exc)
    location = getattr(exc, "location", None)
    if location is None:
        return message
    file = getattr(location, "file", None)
    lines = getattr(location, "lines", None)
    where = f"{file}:{lines}" if file is not None else ""
    return f"{where} {message}".strip() if where else message


def _classify_minizinc_error(exc: BaseException) -> str:
    """Map MiniZinc Python exceptions to COMPILE_ERROR vs SOLVER_ERROR."""
    try:
        from minizinc.error import (
            AssertionError as MznAssertionError,
            CyclicIncludeError,
            EvaluationError,
            IncludeError,
            SyntaxError as MznSyntaxError,
            TypeError as MznTypeError,
        )
    except ImportError:
        return OUTCOME_COMPILE_ERROR

    compile_types = (
        MznSyntaxError,
        MznTypeError,
        IncludeError,
        CyclicIncludeError,
        EvaluationError,
        MznAssertionError,
    )
    if isinstance(exc, compile_types):
        return OUTCOME_COMPILE_ERROR

    text = _format_exception(exc).lower()
    solver_markers = (
        "failed to run solver",
        "solver terminated",
        "unknown solver",
        "could not load solver",
        "solver error",
    )
    if any(marker in text for marker in solver_markers):
        return OUTCOME_SOLVER_ERROR
    return OUTCOME_COMPILE_ERROR


def _outcome_from_status(status: Any) -> str:
    name = getattr(status, "name", str(status))
    mapping = {
        "SATISFIED": OUTCOME_SATISFIED,
        "OPTIMAL_SOLUTION": OUTCOME_OPTIMAL,
        "UNSATISFIABLE": OUTCOME_UNSAT,
        "ALL_SOLUTIONS": OUTCOME_SATISFIED,
        "UNKNOWN": OUTCOME_TIMEOUT_UNKNOWN,
        "ERROR": OUTCOME_SOLVER_ERROR,
        "UNBOUNDED": OUTCOME_TIMEOUT_UNKNOWN,
    }
    return mapping.get(name, OUTCOME_TIMEOUT_UNKNOWN)


def _extract_objective(result: Any) -> Optional[float]:
    objective = getattr(result, "objective", None)
    if objective is None:
        return None
    try:
        return float(objective)
    except (TypeError, ValueError):
        return None


def _extract_solution(result: Any) -> Optional[dict[str, Any]]:
    solution = getattr(result, "solution", None)
    if solution is None:
        return None
    if isinstance(solution, dict):
        return dict(solution)
    as_dict = getattr(solution, "__dict__", None)
    if as_dict:
        return {k: v for k, v in as_dict.items() if not k.startswith("_")}
    return None


def smoke_model_path() -> Path:
    """Bundled fixture for check-minizinc. Not a seed; author does not write this."""
    return Path(__file__).resolve().parent / "fixtures" / "smoke.mzn"


class CheckMiniZincError(RuntimeError):
    """Smoke model did not reach valid solver termination."""


def check_minizinc(
    solver_id: str = DEFAULT_SOLVER_ID,
    time_limit_s: int = DEFAULT_TIME_LIMIT_S,
) -> tuple[ProbeInfo, SolveResult]:
    """No LLM. Probe MiniZinc, then solve the bundled smoke .mzn.

    Passes iff the smoke model reaches SATISFIED / OPTIMAL_SOLUTION / UNSATISFIABLE.
    """
    info = probe(solver_id=solver_id, time_limit_s=time_limit_s)
    path = smoke_model_path()
    if not path.is_file():
        raise CheckMiniZincError(f"Smoke fixture missing: {path}")
    result = compile_and_solve(
        path, solver_id=solver_id, time_limit_s=time_limit_s
    )
    if not result.solver_success:
        raise CheckMiniZincError(
            f"Smoke model did not reach valid termination "
            f"(outcome={result.outcome}). {result.diagnostics}".strip()
        )
    return info, result


def compile_and_solve(
    mzn_path: Union[str, Path],
    solver_id: str = DEFAULT_SOLVER_ID,
    time_limit_s: int = DEFAULT_TIME_LIMIT_S,
) -> SolveResult:
    """Compile and solve one executable .mzn. MiniZinc is the oracle."""
    path = Path(mzn_path)
    if not path.is_file():
        return SolveResult(
            outcome=OUTCOME_COMPILE_ERROR,
            diagnostics=f"MiniZinc model file not found: {path}",
        )

    try:
        from minizinc import Instance, Model, Solver
        from minizinc.error import MiniZincError
    except ImportError as exc:
        raise MiniZincNotFoundError(
            "Python package 'minizinc' is not installed. pip install minizinc"
        ) from exc

    try:
        solver = Solver.lookup(solver_id)
    except Exception as exc:
        raise MiniZincNotFoundError(
            f"MiniZinc solver '{solver_id}' not found. {exc}"
        ) from exc

    started = time.monotonic()
    try:
        model = Model(path)
        instance = Instance(solver, model)
        result = instance.solve(timeout=timedelta(seconds=time_limit_s))
    except MiniZincError as exc:
        elapsed = time.monotonic() - started
        outcome = _classify_minizinc_error(exc)
        return SolveResult(
            outcome=outcome,
            diagnostics=_format_exception(exc),
            raw_status=type(exc).__name__,
            solve_time_s=elapsed,
        )
    except Exception as exc:
        elapsed = time.monotonic() - started
        # Unexpected failure after flattening is treated as solver-side.
        text = _format_exception(exc)
        lower = text.lower()
        if "timeout" in lower or "timed out" in lower:
            return SolveResult(
                outcome=OUTCOME_TIMEOUT_UNKNOWN,
                diagnostics=text,
                raw_status=type(exc).__name__,
                solve_time_s=elapsed,
            )
        return SolveResult(
            outcome=OUTCOME_SOLVER_ERROR,
            diagnostics=text,
            raw_status=type(exc).__name__,
            solve_time_s=elapsed,
        )

    elapsed = time.monotonic() - started
    status = getattr(result, "status", None)
    outcome = _outcome_from_status(status)
    stats = getattr(result, "statistics", None) or {}
    return SolveResult(
        outcome=outcome,
        diagnostics="" if outcome in VALID_TERMINATION else str(status),
        objective=_extract_objective(result),
        solution=_extract_solution(result),
        raw_status=getattr(status, "name", str(status)),
        statistics=dict(stats) if isinstance(stats, dict) else {},
        solve_time_s=elapsed,
    )
