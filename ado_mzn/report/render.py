# Render reports/<run_id>.md from run_config.json, results.json, and the human review.yaml.

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

import yaml

from ado_mzn.schemas.run_config import read_json

LABELS = ("cheap", "expensive")
DIAGNOSTICS_CHARS = 600


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "none"
    return str(value)


def _usage(llm: dict[str, Any], key: str) -> Optional[int]:
    return (llm.get("usage") or {}).get(key)


def _load_review(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "review.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _method(cfg: dict[str, Any]) -> list[str]:
    mzn = cfg.get("minizinc", {})
    llm = cfg.get("llm", {})
    git = cfg.get("git", {})
    lines = [
        "## 2. Method",
        "",
        "Each model received the **same prompt** (output-format rules only) and the same seed text, "
        "generated **one** `.mzn` per seed (no repair), and every `.mzn` was compiled and solved with the "
        "**same solver and time limit**. Values below are copied from `run_config.json`.",
        "",
        "| Role | Requested model | Model reported by API |",
        "|---|---|---|",
    ]
    for label in LABELS:
        m = cfg.get("models", {}).get(label, {})
        lines.append(f"| {label} | `{m.get('requested_model_id')}` | `{m.get('resolved_model_id')}` |")
    lines += [
        "",
        f"- Temperature {llm.get('temperature')}, max output tokens {llm.get('max_tokens')}",
        f"- MiniZinc {mzn.get('version')}, solver `{mzn.get('solver_id')}`, time limit {mzn.get('time_limit_s')}s per solve",
        f"- Prompt hash `{cfg.get('prompts_sha256', {}).get('generate')}`",
        f"- Seeds: {', '.join(cfg.get('included_seed_ids', []))} from `{cfg.get('seed_file')}`",
        f"- Git commit `{git.get('commit')}`" + (" (uncommitted changes)" if git.get("dirty") else ""),
        "",
    ]
    return lines


def _seed_section(seed: dict[str, Any], review: dict[str, Any]) -> list[str]:
    attempts = seed["attempts"]
    comp = seed.get("comparison", {})
    rev = review.get(seed["seed_id"]) or {}

    def row(name: str, fn) -> str:
        return f"| {name} | " + " | ".join(_fmt(fn(attempts[l], rev.get(l) or {})) for l in LABELS) + " |"

    solve = lambda a: a.get("solve") or {}
    lines = [
        f"### {seed['seed_id']} — {seed['title']}",
        "",
        "| Metric | cheap | expensive |",
        "|---|---|---|",
        row("Outcome", lambda a, r: a["outcome"]),
        row("Compiles", lambda a, r: solve(a).get("compile_success")),
        row("Valid termination", lambda a, r: solve(a).get("solver_success")),
        row(f"Objective ({seed.get('objective_sense') or 'NA'})", lambda a, r: solve(a).get("objective")),
        row("Compile + solve time (s)", lambda a, r: solve(a).get("solve_time_s")),
        row("LLM latency (s)", lambda a, r: a.get("llm", {}).get("duration_s")),
        row("Input / output tokens", lambda a, r: (
            f"{_usage(a.get('llm', {}), 'input_tokens')} / {_usage(a.get('llm', {}), 'output_tokens')}"
            if a.get("llm") else None
        )),
        row(".mzn lines", lambda a, r: a.get("mzn_lines")),
        row("Constraints missing (human)", lambda a, r: r.get("constraints_missing")),
        row("Objective correct (human)", lambda a, r: r.get("objective_correct")),
        row("Review 1–5 (human)", lambda a, r: r.get("review_score")),
        "",
        f"- Better objective: **{comp.get('objective_better', 'NA')}**",
        f"- Finished search first: **{comp.get('faster_to_finish', 'NA')}**"
        + (f" (time ratio cheap/expensive {comp['solve_time_ratio_cheap_over_expensive']})"
           if comp.get("solve_time_ratio_cheap_over_expensive") is not None else ""),
        "- Objective and time comparisons only count if the human review says both models are faithful.",
        "",
    ]
    for label in LABELS:
        notes = (rev.get(label) or {}).get("notes")
        if notes:
            lines.append(f"- {label} notes: {notes}")
    lines.append("")
    return lines


def _summary(seeds: list[dict[str, Any]], review: dict[str, Any]) -> list[str]:
    lines = ["## 4. Summary across seeds", "", "| | cheap | expensive |", "|---|---|---|"]

    def count(pred) -> str:
        return " | ".join(str(sum(1 for s in seeds if pred(s, l))) for l in LABELS)

    lines.append(f"| Valid termination | {count(lambda s, l: s['comparison']['solver_success'][l])} |")
    lines.append(f"| Better objective | {count(lambda s, l: s['comparison']['objective_better'] == l)} |")
    lines.append(f"| Finished search first | {count(lambda s, l: s['comparison']['faster_to_finish'] == l)} |")

    scores = []
    for label in LABELS:
        vals = [
            ((review.get(s["seed_id"]) or {}).get(label) or {}).get("review_score")
            for s in seeds
        ]
        vals = [v for v in vals if isinstance(v, (int, float))]
        scores.append(f"{sum(vals) / len(vals):.1f} (n={len(vals)})" if vals else "—")
    lines.append(f"| Mean review score | {scores[0]} | {scores[1]} |")
    lines += ["", f"N = {len(seeds)} seed(s): describe cases, not success rates.", ""]
    return lines


def _failures(seeds: list[dict[str, Any]]) -> list[str]:
    lines = ["## 5. Failure notes", ""]
    found = False
    for seed in seeds:
        for label in LABELS:
            a = seed["attempts"][label]
            text = a.get("llm_error") or (a.get("solve") or {}).get("diagnostics")
            if not text or (a.get("solve") or {}).get("solver_success"):
                continue
            found = True
            snippet = text.strip()[:DIAGNOSTICS_CHARS]
            lines += [f"**{seed['seed_id']} / {label} — {a['outcome']}**", "", "```", snippet, "```", ""]
    if not found:
        lines += ["None: every generated model reached valid termination.", ""]
    return lines


def render_report(run_dir: Union[str, Path], reports_dir: Union[str, Path] = "reports") -> Path:
    run_dir = Path(run_dir)
    cfg = read_json(run_dir / "run_config.json")
    results = read_json(run_dir / "results.json")
    review = _load_review(run_dir)
    seeds = results.get("seeds", [])

    lines = [
        f"# Cheap vs expensive LLM → MiniZinc — run {cfg['run_id']}",
        "",
        "## 1. Question",
        "",
        "Given the same natural-language discrete optimisation problem and the same prompt, how do a cheap and "
        "an expensive LLM differ in the MiniZinc models they write: does each compile, solve, stay faithful to "
        "the problem, and how good and how fast is the result under the same solver?",
        "",
        *_method(cfg),
        "## 3. Results per seed",
        "",
    ]
    for seed in seeds:
        lines += _seed_section(seed, review)
    lines += _summary(seeds, review)
    lines += _failures(seeds)
    lines += [
        "## 6. Limitations",
        "",
        "- Small N; one sample per model at temperature 0, so results are cases, not rates.",
        "- The author wrote the NL only; the LLMs wrote all MiniZinc; there is no reference model.",
        "- Faithfulness is judged by one human reviewer.",
        "- Solve time includes flattening and depends on the machine; both models ran on the same machine.",
        "",
    ]

    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{cfg['run_id']}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
