# Generate one .mzn per seed per model (cheap / expensive) from the natural-language problem.

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from ado_mzn.agent import prompts
from ado_mzn.schemas.seed import Seed

_FENCE_RE = re.compile(r"```(?P<lang>[A-Za-z0-9_+-]*)[^\n]*\n(?P<body>.*?)```", re.DOTALL)
_MZN_LANGS = {"minizinc", "mzn"}
_DATA_LANGS = {"dzn"}


class LLMError(RuntimeError):
    """The LLM call failed or returned no usable MiniZinc."""


@dataclass
class LLMResponse:
    """One LLM call. `model_id` is what the API reports, for run_config.json."""

    mzn: str
    raw_text: str
    model_id: Optional[str]
    response_id: Optional[str]
    duration_s: float
    usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "response_id": self.response_id,
            "duration_s": round(self.duration_s, 3),
            "usage": self.usage,
        }


def extract_mzn(text: str) -> str:
    """Pick the MiniZinc model out of the reply. Any .dzn block is ignored."""
    blocks = [(m["lang"].lower(), m["body"]) for m in _FENCE_RE.finditer(text)]
    for lang, body in blocks:
        if lang in _MZN_LANGS:
            return body.strip() + "\n"
    for lang, body in blocks:
        if lang not in _DATA_LANGS:
            return body.strip() + "\n"
    return text.strip() + "\n"


def make_client(timeout_s: float = 120) -> Any:
    if not os.environ.get("OPENAI_API_KEY"):
        raise LLMError("OPENAI_API_KEY is not set. Export it in your shell; never put it in a file.")
    from openai import OpenAI

    return OpenAI(timeout=timeout_s)


def call_llm(
    instructions: str,
    user_input: str,
    *,
    model_id: str,
    temperature: float,
    max_tokens: int,
    client: Any,
) -> LLMResponse:
    """One Responses API call."""
    started = time.monotonic()
    try:
        response = client.responses.create(
            model=model_id,
            instructions=instructions,
            input=user_input,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
    except Exception as exc:
        raise LLMError(f"LLM call failed ({model_id}): {exc}") from exc
    duration = time.monotonic() - started

    raw_text = getattr(response, "output_text", "") or ""
    if not raw_text.strip():
        raise LLMError(f"LLM returned an empty response ({model_id})")

    usage = getattr(response, "usage", None)
    return LLMResponse(
        mzn=extract_mzn(raw_text),
        raw_text=raw_text,
        model_id=getattr(response, "model", None),
        response_id=getattr(response, "id", None),
        duration_s=duration,
        usage=usage.model_dump() if hasattr(usage, "model_dump") else {},
    )


def generate_mzn(
    seed: Seed,
    seed_dir: Union[str, Path],
    label: str,
    *,
    model_id: str,
    temperature: float,
    max_tokens: int,
    client: Any,
) -> tuple[Path, LLMResponse]:
    """Generate once and save `<seed_dir>/<label>.mzn`. Refuses to overwrite."""
    seed_dir = Path(seed_dir)
    mzn_path = seed_dir / f"{label}.mzn"
    if mzn_path.exists():
        raise FileExistsError(f"{mzn_path} already exists; each model generates exactly once per seed")

    response = call_llm(
        prompts.GENERATE_INSTRUCTIONS,
        prompts.generate_input(seed.nl_text),
        model_id=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
        client=client,
    )

    seed_dir.mkdir(parents=True, exist_ok=True)
    mzn_path.write_text(response.mzn, encoding="utf-8")
    (seed_dir / f"{label}.raw.txt").write_text(response.raw_text, encoding="utf-8")
    return mzn_path, response
