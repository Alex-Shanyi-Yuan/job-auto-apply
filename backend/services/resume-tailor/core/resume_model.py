"""Structured resume content model.

This replaces the old "LLM emits a full LaTeX document" approach. The resume is
represented as validated, constrained data (`ResumeContent`); the LLM only ever
produces/selects this structure, and `core/resume_renderer.py` deterministically
renders it to LaTeX. That makes output always-compilable and ATS-clean, and lets
us validate the model instead of regex-sniffing an LLM blob.

The shape mirrors `data/master.tex` (the Jake-Gutierrez template) 1:1 so the
Jinja2 template can map fields directly onto the existing `\\resume*` commands.
"""

from __future__ import annotations

from typing import Annotated, List, Optional

from pydantic import BaseModel, Field, StringConstraints

# Constrained string types for list items, so the LLM can't return empty or
# rambling entries (plain `List[str]` does not constrain the items themselves).
Bullet = Annotated[str, StringConstraints(min_length=1, max_length=400)]
ShortItem = Annotated[str, StringConstraints(min_length=1, max_length=80)]


class Link(BaseModel):
    """A labelled hyperlink shown in the resume header (LinkedIn, GitHub, ...)."""

    label: str = Field(..., min_length=1, max_length=120)
    url: str = Field(..., min_length=1, max_length=300)


class Header(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=40)
    email: Optional[str] = Field(default=None, max_length=120)
    links: List[Link] = Field(default_factory=list, max_length=6)
    citizenship: Optional[str] = Field(default=None, max_length=200)


class EducationEntry(BaseModel):
    institution: str = Field(..., min_length=1, max_length=160)
    location: str = Field(default="", max_length=120)
    degree: str = Field(..., min_length=1, max_length=200)
    dates: str = Field(default="", max_length=80)
    highlights: List[Bullet] = Field(default_factory=list, max_length=6)


class SkillGroup(BaseModel):
    category: str = Field(..., min_length=1, max_length=80)
    items: List[ShortItem] = Field(..., min_length=1, max_length=40)


class Role(BaseModel):
    """A single title/date row. One company may have several (e.g. intern -> contract)."""

    title: str = Field(..., min_length=1, max_length=160)
    dates: str = Field(default="", max_length=80)


class ExperienceEntry(BaseModel):
    company: str = Field(..., min_length=1, max_length=160)
    location: str = Field(default="", max_length=120)
    roles: List[Role] = Field(..., min_length=1, max_length=4)
    bullets: List[Bullet] = Field(default_factory=list, max_length=10)


class ProjectEntry(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    tech: List[ShortItem] = Field(default_factory=list, max_length=15)
    bullets: List[Bullet] = Field(default_factory=list, max_length=8)
    link: Optional[str] = Field(default=None, max_length=300)


class ResumeContent(BaseModel):
    """A complete resume as structured data.

    During tailoring the LLM receives the full pool (all experiences/projects) and
    returns a tailored `ResumeContent` containing the most relevant subset, reworded
    to mirror the target job's keywords and trimmed to roughly one page.
    """

    header: Header
    education: List[EducationEntry] = Field(default_factory=list, max_length=5)
    skills: List[SkillGroup] = Field(default_factory=list, max_length=8)
    summary: Optional[str] = Field(default=None, max_length=800)
    experience: List[ExperienceEntry] = Field(default_factory=list, max_length=10)
    projects: List[ProjectEntry] = Field(default_factory=list, max_length=20)

    def to_plain_text(self) -> str:
        """Flatten to plain text for the scoring agent (one source of truth)."""
        lines: List[str] = [self.header.name]
        if self.summary:
            lines.append(self.summary)

        if self.skills:
            lines.append("Skills:")
            for group in self.skills:
                lines.append(f"  {group.category}: {', '.join(group.items)}")

        if self.experience:
            lines.append("Experience:")
            for exp in self.experience:
                titles = " / ".join(r.title for r in exp.roles)
                lines.append(f"  {titles} — {exp.company} ({exp.location})")
                lines.extend(f"    - {b}" for b in exp.bullets)

        if self.projects:
            lines.append("Projects:")
            for proj in self.projects:
                tech = f" [{', '.join(proj.tech)}]" if proj.tech else ""
                lines.append(f"  {proj.name}{tech}")
                lines.extend(f"    - {b}" for b in proj.bullets)

        if self.education:
            lines.append("Education:")
            for edu in self.education:
                lines.append(f"  {edu.degree} — {edu.institution} ({edu.dates})")

        return "\n".join(lines)
