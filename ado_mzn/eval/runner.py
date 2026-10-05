# Execute a full run: run_config.json, cheap + expensive generate once per seed, same solve, results.json.

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Union

from ado_mzn.agent import prompts
from ado_mzn.agent.generate import LLMError, generate_mzn, make_client
from ado_mzn.eval.metrics import compare
from ado_mzn.report.render import render_report
from ado_mzn.schemas.results import ModelAttempt, SeedResult
from ado_mzn.schemas.run_config import (
    build_run_config,
    load_settings,
    new_run_id,
    utc_now,
    write_json,
)
from ado_mzn.schemas.seed import Seed, parse_seeds
from ado_mzn.toolchain.minizinc import compile_and_solve, probe


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _review_template(seeds: list[Seed], labels: list[str]) -> str:
    lines = [
        "# Human review. Read each seed's NL, then each generated .mzn, and fill in below.",
        "# constraints_missing: list of ids the model lacks or gets wrong, e.g. [C3, C7]; [] if none.",
        "# objective_correct: true / false / NA (right sense, right quantity, linked to decisions).",
        "# review_score: 1 unrelated .. 5 reasonable first draft.",
        "# Then re-render: python -m ado_mzn report runs/<run_id>",
        "",
    ]
    for seed in seeds:
        ids = ", ".join(seed.constraint_ids) or "none listed"
        lines.append(f"{seed.id}:  # constraints: {ids}")
        for label in labels:
            lines += [
                f"  {label}:",
                "    constraints_missing: null",
                "    objective_correct: null",
                "    review_score: null",
                '    notes: ""',
            ]
    return "\n".join(lines) + "\n"


def run(
    seed_path: Union[str, Path],
    config_path: Union[str, Path],
    *,
    client: Any = None,
) -> Path:
    """Generate once per model per seed, solve every .mzn with the same solver and limit."""
    settings = load_settings(config_path)
    seeds = parse_seeds(seed_path)
    info = probe(solver_id=settings.solver_id, time_limit_s=settings.time_limit_s)

    started_at = utc_now()
    run_id = new_run_id(started_at)
    run_dir = settings.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    run_config = build_run_config(
        settings,
        run_id=run_id,
        started_at=started_at,
        seed_file=str(seed_path),
        seed_ids=[s.id for s in seeds],
        minizinc_info=info.to_dict(),
        prompt_sha256=prompts.template_sha256(),
    )
    run_config_path = write_json(run_dir / "run_config.json", run_config)
    _log(f"run {run_id}: {len(seeds)} seed(s), models " + ", ".join(
        f"{m.label}={m.model_id}" for m in settings.models
    ))

    client = client or make_client(settings.llm_timeout_s)
    seed_results: list[SeedResult] = []

    for seed in seeds:
        seed_dir = run_dir / seed.id
        attempts: dict[str, ModelAttempt] = {}

        for spec in settings.models:
            attempt = ModelAttempt(label=spec.label, requested_model_id=spec.model_id)
            _log(f"  {seed.id} {spec.label}: generating with {spec.model_id}")
            try:
                mzn_path, response = generate_mzn(
                    seed,
                    seed_dir,
                    spec.label,
                    model_id=spec.model_id,
                    temperature=settings.temperature,
                    max_tokens=settings.max_tokens,
                    client=client,
                )
            except LLMError as exc:
                attempt.llm_error = str(exc)
                _log(f"  {seed.id} {spec.label}: {exc}")
            else:
                attempt.resolved_model_id = response.model_id
                attempt.mzn_path = str(mzn_path)
                attempt.mzn_lines = len(response.mzn.splitlines())
                attempt.llm = response.to_dict()
                resolved = run_config["models"][spec.label]
                if resolved["resolved_model_id"] is None:
                    resolved["resolved_model_id"] = response.model_id
            attempts[spec.label] = attempt

        for label, attempt in attempts.items():
            if attempt.mzn_path is None:
                continue
            result = compile_and_solve(
                attempt.mzn_path,
                solver_id=settings.solver_id,
                time_limit_s=settings.time_limit_s,
            )
            attempt.solve = {**result.to_dict(), "solution": result.solution}
            _log(f"  {seed.id} {label}: {result.outcome} objective={result.objective} "
                 f"time={result.solve_time_s:.2f}s")

        seed_results.append(
            SeedResult(
                seed_id=seed.id,
                title=seed.title,
                objective_sense=seed.objective_sense,
                constraint_ids=seed.constraint_ids,
                attempts=attempts,
                comparison=compare(
                    attempts["cheap"],
                    attempts["expensive"],
                    is_optimisation=seed.is_optimisation,
                    objective_sense=seed.objective_sense,
                ),
            )
        )

    run_config["finished_at"] = utc_now().isoformat().replace("+00:00", "Z")
    write_json(run_config_path, run_config)
    write_json(
        run_dir / "results.json",
        {
            "run_id": run_id,
            "run_config_path": str(run_config_path),
            "seeds": [r.to_dict() for r in seed_results],
        },
    )
    review_path = run_dir / "review.yaml"
    if not review_path.exists():
        review_path.write_text(
            _review_template(seeds, [m.label for m in settings.models]), encoding="utf-8"
        )

    report_path = render_report(run_dir, settings.reports_dir)
    _log(f"wrote {run_dir}/results.json, {review_path}, {report_path}")
    return run_dir
