# Generate prompt template (NL only; never MiniZinc gold). Identical for cheap and expensive models.

from __future__ import annotations

import hashlib

GENERATE_INSTRUCTIONS = """\
Write a MiniZinc model for the problem the user describes.

Output rules:
- Return exactly one complete MiniZinc model in a single ```minizinc code block.
- Put all data (sets, parameters, numbers) directly in that model. Do not use a .dzn file or include data files.
- The model must contain a solve item.
- Do not write anything outside the code block.
"""

GENERATE_INPUT = """\
Problem:

{nl_text}"""


def generate_input(nl_text: str) -> str:
    return GENERATE_INPUT.format(nl_text=nl_text.strip())


def template_sha256() -> dict[str, str]:
    """Hash for run_config.json so a report can prove which prompt ran."""
    text = GENERATE_INSTRUCTIONS + GENERATE_INPUT
    return {"generate": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]}
