# Schema for the resolved experimental configuration written before any LLM call.

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import yaml

MODEL_LABELS = ("cheap", "expensive")


class ConfigError(ValueError):
    """configs/*.yaml is missing a required field."""


@dataclass(frozen=True)
class ModelSpec:
    label: str
    provider: str
    model_id: str


@dataclass(frozen=True)
class Settings:
    """Requested values from the YAML. What actually ran goes in run_config.json."""

    config_path: str
    models: tuple[ModelSpec, ...]
    temperature: float
    max_tokens: int
    llm_timeout_s: int
    solver_id: str
    time_limit_s: int
    runs_dir: Path
    reports_dir: Path


def load_settings(path: Union[str, Path]) -> Settings:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    models_raw = raw.get("models") or {}
    missing = [label for label in MODEL_LABELS if label not in models_raw]
    if missing:
        raise ConfigError(f"{path}: models must define {', '.join(MODEL_LABELS)}; missing {missing}")

    models = []
    for label in MODEL_LABELS:
        entry = models_raw[label] or {}
        if not entry.get("model_id"):
            raise ConfigError(f"{path}: models.{label}.model_id is required")
        models.append(
            ModelSpec(label=label, provider=entry.get("provider", "openai"), model_id=entry["model_id"])
        )

    llm = raw.get("llm") or {}
    mzn = raw.get("minizinc") or {}
    paths = raw.get("paths") or {}
    return Settings(
        config_path=str(path),
        models=tuple(models),
        temperature=float(llm.get("temperature", 0.0)),
        max_tokens=int(llm.get("max_tokens", 4096)),
        llm_timeout_s=int(llm.get("timeout_s", 120)),
        solver_id=str(mzn.get("solver_id", "gecode")),
        time_limit_s=int(mzn.get("time_limit_s", 10)),
        runs_dir=Path(paths.get("runs_dir", "runs")),
        reports_dir=Path(paths.get("reports_dir", "reports")),
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_run_id(now: Optional[datetime] = None) -> str:
    return (now or utc_now()).strftime("%Y-%m-%dT%H%M%SZ")


def git_state() -> dict[str, Any]:
    def git(*args: str) -> Optional[str]:
        try:
            out = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
        except (OSError, subprocess.CalledProcessError):
            return None
        return out.stdout.strip()

    commit = git("rev-parse", "--short", "HEAD")
    status = git("status", "--porcelain")
    return {"commit": commit, "dirty": bool(status) if status is not None else None}


def build_run_config(
    settings: Settings,
    *,
    run_id: str,
    started_at: datetime,
    seed_file: str,
    seed_ids: list[str],
    minizinc_info: dict[str, Any],
    prompt_sha256: dict[str, str],
) -> dict[str, Any]:
    """`resolved_model_id` stays null until the API answers; the runner fills it in."""
    return {
        "run_id": run_id,
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "config_path": settings.config_path,
        "seed_file": seed_file,
        "included_seed_ids": seed_ids,
        "protocol": {
            "generate_once_per_model": True,
            "repair": False,
            "output": "single_mzn",
            "same_prompt_for_all_models": True,
        },
        "models": {
            spec.label: {
                "provider": spec.provider,
                "requested_model_id": spec.model_id,
                "resolved_model_id": None,
            }
            for spec in settings.models
        },
        "llm": {
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens,
            "timeout_s": settings.llm_timeout_s,
        },
        "prompts_sha256": prompt_sha256,
        "minizinc": minizinc_info,
        "git": git_state(),
    }


def write_json(path: Union[str, Path], data: Any) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    path.write_text(text + "\n", encoding="utf-8")
    return path


def read_json(path: Union[str, Path]) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
