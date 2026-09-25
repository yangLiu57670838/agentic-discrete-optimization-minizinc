# Render a Markdown comparison report from run_config + results.json.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def render_report(
    run_dir: Union[str, Path],
    *,
    out_path: Union[str, Path, None] = None,
) -> Path:
    """Write reports/<run_id>.md from an existing run directory."""
    run_dir = Path(run_dir)
    run_config = _load_json(run_dir / "run_config.json")
    results = _load_json(run_dir / "results.json")
    run_id = run_config.get("run_id", run_dir.name)

    cheap = run_config.get("llm_cheap") or {}
    expensive = run_config.get("llm_expensive") or {}
    mzn = run_config.get("minizinc") or {}

    lines: list[str] = [
        f"# Cheap vs expensive LLM — MiniZinc comparison (`{run_id}`)",
        "",
        "## 1. Question",
        "",
        "How do a cheap LLM and an expensive LLM differ on NL → MiniZinc, "
        "and how do their models perform under the same solver?",
        "",
        "## 2. Method",
        "",
        f"- Cheap model: `{cheap.get('model_id')}` "
        f"(temp={cheap.get('temperature')})",
        f"- Expensive model: `{expensive.get('model_id')}` "
        f"(temp={expensive.get('temperature')})",
        f"- MiniZinc: {mzn.get('version')}  solver=`{mzn.get('solver_id')}`  "
        f"time_limit_s={mzn.get('time_limit_s')}",
        f"- Protocol: generate once per model; single inlined `.mzn`",
        f"- Seeds: {', '.join(run_config.get('included_seed_ids') or [])}",
        "",
        "## 3. Per-instance results",
        "",
        "| Seed | Inst | Cheap outcome | Cheap t (s) | Exp outcome | Exp t (s) | Faster | Obj equal |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for pair in results.get("pairs") or []:
        c = pair.get("cheap") or {}
        e = pair.get("expensive") or {}
        cmp_ = pair.get("compare") or {}
        lines.append(
            "| {seed} | {inst} | {co} | {ct} | {eo} | {et} | {faster} | {obj} |".format(
                seed=pair.get("seed_id"),
                inst=pair.get("instance_id"),
                co=c.get("outcome"),
                ct=_fmt_time(c.get("solve_time_s")),
                eo=e.get("outcome"),
                et=_fmt_time(e.get("solve_time_s")),
                faster=cmp_.get("faster") or "NA",
                obj=_fmt_bool(cmp_.get("objective_equal")),
            )
        )

    lines.extend(
        [
            "",
            "## 4. Encoding notes",
            "",
            "_Fill in by hand after reading paired `.mzn` files._",
            "",
            "## 5. Limitations",
            "",
            "- Small N; per-instance narrative only.",
            "- No gold MiniZinc; faithfulness is human judgment.",
            "- Small instances may hide encoding quality differences.",
            "",
        ]
    )

    text = "\n".join(lines)
    if out_path is None:
        reports = run_dir.parents[1] / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        out_path = reports / f"{run_id}.md"
    else:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return out_path


def _fmt_time(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_bool(value: Any) -> str:
    if value is None:
        return "NA"
    return "yes" if value else "no"
