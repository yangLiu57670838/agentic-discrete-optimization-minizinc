# Execute a full run: dual LLM generate, same-solver timed solve, results.json.

from __future__ import annotations

from pathlib import Path
from typing import Union

from ado_mzn.agent.generate import LlmError, generate_mzn
from ado_mzn.schemas.results import (
    PairResult,
    RunResults,
    compare_runs,
    model_run_from_solve,
)
from ado_mzn.schemas.run_config import LlmConfig, RunConfig, build_run_config
from ado_mzn.schemas.seed import Seed, load_seeds
from ado_mzn.toolchain.minizinc import MiniZincNotFoundError, SolveResult, compile_and_solve


class RunError(RuntimeError):
    """Run failed before or during experiment execution."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _relative(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _generate_and_solve(
    *,
    role: str,
    llm: LlmConfig,
    seed_nl: str,
    out_path: Path,
    run_config: RunConfig,
) -> tuple[str, SolveResult]:
    model_mzn = generate_mzn(seed_nl, llm)
    _write_text(out_path, model_mzn)
    result = compile_and_solve(
        out_path,
        solver_id=run_config.minizinc.solver_id,
        time_limit_s=run_config.minizinc.time_limit_s,
    )
    return _relative(out_path, repo_root()), result


def _run_pair(
    seed: Seed,
    instance_id: str,
    run_dir: Path,
    run_config: RunConfig,
) -> PairResult:
    job_dir = run_dir / seed.id / instance_id
    seed_nl = seed.nl_for_prompt(instance_id)

    cheap_path = job_dir / "cheap.mzn"
    expensive_path = job_dir / "expensive.mzn"

    cheap_rel, cheap_result = _generate_and_solve(
        role="cheap",
        llm=run_config.llm_cheap,
        seed_nl=seed_nl,
        out_path=cheap_path,
        run_config=run_config,
    )
    expensive_rel, expensive_result = _generate_and_solve(
        role="expensive",
        llm=run_config.llm_expensive,
        seed_nl=seed_nl,
        out_path=expensive_path,
        run_config=run_config,
    )

    cheap = model_run_from_solve(
        role="cheap",
        model_id=run_config.llm_cheap.model_id,
        mzn_path=cheap_rel,
        result=cheap_result,
    )
    expensive = model_run_from_solve(
        role="expensive",
        model_id=run_config.llm_expensive.model_id,
        mzn_path=expensive_rel,
        result=expensive_result,
    )
    return PairResult(
        seed_id=seed.id,
        instance_id=instance_id,
        cheap=cheap,
        expensive=expensive,
        compare=compare_runs(cheap, expensive),
    )


def run_experiment(
    seed_file: Union[str, Path],
    config_path: Union[str, Path],
) -> RunConfig:
    """Generate with cheap + expensive LLMs; solve both with the same MiniZinc."""
    seed_path = Path(seed_file)
    config_file = Path(config_path)
    seeds = load_seeds(seed_path, complete_only=True)
    if not seeds:
        raise RunError(f"No complete seeds found in {seed_path}")

    try:
        run_config = build_run_config(
            config_path=config_file,
            seed_file=seed_path,
            included_seed_ids=[seed.id for seed in seeds],
        )
    except MiniZincNotFoundError as exc:
        raise RunError(str(exc)) from exc

    root = repo_root()
    run_dir = root / "runs" / run_config.run_id
    run_config_path = run_config.write_json(run_dir / "run_config.json")

    results = RunResults(run_config_path=_relative(run_config_path, root))

    for seed in seeds:
        instance_ids = seed.instance_ids or ["i01"]
        for instance_id in instance_ids:
            results.pairs.append(
                _run_pair(seed, instance_id, run_dir, run_config)
            )

    results.write_json(run_dir / "results.json")
    return run_config
