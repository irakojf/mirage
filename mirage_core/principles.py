"""Principles parser and thinking mode selection.

Parses knowledge/principles.md into structured rules that drive
reasoning in prioritize, plan, review, and capture workflows.

Expected markdown format:
    ## Section Name          → becomes a PrincipleSection
    **"Quoted text"**        → extracted as a core_quote
    - Bullet point           → extracted as a tactic
    1. Numbered item         → extracted as a step/question
    > Block quote            → extracted as a quote

The "Application for Mirage" section is parsed specially as decision
filters used by the core engine.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

DEFAULT_PRINCIPLES_PATH = Path(__file__).parent.parent / "knowledge" / "principles.md"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PrincipleSection:
    """A parsed section from principles.md."""

    heading: str
    body: str
    quotes: tuple[str, ...] = ()
    tactics: tuple[str, ...] = ()
    questions: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionFilter:
    """A filter from the 'Application for Mirage' section."""

    name: str
    description: str


@dataclass(frozen=True)
class PrinciplesIndex:
    """Fully parsed principles file."""

    sections: tuple[PrincipleSection, ...]
    decision_filters: tuple[DecisionFilter, ...]
    content_hash: str

    def get_section(self, heading: str) -> Optional[PrincipleSection]:
        """Find a section by heading (case-insensitive substring match)."""
        needle = heading.lower()
        for section in self.sections:
            if needle in section.heading.lower():
                return section
        return None

    @property
    def required_sections(self) -> tuple[str, ...]:
        return (
            "Core Philosophy",
            "The Four Laws",
            "Identity-Based Habits",
            "The 2-Minute Rule",
            "Never Miss Twice",
            "Application for Mirage",
        )

    def validate(self) -> list[str]:
        """Return list of missing required sections."""
        missing = []
        for req in self.required_sections:
            if self.get_section(req) is None:
                missing.append(req)
        return missing


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_BOLD_QUOTE_RE = re.compile(r'\*\*"([^"]+)"\*\*')
_NUMBERED_RE = re.compile(r"^\d+\.\s+(.+)", re.MULTILINE)
_BULLET_RE = re.compile(r"^[-*•]\s+(.+)", re.MULTILINE)
_DECISION_FILTER_RE = re.compile(
    r"^\d+\.\s+\*\*([^*]+)\*\*\s*[—–-]\s*(.+)", re.MULTILINE
)


def parse_principles(text: str) -> PrinciplesIndex:
    """Parse raw markdown into a PrinciplesIndex."""
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

    sections: list[PrincipleSection] = []
    decision_filters: list[DecisionFilter] = []

    # Split into sections by ## headings
    raw_sections = _split_sections(text)

    for heading, body in raw_sections:
        if "application for mirage" in heading.lower():
            decision_filters = _parse_decision_filters(body)

        quotes = tuple(_BOLD_QUOTE_RE.findall(body))
        tactics = tuple(m.group(1) for m in _BULLET_RE.finditer(body))
        questions = tuple(m.group(1) for m in _NUMBERED_RE.finditer(body))

        # Also extract blockquote content
        block_quotes = tuple(
            line.lstrip("> ").strip()
            for line in body.splitlines()
            if line.strip().startswith(">")
        )
        all_quotes = quotes + block_quotes

        sections.append(
            PrincipleSection(
                heading=heading,
                body=body.strip(),
                quotes=all_quotes,
                tactics=tactics,
                questions=questions,
            )
        )

    return PrinciplesIndex(
        sections=tuple(sections),
        decision_filters=tuple(decision_filters),
        content_hash=content_hash,
    )


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) pairs by ## headings."""
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_heading:
                sections.append((current_heading, "\n".join(current_lines)))
            current_heading = line[3:].strip()
            current_lines = []
        elif current_heading:
            current_lines.append(line)

    if current_heading:
        sections.append((current_heading, "\n".join(current_lines)))

    return sections


def _parse_decision_filters(body: str) -> list[DecisionFilter]:
    """Parse the 'Application for Mirage' numbered list."""
    filters = []
    for match in _DECISION_FILTER_RE.finditer(body):
        filters.append(DecisionFilter(name=match.group(1).strip(), description=match.group(2).strip()))
    return filters


def load_principles(path: Path = DEFAULT_PRINCIPLES_PATH) -> PrinciplesIndex:
    """Load and parse principles from file."""
    text = path.read_text(encoding="utf-8")
    return parse_principles(text)


# ---------------------------------------------------------------------------
# Session cache
# ---------------------------------------------------------------------------

_cached_index: Optional[PrinciplesIndex] = None
_cached_hash: Optional[str] = None


def get_principles(path: Path = DEFAULT_PRINCIPLES_PATH) -> PrinciplesIndex:
    """Load principles with session-level caching. Reloads on file change."""
    global _cached_index, _cached_hash

    text = path.read_text(encoding="utf-8")
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

    if _cached_index is not None and _cached_hash == content_hash:
        return _cached_index

    _cached_index = parse_principles(text)
    _cached_hash = content_hash
    return _cached_index


def clear_cache() -> None:
    """Force reload on next access."""
    global _cached_index, _cached_hash
    _cached_index = None
    _cached_hash = None


# ---------------------------------------------------------------------------
# Thinking mode selection
# ---------------------------------------------------------------------------

class ThinkingMode:
    """Selects which principles to inject based on workflow context."""

    CAPTURE = "capture"
    PRIORITIZE = "prioritize"
    REVIEW = "review"
    PLAN = "plan"

    # Maps workflow → relevant principle sections
    SECTION_MAP: dict[str, tuple[str, ...]] = {
        CAPTURE: (
            "The 2-Minute Rule",
            "Identity-Based Habits",
            "Application for Mirage",
        ),
        PRIORITIZE: (
            "Keystone Habits",
            "Never Miss Twice",
            "The Compound Effect",
            "Application for Mirage",
        ),
        REVIEW: (
            "Questions for Annual Review",
            "The Compound Effect",
            "Tracking and Measurement",
            "Core Philosophy",
        ),
        PLAN: (
            "Environment Design",
            "Habit Stacking",
            "Practical Tactics",
            "The Four Laws",
        ),
    }

    @classmethod
    def get_context(
        cls, workflow: str, index: Optional[PrinciplesIndex] = None
    ) -> str:
        """Build a principles context string for a given workflow.

        Returns a compact markdown summary of relevant sections
        suitable for injecting into an LLM system prompt.
        """
        if index is None:
            index = get_principles()

        section_names = cls.SECTION_MAP.get(workflow, cls.SECTION_MAP[cls.CAPTURE])
        parts: list[str] = []

        # Always include decision filters
        if index.decision_filters:
            filters_text = "\n".join(
                f"- **{f.name}**: {f.description}" for f in index.decision_filters
            )
            parts.append(f"## Decision Filters\n{filters_text}")

        for name in section_names:
            section = index.get_section(name)
            if section is None:
                continue

            lines = [f"## {section.heading}"]
            if section.quotes:
                lines.append(f'> "{section.quotes[0]}"')
            if section.tactics:
                for t in section.tactics[:5]:
                    lines.append(f"- {t}")
            if section.questions:
                for q in section.questions[:5]:
                    lines.append(f"- {q}")
            parts.append("\n".join(lines))

        return "\n\n".join(parts)
