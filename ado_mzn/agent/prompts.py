# Generate and repair prompt templates (NL only; never MiniZinc gold).

from __future__ import annotations

# system prompt avoid too much details and tricks for minizinc, so can compare 2 models naturally
GENERATE_SYSTEM = """You translate natural-language discrete optimisation problems into executable MiniZinc.

Rules:
- Output exactly one complete MiniZinc model in a single code block.
- Inline all numeric data from the problem; do not reference or emit a separate .dzn file.
- Include decision variables, parameters/data, constraints, and a solve statement.
- Match the stated objective sense (minimize, maximize, or satisfy).
- Do not add commentary outside the code block."""

GENERATE_USER = """Write one executable MiniZinc model for this problem.

{seed_nl}"""

REPAIR_SYSTEM = """You repair an existing MiniZinc model using compiler/solver diagnostics.

Rules:
- Keep the same problem intent as the original natural-language specification.
- Output exactly one complete MiniZinc model in a single code block.
- Inline all numeric data; do not reference or emit a separate .dzn file.
- Fix compile/solver errors without dropping stated constraints unless necessary for executability.
- Do not add commentary outside the code block."""

REPAIR_USER = """Repair this MiniZinc model.

Original natural-language problem:
{seed_nl}

Current MiniZinc model:
```minizinc
{model_mzn}
```

Diagnostics:
{diagnostics}

Return the full corrected .mzn."""


def build_generate_messages(seed_nl: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": GENERATE_SYSTEM},
        {"role": "user", "content": GENERATE_USER.format(seed_nl=seed_nl.strip())},
    ]


def build_repair_messages(
    seed_nl: str,
    model_mzn: str,
    diagnostics: str,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": REPAIR_SYSTEM},
        {
            "role": "user",
            "content": REPAIR_USER.format(
                seed_nl=seed_nl.strip(),
                model_mzn=model_mzn.strip(),
                diagnostics=diagnostics.strip() or "(no diagnostics)",
            ),
        },
    ]
