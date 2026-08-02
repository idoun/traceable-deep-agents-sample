from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

from traceable_deep_agents_sample.complexity_router import ComplexityDecision


@dataclass(frozen=True)
class SkillRef:
    """Portable Agent Skill reference loaded for a run."""

    skill_id: str
    name: str
    version: str
    path: str
    hash: str
    reason: str


class SkillRegistry:
    """Read-only registry for portable `SKILL.md` folders."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parent / "skills"

    def list_skill_ids(self) -> list[str]:
        return [path.parent.name for path in sorted(self.root.glob("*/SKILL.md"))]

    def select(self, *, user_input: str, decision: ComplexityDecision) -> list[SkillRef]:
        selected: list[SkillRef] = []
        if _asks_for_freshness(user_input):
            selected.append(self._load("daily-news-freshness", reason="freshness-sensitive news request"))
        if decision.route == "deep":
            selected.append(self._load("tech-trend-briefing", reason="deep candidate needs synthesis guidance"))
        return _dedupe(selected)

    def _load(self, skill_id: str, *, reason: str) -> SkillRef:
        skill_path = self.root / skill_id / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        return SkillRef(
            skill_id=skill_id,
            name=_first_heading(content) or skill_id,
            version=_frontmatter_value(content, "version") or "unversioned",
            path=str(skill_path.relative_to(self.root.parent.parent.parent)),
            hash=f"sha256:{sha256(content.encode('utf-8')).hexdigest()}",
            reason=reason,
        )


def _asks_for_freshness(user_input: str) -> bool:
    lowered = user_input.lower()
    return ("오늘" in user_input or "today" in lowered or "최신" in user_input or "latest" in lowered) and (
        "뉴스" in user_input or "news" in lowered
    )


def _first_heading(content: str) -> str | None:
    for line in content.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return None


def _frontmatter_value(content: str, key: Literal["version"]) -> str | None:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"')
    return None


def _dedupe(skills: list[SkillRef]) -> list[SkillRef]:
    seen: set[str] = set()
    unique: list[SkillRef] = []
    for skill in skills:
        if skill.skill_id in seen:
            continue
        seen.add(skill.skill_id)
        unique.append(skill)
    return unique
