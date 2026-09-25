# Schema for the resolved experimental configuration written before any LLM call.

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from ado_mzn.toolchain.minizinc import (
    DEFAULT_SOLVER_ID,
    DEFAULT_TIME_LIMIT_S,
    ProbeInfo,
    probe,
)

PROMPT_GENERATE = "ado_mzn/agent/prompts.py#GENERATE_SYSTEM"


@dataclass(frozen=True)
class LlmConfig:
    provider: str
    model_id: str
    temperature: float
    max_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


@dataclass(frozen=True)
class ProtocolConfig:
    generate_once_per_model: bool
    models: tuple[str, ...]
    output: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "generate_once_per_model": self.generate_once_per_model,
            "models": list(self.models),
            "output": self.output,
        }


@dataclass(frozen=True)
class LimitsConfig:
    wall_clock_s_per_seed: int

    def to_dict(self) -> dict[str, Any]:
        return {"wall_clock_s_per_seed": self.wall_clock_s_per_seed}


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    started_at: str
    config_path: str
    seed_file: str
    included_seed_ids: tuple[str, ...]
    protocol: ProtocolConfig
    llm_cheap: LlmConfig
    llm_expensive: LlmConfig
    minizinc: ProbeInfo
    limits: LimitsConfig
    git_commit: Optional[str]
    prompt_templates: dict[str, str] = field(
        default_factory=lambda: {"generate": PROMPT_GENERATE}
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "config_path": self.config_path,
            "seed_file": self.seed_file,
            "included_seed_ids": list(self.included_seed_ids),
            "protocol": self.protocol.to_dict(),
            "llm_cheap": self.llm_cheap.to_dict(),
            "llm_expensive": self.llm_expensive.to_dict(),
            "minizinc": self.minizinc.to_dict(),
            "limits": self.limits.to_dict(),
            "git_commit": self.git_commit,
            "prompt_templates": dict(self.prompt_templates),
        }

    def write_json(self, path: Union[str, Path]) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        return out


def _git_commit_short() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _run_id_now() -> tuple[str, str]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    run_id = now.strftime("%Y-%m-%dT%H%M%SZ")
    started_at = now.isoformat().replace("+00:00", "Z")
    return run_id, started_at


def load_yaml_config(path: Union[str, Path]) -> dict[str, Any]:
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {config_path}")
    return data


def _parse_llm(raw: dict[str, Any], default_model: str) -> LlmConfig:
    return LlmConfig(
        provider=str(raw.get("provider", "openai")),
        model_id=str(raw.get("model_id", default_model)),
        temperature=float(raw.get("temperature", 0.0)),
        max_tokens=int(raw.get("max_tokens", 4096)),
    )


def build_run_config(
    config_path: Union[str, Path],
    seed_file: Union[str, Path],
    included_seed_ids: list[str],
) -> RunConfig:
    """Probe MiniZinc and merge yaml defaults into a resolved RunConfig."""
    config_path = Path(config_path)
    seed_file = Path(seed_file)
    raw = load_yaml_config(config_path)

    protocol_raw = raw.get("protocol") or {}
    minizinc_raw = raw.get("minizinc") or {}
    limits_raw = raw.get("limits") or {}

    # Back-compat: single `llm:` block becomes cheap if dual keys missing.
    cheap_raw = raw.get("llm_cheap") or raw.get("llm") or {}
    expensive_raw = raw.get("llm_expensive") or {}

    solver_id = str(minizinc_raw.get("solver_id", DEFAULT_SOLVER_ID))
    time_limit_s = int(minizinc_raw.get("time_limit_s", DEFAULT_TIME_LIMIT_S))
    probe_info = probe(solver_id=solver_id, time_limit_s=time_limit_s)

    models = tuple(
        str(x) for x in protocol_raw.get("models", ["cheap", "expensive"])
    )

    run_id, started_at = _run_id_now()
    return RunConfig(
        run_id=run_id,
        started_at=started_at,
        config_path=str(config_path),
        seed_file=str(seed_file),
        included_seed_ids=tuple(included_seed_ids),
        protocol=ProtocolConfig(
            generate_once_per_model=bool(
                protocol_raw.get("generate_once_per_model", True)
            ),
            models=models,
            output=str(protocol_raw.get("output", "single_mzn")),
        ),
        llm_cheap=_parse_llm(cheap_raw, "gpt-4.1-nano"),
        llm_expensive=_parse_llm(expensive_raw, "gpt-4.1"),
        minizinc=probe_info,
        limits=LimitsConfig(
            wall_clock_s_per_seed=int(limits_raw.get("wall_clock_s_per_seed", 300))
        ),
        git_commit=_git_commit_short(),
    )
