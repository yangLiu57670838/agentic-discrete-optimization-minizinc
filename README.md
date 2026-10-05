# Agentic Discrete Optimisation — NL → MiniZinc, cheap vs expensive LLM

Same NL problem + same prompt → a cheap and an expensive LLM each write one MiniZinc model → same solver and time limit → compare outcome, objective, speed, and faithfulness.

Default models (edit `configs/default.yaml`): cheap `gpt-4.1-nano`, expensive `gpt-4.1`. Solver: Gecode, 10s.

## Steps

1. Install [MiniZinc](https://www.minizinc.org/downloads/) (`minizinc` on `PATH`, or set `MINIZINC_DIR`).

2. Create and activate a venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install Python deps:

```bash
pip install -r requirements.txt
```

4. Check the toolchain (no LLM):

```bash
python -m ado_mzn check-minizinc
```

5. Set your OpenAI key (shell only; never commit it):

```bash
export OPENAI_API_KEY=your-key-here
```

6. Run both models on the seeds in `data/seed_problems.md`:

```bash
python -m ado_mzn run --seed data/seed_problems.md --config configs/default.yaml
```

Writes `runs/<run_id>/` (`run_config.json`, `results.json`, `review.yaml`, `<seed>/cheap.mzn`, `<seed>/expensive.mzn`) and `reports/<run_id>.md`.

7. Review: read each seed's NL and both `.mzn` files, fill `runs/<run_id>/review.yaml`.

8. Re-render the report with your review:

```bash
python -m ado_mzn report runs/<run_id>
```
