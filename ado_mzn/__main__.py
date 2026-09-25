# CLI entry for `python -m ado_mzn` (`check-minizinc`, `run`, `report`).

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ado_mzn.agent.generate import LlmError
from ado_mzn.eval.runner import RunError, run_experiment
from ado_mzn.report.render import render_report
from ado_mzn.toolchain.minizinc import (
    CheckMiniZincError,
    MiniZincNotFoundError,
    check_minizinc,
)


def _cmd_check_minizinc(_args: argparse.Namespace) -> int:
    try:
        info, result = check_minizinc()
    except MiniZincNotFoundError as exc:
        print(f"check-minizinc failed: {exc}", file=sys.stderr)
        return 1
    except CheckMiniZincError as exc:
        print(f"check-minizinc failed: {exc}", file=sys.stderr)
        return 1
    print("check-minizinc ok (no LLM)")
    print(f"  minizinc {info.version}  driver={info.driver_path}")
    print(f"  solver={info.solver_id}  outcome={result.outcome}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        run_config = run_experiment(args.seed, args.config)
    except RunError as exc:
        print(f"run failed: {exc}", file=sys.stderr)
        return 1
    except LlmError as exc:
        print(f"run failed: {exc}", file=sys.stderr)
        return 1

    run_dir = Path("runs") / run_config.run_id
    report_path = render_report(run_dir)
    print(f"run ok  run_id={run_config.run_id}")
    print(f"  cheap={run_config.llm_cheap.model_id}")
    print(f"  expensive={run_config.llm_expensive.model_id}")
    print(f"  seeds={', '.join(run_config.included_seed_ids)}")
    print(f"  output={run_dir}/")
    print(f"  report={report_path}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    if not (run_dir / "results.json").is_file():
        print(f"report failed: missing {run_dir / 'results.json'}", file=sys.stderr)
        return 1
    path = render_report(run_dir, out_path=args.out)
    print(f"report ok  {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ado_mzn",
        description="Cheap vs expensive LLM — NL → MiniZinc comparison",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "check-minizinc",
        help="Solve bundled smoke.mzn with no LLM (toolchain check)",
    )

    run_p = sub.add_parser(
        "run",
        help="Generate with cheap+expensive models and timed-solve",
    )
    run_p.add_argument("--seed", default="data/seed_problems.md")
    run_p.add_argument("--config", default="configs/default.yaml")

    report_p = sub.add_parser("report", help="Rebuild Markdown report from a run dir")
    report_p.add_argument("run_dir", help="e.g. runs/2026-09-15T120000Z")
    report_p.add_argument("--out", default=None, help="Optional output .md path")

    args = parser.parse_args(argv)
    if args.command == "check-minizinc":
        return _cmd_check_minizinc(args)
    if args.command == "run":
        return _cmd_run(args)
    if args.command == "report":
        return _cmd_report(args)
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
