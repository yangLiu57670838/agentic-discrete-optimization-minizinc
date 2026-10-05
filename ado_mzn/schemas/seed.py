# Parse data/seed_problems.md headings into NL seed records (no gold MiniZinc).

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

REQUIRED_SECTIONS = ("Problem", "Instance data", "Objective")

_HEADING_RE = re.compile(r"^##\s+(?P<id>\S+)\s+[—–-]\s+(?P<title>.+?)\s*$")
_SECTION_RE = re.compile(r"^###\s+(?P<name>.+?)\s*$")
_META_RE = re.compile(r"^-\s+(?P<key>[a-z_]+):\s*(?P<value>.+?)\s*$")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_CONSTRAINT_ID_RE = re.compile(r"^-\s+(C\d+):", re.MULTILINE)
_SENSE_RE = re.compile(r"sense:\s*(?P<sense>minimi[sz]e|maximi[sz]e)", re.IGNORECASE)

_MINIZINC_MARKERS = (
    re.compile(r"\bvar\s+(int|bool|float|set|\d)"),
    re.compile(r"\bsolve\s+(minimize|maximize|satisfy)\b"),
    re.compile(r"^\s*constraint\b", re.MULTILINE),
    re.compile(r"\barray\s*\["),
    re.compile(r'\binclude\s+"'),
)


class SeedError(ValueError):
    """Seed file is malformed or a seed fails the completeness test."""


@dataclass(frozen=True)
class Seed:
    """One natural-language problem. `nl_text` is exactly what the LLM sees."""

    id: str
    title: str
    family: Optional[str]
    type: Optional[str]
    sections: dict[str, str] = field(default_factory=dict)
    nl_text: str = ""

    @property
    def is_optimisation(self) -> bool:
        return (self.type or "").lower().startswith("optimi")

    @property
    def objective_sense(self) -> Optional[str]:
        """'minimize' / 'maximize' from `### Objective`, used to decide which objective is better."""
        match = _SENSE_RE.search(self.section("Objective"))
        return match["sense"].lower().replace("ise", "ize") if match else None

    @property
    def constraint_ids(self) -> list[str]:
        """Ids like C1, C2 from the optional `### Constraint inventory`."""
        return _CONSTRAINT_ID_RE.findall(self.section("Constraint inventory"))

    def section(self, name: str) -> str:
        return self.sections.get(name, "")


def _split_blocks(text: str) -> list[tuple[str, str, list[str]]]:
    blocks: list[tuple[str, str, list[str]]] = []
    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            blocks.append((match["id"], match["title"], []))
        elif blocks:
            blocks[-1][2].append(line)
    return blocks


def _parse_block(seed_id: str, title: str, lines: list[str]) -> Seed:
    meta: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    current: Optional[str] = None

    for line in lines:
        section = _SECTION_RE.match(line)
        if section:
            current = section["name"]
            sections[current] = []
            continue
        if current is None:
            meta_match = _META_RE.match(line.strip())
            if meta_match:
                meta[meta_match["key"]] = meta_match["value"]
            continue
        sections[current].append(line)

    meta_id = meta.get("id")
    if meta_id is not None and meta_id != seed_id:
        raise SeedError(f"{seed_id}: heading id does not match '- id: {meta_id}'")

    body = {name: "\n".join(text).strip() for name, text in sections.items()}
    nl_parts = [f"# {title}"]
    nl_parts += [f"## {name}\n\n{text}" for name, text in body.items() if text]

    return Seed(
        id=seed_id,
        title=title,
        family=meta.get("family"),
        type=meta.get("type"),
        sections=body,
        nl_text="\n\n".join(nl_parts) + "\n",
    )


def validate_seed(seed: Seed) -> None:
    """PRD §7 completeness test: required sections present, no MiniZinc in the NL."""
    missing = [name for name in REQUIRED_SECTIONS if not seed.section(name)]
    if missing:
        raise SeedError(f"{seed.id}: missing or empty sections: {', '.join(missing)}")
    for marker in _MINIZINC_MARKERS:
        found = marker.search(seed.nl_text)
        if found:
            raise SeedError(
                f"{seed.id}: seed contains MiniZinc syntax ({found.group(0)!r}); "
                "seeds must be natural language only"
            )


def parse_seeds(path: Union[str, Path]) -> list[Seed]:
    """Split the seed file on `## <id> — <title>` headings. One Seed per heading."""
    text = _COMMENT_RE.sub("", Path(path).read_text(encoding="utf-8"))
    seeds = [_parse_block(*block) for block in _split_blocks(text)]
    if not seeds:
        raise SeedError(f"No '## <id> — <title>' headings found in {path}")

    seen: set[str] = set()
    for seed in seeds:
        if seed.id in seen:
            raise SeedError(f"Duplicate seed id: {seed.id}")
        seen.add(seed.id)
        validate_seed(seed)
    return seeds
