# Optional: repair was used in an earlier single-model protocol; not part of v1 dual compare.
# Kept for reference / future ablations only.

from ado_mzn.agent.generate import call_llm, extract_mzn
from ado_mzn.agent.prompts import build_repair_messages
from ado_mzn.schemas.run_config import LlmConfig


def repair_mzn(
    seed_nl: str,
    model_mzn: str,
    diagnostics: str,
    llm: LlmConfig,
) -> str:
    """Repair one .mzn using diagnostics and the original NL (unused in v1 run)."""
    messages = build_repair_messages(seed_nl, model_mzn, diagnostics)
    raw = call_llm(messages, llm)
    return extract_mzn(raw)
