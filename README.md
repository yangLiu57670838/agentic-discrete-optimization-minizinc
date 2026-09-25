# Cheap vs expensive LLM — NL → MiniZinc comparison

5 NL discrete optimisation seeds → two models each write `.mzn` → same MiniZinc solver → compare encodings and solve time → report.

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

5. Set your OpenAI API key, then run the dual-model experiment:

```bash
export OPENAI_API_KEY=your-key-here
python -m ado_mzn run --seed data/seed_problems.md --config configs/default.yaml
```

Default models (edit `configs/default.yaml`):

- **cheap:** `gpt-4.1-nano`
- **expensive:** `gpt-4.1`
- **solver:** Gecode, same `time_limit_s` for both

6. Rebuild a report from an existing run (optional):

```bash
python -m ado_mzn report runs/<run_id>
```

Outputs: `runs/<run_id>/` (`cheap.mzn` / `expensive.mzn` per seed×instance, `results.json`) and `reports/<run_id>.md`.
