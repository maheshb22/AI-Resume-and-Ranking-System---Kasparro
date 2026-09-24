from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Tuple

from github_enrichment import GitHubEnrichmentResult
from resume_parser import (
    ai_evidence_lines,
    collect_evidence_lines,
    detect_skills,
    has_python_evidence,
    summarize_line,
)
from schemas import ParsedResume, ScoreBreakdown, ScreeningResult


def assess_eligibility(parsed: ParsedResume) -> tuple[bool, List[str], Dict[str, List[str]]]:
    evidence: Dict[str, List[str]] = {"python": [], "ai": []}
    python_lines = collect_evidence_lines(
        parsed.lines,
        ("python", "fastapi", "flask", "django", "pytorch", "pandas", "numpy", "scikit-learn", "sklearn"),
        sections={"skills", "technical skills", "tech stack", "projects", "project", "experience", "work experience", "internship", "professional experience"},
    )
    ai_lines = ai_evidence_lines(parsed.lines)
    evidence["python"] = python_lines[:3]
    evidence["ai"] = ai_lines[:3]

    rejection_reasons: List[str] = []
    if not has_python_evidence(parsed.lines, parsed.text):
        rejection_reasons.append("No evidence of Python stack")
    if not ai_lines:
        rejection_reasons.append("No AI/agentic project evidence")
    return not rejection_reasons, rejection_reasons, evidence


def score_candidate(parsed: ParsedResume, github: GitHubEnrichmentResult | None) -> tuple[ScoreBreakdown, List[str], List[str], str, str]:
    breakdown = ScoreBreakdown()
    lower_text = parsed.text.lower()
    project_lines = ai_evidence_lines(parsed.lines)

    # AI / agentic / RAG project depth.
    ai_signals = {
        "langchain": 12,
        "langgraph": 12,
        "llamaindex": 12,
        "rag": 10,
        "retrieval augmented generation": 10,
        "vector database": 6,
        "vector search": 6,
        "embeddings": 6,
        "agentic": 8,
        "multi-agent": 8,
        "tool calling": 8,
        "function calling": 8,
        "llm": 6,
        "openai": 4,
        "gemini": 4,
        "anthropic": 4,
        "ai-driven": 6,
        "machine learning": 4,
        "nlp": 3,
    }
    breakdown.ai_project_depth += sum(points for signal, points in ai_signals.items() if signal in lower_text)
    breakdown.ai_project_depth += min(8, len(project_lines) * 2)
    if project_lines:
        breakdown.ai_project_depth += 4
    if any(token in lower_text for token in ("retrieval", "orchestration", "stateful", "workflow", "evaluation", "feedback loop", "memory")):
        breakdown.ai_project_depth += 4
    if any(token in lower_text for token in ("api", "backend", "backend service", "data pipeline", "database", "postgres", "redis")) and project_lines:
        breakdown.ai_project_depth += 4
    breakdown.ai_project_depth = min(40, breakdown.ai_project_depth)

    # Python & backend engineering.
    python_points = 0
    for token, points in (
        ("python", 10),
        ("fastapi", 8),
        ("flask", 5),
        ("django", 5),
        ("async", 4),
        ("asyncio", 4),
        ("postgresql", 4),
        ("postgres", 4),
        ("redis", 4),
        ("sqlalchemy", 3),
        ("pytest", 3),
    ):
        if token in lower_text:
            python_points += points
    if any(line for line in parsed.lines if "python" in line.lower() and any(verb in line.lower() for verb in ("built", "implemented", "developed", "engineered"))):
        python_points += 4
    breakdown.python_backend = min(30, python_points)

    # Cloud / deployment / full stack.
    cloud_points = 0
    for token, points in (
        ("docker", 4),
        ("gcp", 4),
        ("google cloud", 4),
        ("aws", 3),
        ("ci/cd", 4),
        ("github actions", 3),
        ("deployment", 3),
        ("react", 3),
        ("next.js", 3),
        ("full stack", 4),
        ("frontend", 2),
        ("backend", 2),
    ):
        if token in lower_text:
            cloud_points += points
    if any(token in lower_text for token in ("razorpay", "rest api", "restful", "jwt", "tailwind", "typescript")):
        cloud_points += 1
    breakdown.cloud_fullstack = min(15, cloud_points)

    # Engineering depth signals.
    engineering_points = 0
    for token, points in (
        ("testing", 1),
        ("pytest", 2),
        ("architecture", 1),
        ("caching", 1),
        ("queue", 1),
        ("queues", 1),
        ("observability", 1),
        ("monitoring", 1),
        ("concurrency", 1),
        ("async", 1),
        ("failure handling", 1),
        ("rate limit", 1),
        ("rbac", 1),
        ("state management", 1),
        ("error handling", 1),
        ("modular", 1),
        ("scalable", 1),
    ):
        if token in lower_text:
            engineering_points += points
    breakdown.engineering_depth = min(5, engineering_points)

    # GitHub enrichment.
    github_points = 0
    if github:
        github_points = min(10, github.recent_activity_points + github.repo_points)
    breakdown.github = github_points

    # Project quality penalty.
    penalty = 0
    shallow_ai_phrases = ("ai-assisted development", "github copilot", "copilot", "chatgpt")
    if project_lines and len(project_lines) == 1 and any(phrase in project_lines[0].lower() for phrase in shallow_ai_phrases):
        penalty += 8
    elif any(phrase in lower_text for phrase in shallow_ai_phrases) and not project_lines:
        penalty += 5
    if project_lines and breakdown.ai_project_depth < 12:
        penalty += 5
    breakdown.project_quality_penalty = min(15, penalty)

    project_summary = summarize_line(project_lines[0]) if project_lines else "No strong AI project evidence found."
    github_summary = github.summary if github else "No GitHub profile found on the resume."
    return breakdown, project_lines, [github_summary], project_summary, github_summary


def build_result(parsed: ParsedResume, github: GitHubEnrichmentResult | None) -> ScreeningResult:
    matched_skills = parsed.matched_skills or detect_skills(parsed.text)
    eligible, rejection_reasons, evidence = assess_eligibility(parsed)
    if not eligible:
        return ScreeningResult(
            rank=None,
            candidate_name=parsed.candidate_name or parsed.email or parsed.file_name,
            file_name=parsed.file_name,
            eligible=False,
            total_score=0,
            score_breakdown=ScoreBreakdown(),
            matched_skills=matched_skills,
            project_summary=evidence["ai"][0] if evidence["ai"] else "",
            github_summary=(github.summary if github else "No GitHub profile found on the resume."),
            strengths=[],
            concerns=["Did not meet the hard eligibility filters"],
            rejection_reasons=rejection_reasons,
            evidence=evidence,
        )

    breakdown, project_lines, _, project_summary, github_summary = score_candidate(parsed, github)
    total = breakdown.total()
    strengths = []
    if breakdown.ai_project_depth >= 20:
        strengths.append("Strong AI or agentic project evidence")
    if breakdown.python_backend >= 18:
        strengths.append("Strong Python backend signal")
    if breakdown.cloud_fullstack >= 8:
        strengths.append("Solid deployment or full-stack signal")
    if breakdown.github >= 5:
        strengths.append("Positive GitHub activity")
    if breakdown.engineering_depth >= 3:
        strengths.append("Non-trivial engineering depth")

    concerns = []
    if breakdown.project_quality_penalty > 0:
        concerns.append("Some AI project claims look shallow or thinly implemented")
    if breakdown.github == 0:
        concerns.append("No measurable GitHub signal")
    if breakdown.engineering_depth < 2:
        concerns.append("Limited evidence of testing, concurrency, or observability")

    evidence = {
        "python": collect_evidence_lines(
            parsed.lines,
            ("python", "fastapi", "flask", "django", "pytorch", "pandas", "numpy", "scikit-learn", "sklearn"),
            sections={"skills", "technical skills", "tech stack", "projects", "project", "experience", "work experience", "internship", "professional experience"},
        )[:3],
        "ai": project_lines[:3],
    }

    return ScreeningResult(
        rank=None,
        candidate_name=parsed.candidate_name or parsed.email or parsed.file_name,
        file_name=parsed.file_name,
        eligible=True,
        total_score=total,
        score_breakdown=breakdown,
        matched_skills=matched_skills,
        project_summary=project_summary,
        github_summary=github_summary,
        strengths=strengths,
        concerns=concerns,
        rejection_reasons=[],
        evidence=evidence,
    )