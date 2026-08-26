# CLI entry for `python -m ado_mzn` (`check-minizinc` and `run`).

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


def _cmd_run(_args: argparse.Namespace) -> int:
    print(
        "run is not implemented yet. After check-minizinc passes, "
        "add NL seeds and the generate/repair loop.",
        file=sys.stderr,
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ado_mzn",
        description="NL → MiniZinc agent harness",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "check-minizinc",
        help="Solve bundled smoke.mzn with no LLM (toolchain check)",
    )

    run_p = sub.add_parser("run", help="Generate and score seeds (not yet implemented)")
    run_p.add_argument("--seed", default="data/seed_problems.md")
    run_p.add_argument("--config", default="configs/default.yaml")

    args = parser.parse_args(argv)
    if args.command == "check-minizinc":
        return _cmd_check_minizinc(args)
    if args.command == "run":
        return _cmd_run(args)
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
