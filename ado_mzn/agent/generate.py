# Generate attempt_0.mzn exactly once per seed from the natural-language problem.

from __future__ import annotations

import os
import re
from typing import Optional

from ado_mzn.agent.prompts import build_generate_messages
from ado_mzn.schemas.run_config import LlmConfig

_CODE_FENCE_RE = re.compile(
    r"```(?:minizinc|mzn)?\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


class LlmError(RuntimeError):
    """LLM call or response extraction failed."""


def extract_mzn(text: str) -> str:
    """Pull MiniZinc source from a fenced or plain LLM response."""
    match = _CODE_FENCE_RE.search(text)
    if match:
        return match.group(1).strip() + "\n"
    stripped = text.strip()
    if not stripped:
        raise LlmError("LLM returned empty MiniZinc content")
    return stripped + "\n"


def _openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LlmError(
            "OpenAI package is not installed. pip install openai"
        ) from exc
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LlmError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)

# for this simple project, we will use the openai Responses API to call the LLM
def call_llm(messages: list[dict[str, str]], llm: LlmConfig) -> str:
    if llm.provider != "openai":
        raise LlmError(f"Unsupported LLM provider: {llm.provider}")

    client = _openai_client()
    instructions = None
    input_messages: list[dict[str, str]] = []
    for message in messages:
        if message.get("role") == "system" and instructions is None:
            instructions = message.get("content")
        else:
            input_messages.append(message)

    try:
        kwargs: dict = {
            "model": llm.model_id,
            "input": input_messages or messages,
            "temperature": llm.temperature,  # 0 for more deterministic research runs
            "max_output_tokens": llm.max_tokens,  # cost / length cap
        }
        if instructions:
            kwargs["instructions"] = instructions
        response = client.responses.create(**kwargs)
    except Exception as exc:
        raise LlmError(f"OpenAI API call failed: {exc}") from exc

    content = getattr(response, "output_text", None)
    if not content:
        raise LlmError("OpenAI returned no message content")
    return content


def generate_mzn(seed_nl: str, llm: LlmConfig) -> str:
    """Generate one executable .mzn from a single seed's NL."""
    messages = build_generate_messages(seed_nl)
    raw = call_llm(messages, llm)
    return extract_mzn(raw)
