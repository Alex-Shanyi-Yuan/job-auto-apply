"""Deterministic LaTeX rendering of a :class:`ResumeContent`.

The LLM never emits LaTeX. It produces a validated ``ResumeContent``; this module
renders it through a fixed Jinja2 template (``data/resume_template.tex.j2``) with
every interpolated value LaTeX-escaped. That makes the output always compilable
and ATS-clean, eliminating the unbalanced-brace / unescaped-character failure
class of the old "ask the LLM for raw LaTeX" approach.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .resume_model import ResumeContent

# Template lives next to the master resume data.
_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "data"
_TEMPLATE_NAME = "resume_template.tex.j2"


_LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# Single-pass regex so replacements (e.g. the braces in \textbackslash{}) are not
# themselves re-escaped.
_LATEX_PATTERN = re.compile("|".join(re.escape(c) for c in _LATEX_REPLACEMENTS))


def latex_escape(value) -> str:
    """Escape LaTeX special characters in arbitrary text."""
    if value is None:
        return ""
    return _LATEX_PATTERN.sub(lambda m: _LATEX_REPLACEMENTS[m.group()], str(value))


def latex_escape_url(value) -> str:
    """Escape only the characters that break a URL inside ``\\href``.

    Backslashes are not escaped (they don't appear in real URLs and would corrupt
    the link); ``%`` and ``#`` are the characters LaTeX would otherwise eat.
    """
    if value is None:
        return ""
    return str(value).replace("\\", "").replace("%", r"\%").replace("#", r"\#")


@lru_cache(maxsize=1)
def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        # LaTeX-safe delimiters so the template stays readable and doesn't clash
        # with LaTeX's own {} and {{ }}.
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<#",
        comment_end_string="#>",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
        undefined=StrictUndefined,
    )
    env.filters["tex"] = latex_escape
    env.filters["texurl"] = latex_escape_url
    return env


def render_resume(content: ResumeContent) -> str:
    """Render a ``ResumeContent`` to a complete LaTeX document string."""
    template = _environment().get_template(_TEMPLATE_NAME)
    rendered = template.render(r=content)
    # Normalise trailing whitespace; ensure a single trailing newline.
    return re.sub(r"[ \t]+\n", "\n", rendered).rstrip() + "\n"
