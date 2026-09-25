# Product Requirements Document

**Project:** Cheap vs expensive LLM — NL → MiniZinc  
**Status:** Draft v1.0 (1-week scope)  
**Deadline:** 1 week from start  
**Date:** 15 September 2026

---

## 1. Question

> Given the same natural-language discrete optimisation problems, how do a **cheap** LLM and an **expensive** LLM differ in the MiniZinc models they write, and how do those models perform under the **same** solver?

v1 is a **small author-written case study**. You write **natural-language problems only** — no MiniZinc. Target **5** complete seeds (`p01`–`p05`; N = count complete at freeze). Each seed may include **one or more numeric instances**. Both models see the same NL + instance and each emit **one** executable `.mzn`. MiniZinc (same solver, same time limit) is the oracle for compile/solve and wall-clock solve time. You write a short report comparing the two.

### Why this design

| Role | Who |
|---|---|
| **Author** | NL problem + instance data only |
| **Cheap LLM** | Invent `.mzn` (modelling judgment + language) |
| **Expensive LLM** | Invent `.mzn` independently from the same NL |
| **MiniZinc** | Same Gecode + time limit; compile/solve + timed run |
| **You** | Compare models (structure / faithfulness notes) and interpret timing |

Seeds describe the **problem**, not an expert encoding recipe. Matching lecture performance tricks is **not** a pass/fail metric. Efficiency is measured empirically (solve time, timeout), not by a checklist.

**Illustrative faithfulness failure (either model):** valid MiniZinc that compiles and “optimises” but drops a required constraint. Language/oracle look fine; modelling judgment failed.

---

## 2. What ships in 1 week

1. Author-written **NL** seeds in `data/seed_problems.md` (`p01`–`p05`; target **5** complete). **No gold `.mzn`.**
2. Dual agent: for each seed × instance, **cheap** and **expensive** each generate **one** `.mzn` (data inlined; no `.dzn`).
3. Local **MiniZinc Python** oracle. Default solver: **Gecode**. Same `time_limit_s` for both models.
4. Per pair: outcomes, objectives (when present), **wall-clock solve time**, solver statistics when available.
5. `runs/<id>/run_config.json` written **before** any LLM call; `results.json` with paired rows.
6. Markdown report `reports/<id>.md`: method, per-instance comparison, limitations.
7. README: install MiniZinc, API key, `check-minizinc`, `run`.

**Cut order if time slips:** polish → optional human faithfulness table → report prose. Do **not** cut: dual generate, same-solver timing, `run_config.json`, all **5** complete seeds.

---

## 3. Out of scope

UI/SaaS, fine-tuning, MiniZinc Challenge, gold `.mzn`, agent-emitted `.dzn`, LLM-as-judge as ground truth, repair loops (K=3), second solver family, formal equivalence proofs, lecture-trick checklists as metrics.

---

## 4. Research questions (answer per seed × instance)

| ID | Question |
|---|---|
| RQ1 | Does each model’s `.mzn` compile and reach **valid solver termination** (`SATISFIED` / `OPTIMAL_SOLUTION` / `UNSATISFIABLE`)? |
| RQ2 | Under the **same** solver and time limit, which model’s encoding is **faster** (wall-clock solve time)? Tie / NA if either failed or timed out. |
| RQ3 | Do objectives match when both succeed on an optimisation seed? |
| RQ4 | (Human, brief) How do the two encodings differ (variables, constraints, obvious modelling mistakes)? |

**Hypotheses (light):** the expensive model may be more faithful or more often compile; the cheaper model may still win on solve time when both succeed; small instances may hide encoding quality.

---

## 5. Protocol

**Per complete seed, per instance, in one run:**

```
nl = seed_nl + this_instance_data
cheap_mzn     = cheap_LLM.generate(nl)       # once
expensive_mzn = expensive_LLM.generate(nl)   # once
save …/cheap.mzn and …/expensive.mzn

result_c = minizinc.solve(cheap.mzn,     solver=gecode, t=T)
result_e = minizinc.solve(expensive.mzn, solver=gecode, t=T)
# record outcomes, objectives, wall_clock solve_time_s
```

- Same prompt template for both models (only `model_id` differs).
- Generate **once** per model per instance. No repair loop in v1.
- Same MiniZinc binary, solver id, and time limit for both.
- Wall clock: harness times `compile_and_solve` (and stores MiniZinc statistics when present).
- API key via env only; never in `run_config`.

**CLI:**

```
python -m ado_mzn check-minizinc
python -m ado_mzn run --seed data/seed_problems.md --config configs/default.yaml
```

### 5.1 Outcome taxonomy (unchanged)

| Bucket | Meaning |
|---|---|
| `COMPILE_ERROR` | Model rejected before solver |
| `SOLVER_ERROR` | Solver invoked then failed |
| `TIMEOUT / UNKNOWN` | Solver started; no qualifying result |
| `SATISFIED` / `OPTIMAL_SOLUTION` / `UNSATISFIABLE` | Valid termination |

### 5.2 `run_config` (required)

Write `runs/<id>/run_config.json` after MiniZinc probe, before LLM calls.

```json
{
  "run_id": "2026-09-15T120000Z",
  "started_at": "2026-09-15T12:00:00Z",
  "config_path": "configs/default.yaml",
  "seed_file": "data/seed_problems.md",
  "included_seed_ids": ["p01", "p02", "p03", "p04", "p05"],
  "protocol": {
    "generate_once_per_model": true,
    "models": ["cheap", "expensive"],
    "output": "single_mzn"
  },
  "llm_cheap": {
    "provider": "openai",
    "model_id": "gpt-4.1-nano",
    "temperature": 0.0,
    "max_tokens": 4096
  },
  "llm_expensive": {
    "provider": "openai",
    "model_id": "gpt-4.1",
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
    "wall_clock_s_per_seed": 300
  },
  "git_commit": "abc1234"
}
```

Never log API keys. `included_seed_ids` = complete seeds that actually ran.

---

## 6. Metrics (per seed × instance; both models)

| Metric | Source |
|---|---|
| **Compile** | outcome ≠ `COMPILE_ERROR` (per model) |
| **Solver success** | valid termination (per model) |
| **Solve time (s)** | wall-clock for `compile_and_solve` (per model) |
| **Faster** | cheaper wall time among both solver-success; else `NA` |
| **Objective** | parsed when solver provides it; note equal / differ / NA |
| **Human notes** | optional short comparison of the two `.mzn` files |

Report **per instance**, not a headline win-rate (small N). Solver success ≠ correct model.

Artefacts:

```
runs/<id>/<seed>/<instance>/cheap.mzn
runs/<id>/<seed>/<instance>/expensive.mzn
```

---

## 7. Seeds (NL only; 5 at freeze)

**File:** `data/seed_problems.md` — one `##` heading per problem. Headline N = **5** complete seeds (`p01`–`p05`).

- English (or other NL) only — **no** MiniZinc keywords.
- Optional English constraint inventory (C1, C2, …).
- **One or more** instance blocks under the same problem.

### Multiple instances

```markdown
### Instance i01
...numbers...

### Instance i02
...numbers...
```

Legacy heading `### Instance data` is treated as **`i01`**.

The harness expands each complete seed into **seed × instance** jobs. Each LLM call gets **only that problem + that instance**.

### Completeness (headline run)

- Clear decisions
- Constraints in prose and/or inventory
- SAT or min/max + quantity
- Numeric data in at least one instance (or in the problem prose)
- No MiniZinc in the seed text

### Split plan

Python splits `##` headings and instance blocks. The LLM never sees the whole file.

### Adding seeds

Append `## p0N` until you have **5** complete seeds; rerun. Each run creates a new `runs/<run_id>/`. At freeze, pick the headline run whose `included_seed_ids` is `p01`–`p05`.

---

## 8. Repo layout

```
ado_mzn/                 # agent, minizinc wrapper, eval, report
ado_mzn/toolchain/fixtures/smoke.mzn
data/seed_problems.md
configs/default.yaml
runs/<id>/run_config.json
runs/<id>/results.json
runs/<id>/<seed>/<instance>/{cheap,expensive}.mzn
reports/
prd.md
README.md
```

---

## 9. One-week plan

| Day | Do | Done when |
|---|---|---|
| **1** | MiniZinc + `check-minizinc`; dual-LLM config; runner skeleton | smoke ok; config has cheap+expensive |
| **2–3** | Finish **5** NL seeds (multi-instance where useful); parser | 5 complete headings |
| **4–5** | Full `run`; both models generate; timed solves; `results.json` | paired rows for included set |
| **6** | Human skim of `.mzn` pairs; draft report tables | notes + timing table |
| **7** | `reports/<id>.md` + README polish; freeze | tag v1 |

Slip buffer: drop incomplete seeds, not the dual-model timing core.

---

## 10. Done-when (v1)

- [ ] `check-minizinc` passes (no LLM).
- [ ] `run_config.json` records both `llm_cheap` and `llm_expensive` plus MiniZinc probe.
- [ ] Each included seed × instance has `cheap.mzn` and `expensive.mzn`.
- [ ] `results.json` has outcomes, solve times, and compare fields per pair.
- [ ] Report Method copied from `run_config`; per-instance comparison table.
- [ ] README: install, env, `check-minizinc`, `run`.
- [ ] Negative / mixed results acceptable.

---

## 11. Report outline

1. Question  
2. Method — models, MiniZinc version, Gecode, time limit, generate-once, N seeds / instances  
3. Seeds (ids + instance ids)  
4. Per-instance results (compile / solve / time / faster / objective)  
5. Encoding notes (brief human comparison)  
6. Limitations (small N, no gold MiniZinc, instance size may hide quality) and next step  

---

## 12. Risks

| Risk | What you do |
|---|---|
| MiniZinc missing | Day 1 `check-minizinc` |
| API cost | Cap N; cheap default `gpt-4.1-nano`, expensive `gpt-4.1` |
| Small instances → both finish in ms | Note in limitations; optional harder instances |
| Treating N as a win rate | Per-instance narrative |
| Scope creep | No repair, no LLM-as-judge, no gold `.mzn` |

---

## 13. Result record (minimum)

```json
{
  "seed_id": "p01",
  "instance_id": "i01",
  "cheap": {
    "mzn_path": "runs/<id>/p01/i01/cheap.mzn",
    "outcome": "OPTIMAL_SOLUTION",
    "compile_success": true,
    "solver_success": true,
    "objective": 42.0,
    "solve_time_s": 0.12,
    "diagnostics": ""
  },
  "expensive": {
    "mzn_path": "runs/<id>/p01/i01/expensive.mzn",
    "outcome": "OPTIMAL_SOLUTION",
    "compile_success": true,
    "solver_success": true,
    "objective": 42.0,
    "solve_time_s": 0.08,
    "diagnostics": ""
  },
  "compare": {
    "both_compile": true,
    "both_solver_success": true,
    "faster": "expensive",
    "solve_time_delta_s": 0.04,
    "objective_equal": true
  }
}
```

---

## 14. MiniZinc Python (contract)

```python
from datetime import timedelta
import minizinc

model = minizinc.Model(mzn_path)  # one file; data inlined; no .dzn in v1
inst = minizinc.Instance(minizinc.Solver.lookup("gecode"), model)
# wall-clock measured around solve; statistics retained when present
```

Pip package `minizinc` does **not** include the compiler. Install MiniZinc locally.

---

**Brief:** In one week, write **5** NL discrete optimisation seeds (optional multiple instances), generate MiniZinc with one cheap and one expensive LLM, solve both with the same Gecode settings, compare encodings and solve times, and ship `run_config.json` plus a short report.
