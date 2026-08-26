# Agentic Discrete Optimisation — NL → MiniZinc

NL problems → LLM MiniZinc → MiniZinc oracle (compile/solve).

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

4. Check the toolchain (no LLM; run after install and before any agent work):

```bash
python -m ado_mzn check-minizinc
```

5. Run the agent (not implemented yet):

```bash
python -m ado_mzn run --seed data/seed_problems.md --config configs/default.yaml
```
