from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.resume_model import (
    Header,
    Link,
    EducationEntry,
    SkillGroup,
    Role,
    ExperienceEntry,
    ProjectEntry,
    ResumeContent,
)
from core.resume_renderer import render_resume, latex_escape, latex_escape_url
from pydantic import ValidationError


def _sample(**overrides) -> ResumeContent:
    base = dict(
        header=Header(
            name="Alex Yuan",
            phone="+1 647-573-0588",
            email="a@b.com",
            links=[Link(label="linkedin.com/in/alex", url="https://linkedin.com/in/alex")],
            citizenship="Canada (TN eligible)",
        ),
        education=[
            EducationEntry(
                institution="U of T",
                location="Toronto, ON",
                degree="BASc Computer Engineering",
                dates="2021--2026",
                highlights=["Minor in AI & Business (GPA: 3.75/4.0)"],
            )
        ],
        skills=[SkillGroup(category="Languages", items=["Python", "C++", "Go"])],
        summary="Engineer with 100% focus on backend & scale.",
        experience=[
            ExperienceEntry(
                company="AMD",
                location="Toronto, ON",
                roles=[
                    Role(title="SWE (Contract)", dates="May 2025 -- Aug 2025"),
                    Role(title="SWE Intern (PEY)", dates="May 2024 -- May 2025"),
                ],
                bullets=["Reduced latency by 30% via Jenkins CI/CD."],
            )
        ],
        projects=[
            ProjectEntry(name="AutoCareer", tech=["FastAPI", "Docker"], bullets=["Automated tailoring with AI."])
        ],
    )
    base.update(overrides)
    return ResumeContent(**base)


class LatexEscapeTests(unittest.TestCase):
    def test_escapes_all_special_characters(self):
        self.assertEqual(
            latex_escape("a & b 100% #1 $x_y {z}"),
            r"a \& b 100\% \#1 \$x\_y \{z\}",
        )

    def test_backslash_escaped_first(self):
        self.assertEqual(latex_escape(r"a\b"), r"a\textbackslash{}b")

    def test_none_is_empty(self):
        self.assertEqual(latex_escape(None), "")

    def test_url_escape_keeps_url_usable(self):
        self.assertEqual(latex_escape_url("https://x.com/a#b%c"), r"https://x.com/a\#b\%c")


class RenderResumeTests(unittest.TestCase):
    def test_renders_full_document(self):
        out = render_resume(_sample())
        self.assertIn(r"\documentclass", out)
        self.assertIn(r"\begin{document}", out)
        self.assertIn(r"\end{document}", out)
        self.assertIn(r"\pdfgentounicode=1", out)  # ATS-parsable flag preserved

    def test_escapes_content_in_body(self):
        out = render_resume(_sample())
        self.assertIn(r"100\%", out)
        self.assertIn(r"backend \& scale", out)
        self.assertIn(r"AI \& Business", out)

    def test_multiple_roles_under_one_company(self):
        out = render_resume(_sample())
        self.assertIn(r"\textbf{AMD}", out)
        self.assertEqual(out.count(r"\textit{\small SWE"), 2)

    def test_email_and_link_become_hrefs(self):
        out = render_resume(_sample())
        self.assertIn(r"\href{mailto:a@b.com}", out)
        self.assertIn(r"\href{https://linkedin.com/in/alex}", out)

    def test_optional_sections_omitted_when_empty(self):
        out = render_resume(_sample(summary=None, projects=[], skills=[]))
        self.assertNotIn(r"\section{Summary}", out)
        self.assertNotIn(r"\section{Projects}", out)
        self.assertNotIn(r"\section{Technical Skills}", out)
        self.assertIn(r"\section{Experience}", out)


class ResumeContentValidationTests(unittest.TestCase):
    def test_rejects_empty_bullet(self):
        with self.assertRaises(ValidationError):
            ProjectEntry(name="X", tech=[], bullets=[""])

    def test_rejects_empty_name(self):
        with self.assertRaises(ValidationError):
            ProjectEntry(name="", tech=[], bullets=["ok"])

    def test_experience_requires_a_role(self):
        with self.assertRaises(ValidationError):
            ExperienceEntry(company="X", location="Y", roles=[], bullets=[])

    def test_to_plain_text_includes_key_sections(self):
        text = _sample().to_plain_text()
        self.assertIn("Alex Yuan", text)
        self.assertIn("AMD", text)
        self.assertIn("AutoCareer", text)
        self.assertIn("Languages: Python, C++, Go", text)


if __name__ == "__main__":
    unittest.main()
