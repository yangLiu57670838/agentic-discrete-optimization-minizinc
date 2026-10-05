# Product Requirements Document

**Project:** Agentic Discrete Optimisation — NL → MiniZinc, cheap vs expensive LLM  
**Status:** Draft v0.14 (2-week scope)  
**Deadline:** 2 weeks from start  
**Date:** 6 October 2026

---

## 1. Question

> Given the same natural-language discrete optimisation problem and the same prompt, how do a **cheap** and an **expensive** LLM differ in the MiniZinc models they write?

"Differ" means four things, all judged against the natural-language (NL) seed:

1. **Runs** — does the `.mzn` compile, and does the solver terminate validly?
2. **Faithful** — are the stated constraints and the objective actually modelled? (human review)
3. **Result quality** — under the same solver and time limit, which model reaches the better objective?
4. **Speed** — when both finish the search, which model's encoding solves faster?

**Core research target:** compare the two models on the same seed. Faithfulness beats everything: a model that compiles and solves fast but solves the wrong problem is a failure, and its objective and time do not count.

**Audience:** GitHub portfolio (AI engineer jobs) and a short research write-up (PhD application).

---

## 2. Why an LLM at all

An NL seed already lists decisions, rules, and an objective, so it can look like MiniZinc just needs "math syntax". The gap is **modelling judgment**: choosing decision variables, linking them to the rules, encoding soft penalties, and wiring the objective to the decisions. Syntax can be perfect while the design is wrong.

Example: the NL says "an employee works a weekend if they work *at least one* of its two days". A model that writes `works_weekend = x[sat] /\ x[sun]` compiles and solves, but counts only full weekends, so the weekend limit is too loose. The solver happily returns a "better" objective for the wrong problem. That is why the human review gates the objective and time comparison.

The research asks whether paying for a stronger model buys better modelling judgment, not just fewer syntax errors.

---

## 3. What ships in 2 weeks

1. **One** author-written NL seed: `p01` in `data/seed_problems.md` (hospital staff rostering and surgery scheduling, instance A). **No gold `.mzn`.** You do not write MiniZinc.
2. **Two LLMs**, set in `configs/default.yaml`:
   - **cheap:** `gpt-4.1-nano`
   - **expensive:** `gpt-4.1`
3. Each model **generates exactly one `.mzn` per seed** from the **same prompt** at the **same temperature (0.0)** and token budget. No repair, no resampling.
4. Local **MiniZinc Python** as the oracle. Every generated `.mzn` is compiled and solved with the **same solver (Gecode)** and the **same time limit (10s)** on the same machine, one after another.
5. `run_config.json` for every run: requested and API-reported model ids, MiniZinc version, solver, limits, prompt hash, git commit (§6.2).
6. `results.json`: per seed, both models' outcome, objective, solve time, LLM latency and tokens, plus the solver-side comparison (§7).
7. `review.yaml`: a template you fill in by hand (constraints missing, objective correct, 1–5 score per model).
8. `reports/<run_id>.md`, re-rendered after you fill `review.yaml`.
9. README: install MiniZinc, set the API key, `check-minizinc`, `run`, `report`.

If time slips, **cut in this order:** report polish → summary table → token/latency columns. Do **not** cut: the MiniZinc oracle, both models on p01, the human review, `run_config.json`.

---

## 4. Out of scope

UI/SaaS, extra solvers, fine-tuning, repair loops, multiple samples per model, LLM-as-judge, a third model, providers other than OpenAI, formal equivalence proofs, agent-emitted `.dzn`, author-written MiniZinc / gold `.mzn`, prompt engineering per model (both models must see identical input).

---

## 5. Research questions (answer per seed, as a case study, not a %)

| ID | Question |
|---|---|
| RQ1 | Does each model's `.mzn` compile and reach valid termination (`SATISFIED` / `OPTIMAL_SOLUTION` / `UNSATISFIABLE`)? |
| RQ2 | Which stated constraints (C1, C2, …) does each model miss or get wrong? Is the objective the right sense and quantity, linked to the decisions? |
| RQ3 | If both are faithful and both terminate validly, which reaches the better objective within the time limit? |
| RQ4 | If both finish the search (optimum proven), which encoding solves faster? |
| RQ5 | What does the expensive model cost in latency and tokens, and is the quality gain worth it on this seed? |

**Hypotheses (light):** the cheap model is more likely to fail to compile or to drop hard-to-encode rules (weekend counting, surgery overlap, theatre capacity); the expensive model is more likely to be faithful. Speed differences only matter after faithfulness.

---

## 6. Protocol

```
for seed in seeds:                         # v1: just p01
    for model in [cheap, expensive]:
        mzn[model] = LLM(model).generate(prompt(seed.nl))   # once; same prompt, temp 0
        save runs/<id>/<seed>/<model>.mzn
    for model in [cheap, expensive]:
        result[model] = minizinc.solve(mzn[model], solver=gecode, t=10s)   # timed
    compare(result[cheap], result[expensive])
human fills review.yaml → report re-rendered
```

- The LLM never grades anything. MiniZinc decides outcome; you decide faithfulness.
- Generate both models first, then solve one after the other, so LLM latency never overlaps a timed solve.
- If a reply also contains a `.dzn` block, **ignore it**. Only the `.mzn` block is compiled.
- The prompt has **output-format rules only** (one `minizinc` code block, data inlined, a `solve` item). No modelling advice, so the comparison measures the models, not the prompt.
- API key via env (`OPENAI_API_KEY`) only. Never log it or put it in `run_config`.
- If one model's API call fails, record `LLM_ERROR` for that model and still run the other.

**CLI:**

```
python -m ado_mzn check-minizinc
python -m ado_mzn run --seed data/seed_problems.md --config configs/default.yaml
python -m ado_mzn report runs/<run_id>
```

`check-minizinc` solves a bundled smoke `.mzn` (harness fixture, not a seed) with **no LLM**. `run` probes MiniZinc (fail fast if missing), writes `run_config.json` **first**, then both `.mzn` files, `results.json`, `review.yaml`, and `reports/<id>.md`. `report` re-renders the report after you edit `review.yaml`.

### 6.1 Outcome taxonomy (MiniZinc is the oracle)

Every compile/solve maps to **exactly one** bucket, decided by the wrapper, not the LLM.

| Bucket | Meaning |
|---|---|
| **`LLM_ERROR`** | The API call failed; no `.mzn` exists for this model. |
| **`COMPILE_ERROR`** | MiniZinc rejects the model: parse, type-check, or flattening fails. Solver not invoked. |
| **`SOLVER_ERROR`** | Flattening succeeds, the solver is invoked, but solver execution fails. |
| **`TIMEOUT / UNKNOWN`** | The solver starts but returns no qualifying result in the time limit. |
| **`SATISFIED`** / **`OPTIMAL_SOLUTION`** / **`UNSATISFIABLE`** | Valid solver termination. |

For an optimisation seed, `SATISFIED` means a solution was found but optimality was not proven within the limit; `OPTIMAL_SOLUTION` means the search finished.

### 6.2 `run_config.json` (required)

Written at the start of `run`, after probing MiniZinc and before any LLM call. `resolved_model_id` is filled in from the API response after generation.

```json
{
  "run_id": "2026-10-06T120000Z",
  "started_at": "2026-10-06T12:00:00Z",
  "finished_at": "2026-10-06T12:01:10Z",
  "config_path": "configs/default.yaml",
  "seed_file": "data/seed_problems.md",
  "included_seed_ids": ["p01"],
  "protocol": {
    "generate_once_per_model": true,
    "repair": false,
    "output": "single_mzn",
    "same_prompt_for_all_models": true
  },
  "models": {
    "cheap":     {"provider": "openai", "requested_model_id": "gpt-4.1-nano", "resolved_model_id": "gpt-4.1-nano-2025-04-14"},
    "expensive": {"provider": "openai", "requested_model_id": "gpt-4.1",      "resolved_model_id": "gpt-4.1-2025-04-14"}
  },
  "llm": {"temperature": 0.0, "max_tokens": 4096, "timeout_s": 120},
  "prompts_sha256": {"generate": "4f0149b61d71deac"},
  "minizinc": {"version": "2.10.1", "driver_path": "...", "python_package_version": "0.10.0", "solver_id": "gecode", "time_limit_s": 10},
  "git": {"commit": "abc1234", "dirty": false}
}
```

The report's Method section is generated from this file, never handwritten.

---

## 7. Metrics

**Automatic (from MiniZinc), per model:**

| Metric | Source |
|---|---|
| Outcome | §6.1 bucket |
| Compiles | outcome ≠ `COMPILE_ERROR` / `LLM_ERROR` |
| Valid termination | `SATISFIED` / `OPTIMAL_SOLUTION` / `UNSATISFIABLE` |
| Objective | value reported by the solver (optimisation seeds) |
| Compile + solve time | wall time around compile and solve, same clock for both models |
| LLM latency, input/output tokens | API response |
| `.mzn` lines | generated file |

**Automatic comparison, per seed:**

| Field | Rule |
|---|---|
| `objective_better` | Both valid termination → lower wins for minimise, higher for maximise; `tie`; else `NA` |
| `faster_to_finish` | Both finished the search → lower solve time wins (`tie` if within 0.1s); only one finished → that one; else `NA` |
| `solve_time_ratio_cheap_over_expensive` | When both finished |

**Human (you, in `review.yaml`), per model:**

| Metric | Pass |
|---|---|
| Constraints missing | ids from the seed's Constraint inventory the model lacks or gets wrong (`[]` = none) |
| Objective correct | right sense, right quantity, linked to the decisions |
| Review 1–5 | 1 unrelated … 5 reasonable first draft. Judge NL vs `.mzn` + solver outcome |

**Reading rule:** the objective and speed comparison only counts for a model whose human review says it is faithful. If the cheap model is "faster" because it dropped C11, that is a faithfulness failure, not a speed win.

N=1 in v1: report the **p01 case**, not a win rate.

---

## 8. Seed

**File:** `data/seed_problems.md`. v1 has one heading, `## p01`. The runner runs every heading in the file, so more seeds can be added later without code changes, but v1's result is about p01.

**You write English only.** No `var`, `constraint`, `solve`, or any MiniZinc. There is no gold `.mzn`.

`ado_mzn/schemas/seed.py` splits the file on `## <id> — <title>` headings. Each model sees **only one seed's NL** per call.

**Completeness test (enforced by the parser):**

- `### Problem`, `### Instance data`, `### Objective` present and non-empty
- No MiniZinc syntax (`var int`, `solve minimize`, a line starting with `constraint`, `array[`, `include "`)
- Unique ids; heading id matches `- id:`

**Seed schema:**

```markdown
## p01 — Short title
- id: p01
- family: rostering_scheduling
- type: optimisation

### Problem

Natural-language statement. Say what to choose, the rules, and min/max what.

### Instance data

Numbers the model must inline into its `.mzn`.

### Constraint inventory   # optional, plain English; ids feed review.yaml
- C1: ...

### Objective
- sense: minimize
- quantity: request penalty + staffing penalty
```

The current seed (hospital staff rostering and surgery scheduling, instance A: one shift type) is p01.

---

## 9. Repo layout

```
ado_mzn/toolchain/minizinc.py        # probe, check-minizinc, timed compile_and_solve, outcomes
ado_mzn/toolchain/fixtures/smoke.mzn # bundled toolchain test; not a seed
ado_mzn/schemas/seed.py              # parse seed file → one record per heading
ado_mzn/schemas/run_config.py        # load YAML, build/write run_config.json
ado_mzn/schemas/results.py           # per-seed, per-model result records
ado_mzn/agent/prompts.py             # the one generate prompt (same for both models)
ado_mzn/agent/generate.py            # OpenAI Responses call, extract .mzn, save <model>.mzn
ado_mzn/eval/metrics.py              # cheap vs expensive comparison
ado_mzn/eval/runner.py               # full run
ado_mzn/report/render.py             # reports/<run_id>.md
data/seed_problems.md                # NL seed(s): p01
configs/default.yaml                 # cheap/expensive model ids, solver, limits
runs/<id>/run_config.json
runs/<id>/results.json
runs/<id>/review.yaml                # you fill this in
runs/<id>/p01/cheap.mzn              # + cheap.raw.txt (full LLM reply)
runs/<id>/p01/expensive.mzn          # + expensive.raw.txt
reports/<id>.md
```

---

## 10. Two-week plan

| Days | Do | Done when |
|---|---|---|
| **1–2** | MiniZinc install; wrapper; `check-minizinc` | smoke model reaches valid termination, no LLM |
| **3–4** | p01 NL complete; parser | `parse_seeds` returns p01 with no errors |
| **5–6** | First real `run` with both models | `cheap.mzn`, `expensive.mzn`, `results.json` exist |
| **7–9** | Review both models against the NL; fill `review.yaml` | every human field filled for p01 |
| **10–11** | If both time out or both fail trivially, adjust the solver time limit (same for both) and rerun; keep the earlier run | one run you can explain |
| **12–13** | Report prose (findings, failure notes) + README | clone-and-run documented |
| **14** | Freeze p01 NL and config; tag v1 | `reports/<id>.md` final |

---

## 11. Done-when (v1)

- [ ] `check-minizinc` passes on the bundled smoke model.
- [ ] `run` writes `run_config.json` (both requested and resolved model ids, MiniZinc version, solver, limit) before generation.
- [ ] Both models generated exactly one `.mzn` for p01 from the identical prompt.
- [ ] Both `.mzn` files solved with the same solver and time limit; outcome, objective, time recorded.
- [ ] `review.yaml` filled for both models.
- [ ] `reports/<id>.md`: method from `run_config`, p01 comparison, failure notes, limitations.
- [ ] README: MiniZinc install, env var, `check-minizinc`, `run`, `report`.
- [ ] Negative results are acceptable (e.g. both fail, or cheap wins).

---

## 12. Report outline (generated, then you add prose)

1. Question
2. Method — from `run_config.json` (both model ids, temperature, prompt hash, MiniZinc version, Gecode, time limit)
3. Results per seed — cheap vs expensive table (automatic + human rows), comparison lines
4. Summary across seeds
5. Failure notes — diagnostics for every non-valid outcome
6. Limitations — N=1, one sample per model, no reference model, one human reviewer, machine-dependent timing

---

## 13. Risks

| Risk | What you do |
|---|---|
| MiniZinc not installed | Day 1 `check-minizinc` |
| Both models time out (hard seed, 10s) | Raise `time_limit_s` for both, rerun, report both runs |
| Fast but unfaithful model looks like a "win" | Reading rule in §7: review gates objective/speed |
| Prompt favours one model | One shared prompt, format rules only; hash in `run_config` |
| Nondeterminism despite temperature 0 | State it; one sample per model is a limitation |
| Model id drifts behind an alias | Record `resolved_model_id` from the API |
| Timing noise | Solve sequentially on the same machine; differences under 0.1s are ties |
| Scope creep (repair, more models, more seeds) | Out of scope for v1 |
| API cost | One call per model per seed; tokens recorded in `results.json` |

---

## 14. Result record (per seed in `results.json`)

```json
{
  "seed_id": "p01",
  "title": "Hospital staff rostering and surgery scheduling (instance A: one shift type)",
  "objective_sense": "minimize",
  "constraint_ids": ["C1", "C2", "...", "C12"],
  "attempts": {
    "cheap": {
      "requested_model_id": "gpt-4.1-nano",
      "resolved_model_id": "gpt-4.1-nano-2025-04-14",
      "outcome": "COMPILE_ERROR",
      "mzn_path": "runs/<id>/p01/cheap.mzn",
      "mzn_lines": 84,
      "llm": {"duration_s": 6.2, "usage": {"input_tokens": 2100, "output_tokens": 1400}},
      "solve": {"outcome": "COMPILE_ERROR", "objective": null, "solve_time_s": 0.08, "diagnostics": "..."}
    },
    "expensive": {
      "requested_model_id": "gpt-4.1",
      "outcome": "SATISFIED",
      "solve": {"outcome": "SATISFIED", "objective": 607, "solve_time_s": 10.1}
    }
  },
  "comparison": {
    "objective_better": "NA",
    "faster_to_finish": "NA",
    "solve_time_ratio_cheap_over_expensive": null
  }
}
```

---

## 15. MiniZinc Python (contract)

```python
from datetime import timedelta
import minizinc

model = minizinc.Model(mzn_path)  # one file; no .dzn
inst = minizinc.Instance(minizinc.Solver.lookup("gecode"), model)
result = inst.solve(timeout=timedelta(seconds=10))   # timed by the wrapper
# MiniZincError before solver invoke → COMPILE_ERROR
# solver invoked then fails → SOLVER_ERROR
# result.status unknown / limit → TIMEOUT / UNKNOWN
# SATISFIED | OPTIMAL_SOLUTION | UNSATISFIABLE → valid termination
```

The pip package `minizinc` does not include the compiler. Install MiniZinc locally.

---

**Brief:** In two weeks, write one NL seed (p01), let a cheap model (`gpt-4.1-nano`) and an expensive model (`gpt-4.1`) each write one `.mzn` from the identical prompt, solve both with the same Gecode time limit, compare outcome, objective and speed, judge faithfulness yourself, and ship `run_config.json`, `results.json`, and a short comparison report.
