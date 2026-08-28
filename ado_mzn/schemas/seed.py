# Parse data/seed_problems.md headings into NL seed records (no gold MiniZinc).

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

# Completeness / hygiene: reject seeds that already look like MiniZinc.
_MINIZINC_MARKERS = (
    "var int",
    "var bool",
    "constraint ",
    "solve satisfy",
    "solve minimize",
    "solve maximize",
    "include \"",
)

_HEADING_RE = re.compile(
    r"^##\s+(?P<title>.+?)\s*$",
    re.MULTILINE,
)
_META_RE = re.compile(
    r"^-\s*(?P<key>id|family|type)\s*:\s*(?P<value>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_SECTION_RE = re.compile(
    r"^###\s+(?P<name>.+?)\s*$",
    re.MULTILINE,
)
_CONSTRAINT_RE = re.compile(
    r"^-\s*(?P<cid>C\d+)\s*:\s*(?P<text>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_OBJECTIVE_FIELD_RE = re.compile(
    r"^-\s*(?P<key>sense|quantity)\s*:\s*(?P<value>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_HAS_DIGIT_RE = re.compile(r"\d")


@dataclass(frozen=True)
class SeedObjective:
    """SAT or optimisation goal from the seed (plain English)."""

    sense: str
    quantity: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {"sense": self.sense, "quantity": self.quantity}


@dataclass(frozen=True)
class Seed:
    """One NL problem from a ## heading. No MiniZinc."""

    id: str
    title: str
    family: str
    type: str
    problem: str
    instance_data: str = ""
    constraints: dict[str, str] = field(default_factory=dict)
    objective: Optional[SeedObjective] = None
    raw_heading: str = ""

    @property
    def is_complete(self) -> bool:
        """PRD completeness test for the headline run."""
        if not self.id or not self.problem.strip():
            return False
        if self._contains_minizinc(self.problem) or self._contains_minizinc(
            self.instance_data
        ):
            return False
        if self._contains_minizinc(" ".join(self.constraints.values())):
            return False
        has_constraints = bool(self.constraints) or self._mentions_rules(
            self.problem
        )
        if not has_constraints:
            return False
        if self.objective is None or not self.objective.sense.strip():
            return False
        sense = self.objective.sense.strip().lower()
        if sense in {"minimize", "minimise", "maximize", "maximise"}:
            if not (self.objective.quantity or "").strip():
                return False
        elif sense not in {"satisfy", "satisfaction", "sat"}:
            return False
        if not self._has_numeric_data():
            return False
        return True

    def nl_for_prompt(self) -> str:
        """Single-seed NL text for LLM generate/repair (no other seeds)."""
        lines = [
            f"# {self.id} — {self.title}",
            f"- id: {self.id}",
            f"- family: {self.family}",
            f"- type: {self.type}",
            "",
            "### Problem",
            "",
            self.problem.strip(),
        ]
        if self.instance_data.strip():
            lines.extend(["", "### Instance data", "", self.instance_data.strip()])
        if self.constraints:
            lines.extend(["", "### Constraint inventory", ""])
            for cid in sorted(self.constraints, key=_constraint_sort_key):
                lines.append(f"- {cid}: {self.constraints[cid]}")
        if self.objective is not None:
            lines.extend(
                [
                    "",
                    "### Objective",
                    f"- sense: {self.objective.sense}",
                ]
            )
            if self.objective.quantity:
                lines.append(f"- quantity: {self.objective.quantity}")
        return "\n".join(lines).strip() + "\n"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "family": self.family,
            "type": self.type,
            "problem": self.problem,
            "instance_data": self.instance_data,
            "constraints": dict(self.constraints),
            "objective": None
            if self.objective is None
            else self.objective.to_dict(),
            "is_complete": self.is_complete,
        }

    def _has_numeric_data(self) -> bool:
        if _HAS_DIGIT_RE.search(self.instance_data):
            return True
        return bool(_HAS_DIGIT_RE.search(self.problem))

    @staticmethod
    def _contains_minizinc(text: str) -> bool:
        lower = text.lower()
        return any(marker in lower for marker in _MINIZINC_MARKERS)

    @staticmethod
    def _mentions_rules(problem: str) -> bool:
        # Fallback when optional Constraint inventory is omitted.
        lower = problem.lower()
        cues = ("must ", "cannot ", "at most", "at least", "each ", "every ")
        return any(cue in lower for cue in cues)


def _constraint_sort_key(cid: str) -> tuple[int, str]:
    match = re.match(r"C(\d+)$", cid, re.IGNORECASE)
    if match:
        return (int(match.group(1)), cid.upper())
    return (10**9, cid.upper())


def _split_heading_blocks(text: str) -> list[tuple[str, str]]:
    """Return (heading_title, body) for each ## section."""
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return []
    blocks: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        title = match.group("title").strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip("\n")
        blocks.append((title, body))
    return blocks


# parse the sections of the body in
def _parse_sections(body: str) -> dict[str, str]:
    matches = list(_SECTION_RE.finditer(body))
    if not matches:
        return {}
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        name = match.group("name").strip().lower()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[name] = body[start:end].strip()
    return sections


def _parse_meta(body: str) -> dict[str, str]:
    # Metadata bullets sit before the first ### section.
    first_section = _SECTION_RE.search(body)
    header = body[: first_section.start()] if first_section else body
    meta: dict[str, str] = {}
    for match in _META_RE.finditer(header):
        meta[match.group("key").lower()] = match.group("value").strip()
    return meta


def _parse_constraints(section: str) -> dict[str, str]:
    constraints: dict[str, str] = {}
    for match in _CONSTRAINT_RE.finditer(section):
        cid = match.group("cid").upper()
        constraints[cid] = match.group("text").strip()
    return constraints


def _parse_objective(section: str) -> Optional[SeedObjective]:
    fields: dict[str, str] = {}
    for match in _OBJECTIVE_FIELD_RE.finditer(section):
        fields[match.group("key").lower()] = match.group("value").strip()
    sense = fields.get("sense")
    if not sense:
        return None
    return SeedObjective(sense=sense, quantity=fields.get("quantity"))


def _title_id_fallback(title: str) -> str:
    # "## p01 — PowerGen ..." → p01
    token = title.split("—", 1)[0].split("-", 1)[0].strip()
    return token or title.strip()


def parse_seed_block(title: str, body: str) -> Seed:
    """Parse one ## heading body into a Seed (may be incomplete)."""
    meta = _parse_meta(body)
    sections = _parse_sections(body)

    problem = sections.get("problem", "").strip()
    instance_data = sections.get("instance data", "").strip()
    constraints = _parse_constraints(sections.get("constraint inventory", ""))
    objective = _parse_objective(sections.get("objective", ""))

    seed_id = meta.get("id") or _title_id_fallback(title)
    display_title = title
    if "—" in title:
        display_title = title.split("—", 1)[1].strip()
    elif " - " in title:
        display_title = title.split(" - ", 1)[1].strip()

    return Seed(
        id=seed_id,
        title=display_title,
        family=meta.get("family", ""),
        type=meta.get("type", ""),
        problem=problem,
        instance_data=instance_data,
        constraints=constraints,
        objective=objective,
        raw_heading=title,
    )


def parse_seed_markdown(text: str) -> list[Seed]:
    """Parse all ## seeds from markdown text (complete and incomplete)."""
    seeds: list[Seed] = []
    for title, body in _split_heading_blocks(text):
        seeds.append(parse_seed_block(title, body)) # split 
    return seeds


def load_seeds(
    path: Union[str, Path],
    *,
    complete_only: bool = True,
) -> list[Seed]:
    """Load seeds from seed_problems.md.

    By default returns only complete seeds (headline run). Pass
    complete_only=False to inspect incomplete drafts too.
    """
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    seeds = parse_seed_markdown(text)
    if complete_only:
        return [seed for seed in seeds if seed.is_complete]
    return seeds


def default_seed_path() -> Path:
    """Repo-relative default: data/seed_problems.md."""
    return Path(__file__).resolve().parents[2] / "data" / "seed_problems.md"
