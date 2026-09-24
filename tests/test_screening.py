from __future__ import annotations

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from resume_parser import split_lines  # noqa: E402
from scoring import assess_eligibility, build_result  # noqa: E402
from schemas import ParsedResume  # noqa: E402


def make_parsed_resume(text: str, candidate_name: str = "Test Candidate") -> ParsedResume:
    return ParsedResume(
        file_name="test.pdf",
        file_path="/tmp/test.pdf",
        text=text,
        lines=split_lines(text),
        candidate_name=candidate_name,
        matched_skills=[],
    )


class ScreeningTests(unittest.TestCase):
    def test_js_only_profile_is_rejected(self) -> None:
        text = """
        Jane Doe
        Skills: React, Next.js, TypeScript, Node.js
        Projects: Built a dashboard with REST APIs and deployment pipelines.
        """
        parsed = make_parsed_resume(text)
        eligible, reasons, _ = assess_eligibility(parsed)
        self.assertFalse(eligible)
        self.assertIn("No evidence of Python stack", reasons)
        self.assertIn("No AI/agentic project evidence", reasons)

    def test_python_ai_profile_is_eligible(self) -> None:
        text = """
        Asha Rao
        Skills: Python, FastAPI, PostgreSQL, Docker
        Projects: Built a stateful RAG assistant with LangChain, vector search, and tool calling.
        Experience: Implemented async backend services and evaluation pipelines.
        """
        parsed = make_parsed_resume(text)
        eligible, reasons, _ = assess_eligibility(parsed)
        self.assertTrue(eligible, reasons)
        result = build_result(parsed, None)
        self.assertTrue(result.eligible)
        self.assertGreater(result.total_score, 0)
        self.assertIn("Python", result.matched_skills)

    def test_shallow_ai_claim_does_not_count_as_eligibility(self) -> None:
        text = """
        Sam Lee
        Skills: Python, Flask
        Projects: Leveraged AI-assisted development tools and Copilot to speed up coding.
        """
        parsed = make_parsed_resume(text)
        eligible, reasons, _ = assess_eligibility(parsed)
        self.assertFalse(eligible)
        self.assertIn("No AI/agentic project evidence", reasons)


if __name__ == "__main__":
    unittest.main()