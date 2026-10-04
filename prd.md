# Product Requirements Document

**Project:** Agentic Discrete Optimisation — NL → MiniZinc  
**Status:** Draft v0.12 (2-week scope)  
**Deadline:** 2 weeks from start  
**Date:** 4 October 2026

---

## 1. Question

> How effectively can an LLM-based agent translate natural-language discrete optimisation problems into executable MiniZinc models?

v1 is a **one-problem case study**. You write **one** natural-language seed (`p01` in `data/seed_problems.md`) — no MiniZinc. Extra seeds are out of scope. The LLM is the only source of the seed `.mzn`. Faithfulness beats compilation: a model that compiles but solves the wrong problem is a failure.

**Audience:** GitHub portfolio (AI engineer jobs) and a short research write-up (PhD application).

---

## 2. What ships in 2 weeks

1. **One** author-written natural-language seed: `p01` in `data/seed_problems.md`. **N = 1.** **No gold `.mzn`.** You do not write MiniZinc.
2. An agent: that NL (including its numbers) → **one executable `.mzn`**. That is the only MiniZinc in the experiment besides a tiny **bundled smoke file** used to test the toolchain.
3. Local **MiniZinc Python** as the oracle (compile + solve). Default solver: **Gecode**, **10s** per solve.
4. Repair up to **K=3** only on `COMPILE_ERROR` or `SOLVER_ERROR`. Do **not** repair `TIMEOUT` / `UNKNOWN` or valid termination (`SATISFIED` / `OPTIMAL_SOLUTION` / `UNSATISFIABLE`).
5. One LLM. **Generate attempt 0 exactly once for p01.** K=0 scores that `.mzn`. K=3 continues from the **same** attempt-0 `.mzn` (up to three repairs). Do not regenerate to produce the K=0 vs K=3 comparison.
6. A Markdown report from the run (`reports/<run_id>.md`).
7. **`run_config.json`** for every run: the actual LLM, MiniZinc, solver, limits, and seed list used (see §5.2).
8. README: how to install MiniZinc, set the API key, `check-minizinc`, run the agent.

If time slips, **cut in this order:** polish → report prose → skip the repair loop (keep attempt 0 / K=0). Do **not** cut: MiniZinc oracle, metrics on p01, the one complete NL seed. Never “compare” K=0 and K=3 from two different generations.

---

## 3. Out of scope

UI/SaaS, extra solvers, fine-tuning, a second seed (`p02+`), second LLM, compile-only ablation, LLM-as-judge, formal equivalence proofs, MiniZinc Challenge, a second `generate` call used as a fake K=0 baseline, **agent-emitted `.dzn`**, **author-written MiniZinc / gold `.mzn`**.

---

## 4. Research questions (answer for **p01**, not as a %)

| ID | Question |
|---|---|
| RQ1 | Does attempt 0 compile, and does it end in **valid solver termination** (`SATISFIED` / `OPTIMAL_SOLUTION` / `UNSATISFIABLE`)? |
| RQ2 | Starting from that same attempt-0 model, do up to three repairs recover from `COMPILE_ERROR` / `SOLVER_ERROR` to valid termination? |
| RQ3 | Are the stated constraints present? Is the objective the right min/max and quantity? |
| RQ4 | Which outcome bucket occurred (compile error, solver error, timeout/unknown, valid termination), and what modelling mistakes remain? |

**Hypotheses (light):** single-shot on p01 will fail to compile, or will compile a shallow/wrong model; repair may fix compile but not faithfulness.

---

## 5. Agent

**Paired K=0 / K=3 (required).** For p01, in one run:

1. **Generate attempt 0 exactly once** (`LLM.generate`). Save **one** `attempt_0.mzn`. Do not sample again for this seed in the headline run. Inline parameters in that file; do not emit `.dzn`.
2. Compile/solve that `.mzn`. That row is **K=0**.
3. **K=3** starts from that exact `.mzn`. Repair **only** while the latest outcome is `COMPILE_ERROR` or `SOLVER_ERROR`, up to three times (always re-attach the original NL). If attempt 0 is `TIMEOUT` / `UNKNOWN` or valid termination, do **not** repair; K=3 copies K=0 (`repairs_used = 0`).

```
model_0 = LLM.generate(nl)               # once for p01; one .mzn, data inlined
save attempt_0.mzn
result_0 = minizinc_python.solve(attempt_0.mzn, solver=gecode, t=10s)
# K=0 := (model_0, result_0)

model, result = model_0, result_0
repairs_used = 0
while result in {COMPILE_ERROR, SOLVER_ERROR} and repairs_used < 3:
    model = LLM.repair(model, diagnostics, original_nl)
    result = minizinc_python.solve(model, solver=gecode, t=10s)
    repairs_used += 1
# K=3 := (model, result)  — same lineage as model_0
```

- LLM never grades compile/solve. Log `attempt_0.mzn`, each repaired `.mzn`, diagnostics.
- If the LLM also dumps a `.dzn`, **ignore it**. Only the `.mzn` is compiled.
- Prompt the model to put sets, parameters, constraints, and `solve` in **a single `.mzn`**.
- Wall clock cap: **180s** for p01 including LLM. API key via env only; never put the key in `run_config`.
- The seed contains **no MiniZinc**. The agent prompt is the p01 NL only.

**CLI:**

```
python -m ado_mzn check-minizinc
python -m ado_mzn run --seed data/seed_problems.md --config configs/default.yaml
```

`check-minizinc` solves a **bundled smoke `.mzn`** (harness fixture, not a seed) to prove MiniZinc + the wrapper work **with no LLM**. `run` writes `runs/<id>/run_config.json` **first**, then `attempt_0.mzn`, K=0/K=3 scores, `results.json`, and `reports/<id>.md`. Fail fast if MiniZinc is missing. The report Method section is filled from `run_config`.

### 5.1 Outcome taxonomy (MiniZinc is the oracle)

Every compile/solve maps to **exactly one** bucket. The wrapper must classify MiniZinc Python exceptions vs `result.status` using these rules — not the LLM.

| Bucket | Meaning |
|---|---|
| **`COMPILE_ERROR`** | MiniZinc **rejects** the model: parse, type-check, or flattening fails. The solver is **not** invoked. |
| **`SOLVER_ERROR`** | Flattening succeeds and the **solver is invoked**, but **solver execution fails** (crash, abort, unsupported, runtime exception). |
| **`TIMEOUT` / `UNKNOWN`** | The **solver starts** but **no qualifying result** is returned (time limit, unknown, incomplete). |
| **`SATISFIED`** / **`OPTIMAL_SOLUTION`** / **`UNSATISFIABLE`** | **Valid solver termination.** A qualifying result. |

**Derived flags**

| Flag | True iff |
|---|---|
| `compile_success` | Not `COMPILE_ERROR` (flattening finished; solver was reached or a valid/timeout/unknown status exists) |
| `solver_success` | Valid termination: `SATISFIED` or `OPTIMAL_SOLUTION` or `UNSATISFIABLE` |
| `should_repair` | `COMPILE_ERROR` or `SOLVER_ERROR` only |

`TIMEOUT` / `UNKNOWN` is **not** `solver_success` and **not** repaired. Valid `UNSATISFIABLE` **is** `solver_success` (the toolchain finished); whether UNSAT is the *right* model is a faithfulness question (§6).

If the seed is optimisation and status is `SATISFIED` or `OPTIMAL_SOLUTION`, parse an objective value when the solver provides one.

### 5.2 `run_config` (required)

Record **what actually ran**. Write `runs/<id>/run_config.json` at the start of `run`, after probing MiniZinc, before any LLM call. Do not rely on `configs/default.yaml` alone — copy resolved values (model id string returned by the API, MiniZinc version from the binary, …).

**Required fields**

```json
{
  "run_id": "2026-08-26T120000Z",
  "started_at": "2026-08-26T12:00:00Z",
  "config_path": "configs/default.yaml",
  "seed_file": "data/seed_problems.md",
  "included_seed_ids": ["p01"],
  "protocol": {
    "generate_once": true,
    "k_max": 3,
    "repair_on": ["COMPILE_ERROR", "SOLVER_ERROR"],
    "output": "single_mzn"
  },
  "llm": {
    "provider": "openai",
    "model_id": "gpt-4.1-mini",
    "temperature": 0.0,
    "max_tokens": 4096
  },
  "minizinc": {
    "version": "2.8.x",
    "driver_path": "/opt/homebrew/bin/minizinc",
    "python_package_version": "0.9.x",
    "solver_id": "gecode",
    "time_limit_s": 10
  },
  "limits": {
    "wall_clock_s_per_seed": 180
  },
  "git_commit": "abc1234"
}
```

**Also log (not secrets):** generate and repair prompt templates (path or hash); per-seed timestamps; MiniZinc diagnostics. **Never log API keys.**

`temperature` / `model_id` / MiniZinc `version` in the report must match this file. If a field could not be probed, store `null` and fail the run only for MiniZinc missing — still write the rest so the experiment is inspectable.

`included_seed_ids` is `["p01"]` for v1.

---

## 6. Metrics (p01; K=0 and K=3 from one generation)

K=0 = `attempt_0.mzn` after one compile/solve. K=3 = that same file after up to three in-place repairs (or a copy of K=0 if no repair ran).

| Metric | Pass |
|---|---|
| **Compile** | Outcome ≠ `COMPILE_ERROR`. Report @ attempt 0 and @ K=3 |
| **Solver** | Valid termination (`SATISFIED` / `OPTIMAL_SOLUTION` / `UNSATISFIABLE`). Same two columns |
| **Repair** | Attempt 0 was `COMPILE_ERROR` or `SOLVER_ERROR` **and** some repair 1..3 reaches valid termination; else `NA` (already valid, or `TIMEOUT`/`UNKNOWN` at attempt 0) |
| **Constraints** | Human: requirements stated in the NL (optional English C1, C2, …) are in the generated model. Score attempt 0; if the K=3 `.mzn` differs, score it too |
| **Objective** | Human: right sense + quantity + linked to decisions, as stated in the NL (`NA` if SAT-only) |
| **Review 1–5** | 1 unrelated … 5 reasonable first draft. Judge **NL vs generated `.mzn` + status** only. Score attempt 0; score K=3 if the `.mzn` changed |

N=1: report the **p01 case**, not a success rate. Solver success ≠ correct model.

**Table columns:** outcome @0 / @K=3, compile @0 / @K=3, solver_success @0 / @K=3, repair yes/no/NA, repairs_used, constraints (and missing ids) @0 and @K=3 if different, objective, review.

---

## 7. Seed (one natural-language problem)

**N = 1.** File: `data/seed_problems.md` with a single heading, **`## p01`**. v1 does not add `p02`.

**You write English only.** You do **not** write `var`, `constraint`, `solve`, or any other MiniZinc. There is **no** `gold.mzn`. The first `.mzn` is `runs/<id>/p01/attempt_0.mzn` from the LLM.

A bundled smoke model (`ado_mzn/toolchain/fixtures/smoke.mzn`) is **not** the seed. It only proves the compiler works.

`ado_mzn/schemas/seed.py` parses `## p01` into one record. The runner and LLM see **only that NL**.

**Completeness test (p01 must pass):**

- Clear decisions (what is chosen)
- Constraints stated in the problem text (or English C1, C2, … — still not MiniZinc)
- SAT **or** min/max + quantity in words
- **Numeric data** in the prose and/or `### Instance data`
- **No MiniZinc keywords** (`var int`, `constraint`, `solve minimize`, …)

**Seed schema (v1 uses this one problem only):**

```markdown
## p01 — Short title
- id: p01
- family: capacity_expansion
- type: optimisation

### Problem

Natural-language statement. Say what to choose, the rules, and min/max what.

### Instance data

Numbers the agent must inline into its `.mzn`.

### Constraint inventory   # optional, plain English
- C1: ...

### Objective
- sense: minimize
- quantity: total building cost
```

No `### Gold` section. The current repo seed (PowerGen capacity expansion) is the intended p01.

---

## 8. Repo layout

```
ado_mzn/          # agent, minizinc wrapper, eval, report
ado_mzn/toolchain/fixtures/smoke.mzn   # bundled toolchain test; not a seed
data/seed_problems.md              # one NL seed: p01
configs/default.yaml
runs/<id>/run_config.json
runs/<id>/results.json
runs/<id>/p01/attempt_0.mzn        # LLM MiniZinc for p01
reports/
prd.md
README.md
```

---

## 9. Two-week plan

| Days | Do | Done when |
|---|---|---|
| **1–2** | Install MiniZinc; wrapper; `check-minizinc` on bundled smoke `.mzn` | smoke model reaches valid termination, **no LLM** |
| **3–4** | Finish **p01** NL in `data/seed_problems.md`; parser | one complete heading |
| **5–7** | LLM generate **once** for p01; save `attempt_0.mzn`; optional repair | p01 `.mzn` exists |
| **8–9** | `run_config.json` + paired K=0/K=3 for p01 | one paired result row |
| **10–11** | You score NL vs generated `.mzn` (constraints, objective, review) | p01 reviewed |
| **12–13** | `reports/<id>.md` + README | clone-and-run documented |
| **14** | Freeze p01 NL | tag v1 |

Slip buffer: skip repair, not the one seed.

---

## 10. Done-when (v1)

- [ ] `check-minizinc` passes on the bundled smoke model (no LLM, no seed MiniZinc).
- [ ] Each `run` writes `run_config.json` (resolved LLM id, MiniZinc version, solver, limits, `included_seed_ids: ["p01"]`) before generation.
- [ ] `run` generates **p01 once**, saves `attempt_0.mzn`, and writes K=0 + K=3 into `results.json`.
- [ ] Report Method section is generated from `run_config`, not handwritten model names.
- [ ] All six metrics filled for p01 (you are the reviewer, using the NL as the spec).
- [ ] `reports/<id>.md` exists: method, **p01 case study**, limitations (N=1, **author wrote NL only**, LLM wrote the MiniZinc).
- [ ] README: MiniZinc install, env var, `check-minizinc`, `run`.
- [ ] Negative results are acceptable.

---

## 11. Report outline (fill from `results.json`)

1. Question  
2. Method — copy from `run_config.json` (LLM `model_id`, MiniZinc version, Gecode, 10s, generate once, K=3, single `.mzn`)  
3. Seed p01 (PowerGen / the one NL problem)  
4. p01 results: K=0 vs K=3 (not a rate)  
5. Failure notes (only what occurred)  
6. Limitations (N=1, NL-only, no reference MiniZinc, human faithfulness) and next step

---

## 12. Risks (2-week)

| Risk | What you do |
|---|---|
| MiniZinc not installed | Day 1 `check-minizinc`; README |
| Smoke fixture fails | Fix wrapper/install before any LLM |
| Repair deletes constraints | Always re-attach NL |
| Treating N=1 as a general LLM rate | Write a case study only |
| Scope creep | No second LLM, no UI, **do not write seed gold `.mzn`** |
| Independent K=0 reroll | K=3 must load saved `attempt_0.mzn` |
| Agent emits `.mzn` + `.dzn` | Compile only the `.mzn` |
| Missing MiniZinc version / model id | Require `run_config.json` |
| Config yaml ≠ what ran | Store resolved values after probe |
| Incomplete p01 NL (no numbers / no objective) | Do not run the agent until p01 is complete |
| Adding more seeds mid-sprint | Out of scope for v1 |

---

## 13. Result record (minimum)

```json
{
  "run_config_path": "runs/<id>/run_config.json",
  "instance_id": "p01",
  "attempt_0_path": "runs/<id>/p01/attempt_0.mzn",
  "outcome_k0": "COMPILE_ERROR",
  "outcome_k3": "OPTIMAL_SOLUTION",
  "compile_success_k0": false,
  "solver_success_k0": false,
  "compile_success_k3": true,
  "solver_success_k3": true,
  "repair_success": true,
  "repairs_used": 2,
  "constraints_missing_k0": ["C3"],
  "constraints_missing_k3": [],
  "objective_correct_k0": false,
  "objective_correct_k3": true,
  "review_score_k0": 2,
  "review_score_k3": 4
}
```

---

## 14. MiniZinc Python (contract)

```python
from datetime import timedelta
import minizinc

model = minizinc.Model(mzn_path)  # one file; no .dzn in v1
inst = minizinc.Instance(minizinc.Solver.lookup("gecode"), model)
# MiniZincError before solver invoke → COMPILE_ERROR
# solver invoked then fails → SOLVER_ERROR
# result.status unknown / limit → TIMEOUT / UNKNOWN
# SATISFIED | OPTIMAL_SOLUTION | UNSATISFIABLE → valid termination
```

Pip package `minizinc` does **not** include the compiler. Install MiniZinc locally.

---

**Brief:** In two weeks, write **one** NL seed (p01), prove MiniZinc with a bundled smoke model (no LLM), generate one `.mzn` for that seed, pair K=0/K=3, score compile/solve/repair plus human faithfulness against the NL, and ship `run_config.json` plus a short p01 report.
