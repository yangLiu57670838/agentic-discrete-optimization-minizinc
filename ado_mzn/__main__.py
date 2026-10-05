# CLI entry for `python -m ado_mzn` (`check-minizinc`, `run`, `report`).

from __future__ import annotations

import argparse
import sys

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
    from ado_mzn.agent.generate import LLMError
    from ado_mzn.eval.runner import run
    from ado_mzn.schemas.run_config import ConfigError
    from ado_mzn.schemas.seed import SeedError

    try:
        run_dir = run(args.seed, args.config)
    except (MiniZincNotFoundError, SeedError, ConfigError, LLMError) as exc:
        print(f"run failed: {exc}", file=sys.stderr)
        return 1
    print(run_dir)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from ado_mzn.report.render import render_report

    print(render_report(args.run_dir, args.reports_dir))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ado_mzn",
        description="NL → MiniZinc: cheap vs expensive LLM comparison harness",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "check-minizinc",
        help="Solve bundled smoke.mzn with no LLM (toolchain check)",
    )

    run_p = sub.add_parser("run", help="Cheap + expensive model each generate one .mzn per seed; solve and compare")
    run_p.add_argument("--seed", default="data/seed_problems.md")
    run_p.add_argument("--config", default="configs/default.yaml")

    report_p = sub.add_parser("report", help="Re-render reports/<run_id>.md after filling review.yaml")
    report_p.add_argument("run_dir")
    report_p.add_argument("--reports-dir", default="reports")

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
