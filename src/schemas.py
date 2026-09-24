from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class ResumeCandidate:
    name: str
    resume_path: str
    github_username: Optional[str] = None
    email: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedResume:
    file_name: str
    file_path: str
    text: str
    lines: List[str]
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    github_username: Optional[str] = None
    github_url: Optional[str] = None
    matched_skills: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ScoreBreakdown:
    ai_project_depth: int = 0
    python_backend: int = 0
    cloud_fullstack: int = 0
    github: int = 0
    engineering_depth: int = 0
    project_quality_penalty: int = 0

    def total(self) -> int:
        return max(
            0,
            min(
                100,
                self.ai_project_depth
                + self.python_backend
                + self.cloud_fullstack
                + self.github
                + self.engineering_depth
                - self.project_quality_penalty,
            ),
        )


@dataclass(slots=True)
class ScreeningResult:
    rank: Optional[int]
    candidate_name: str
    file_name: str
    eligible: bool
    total_score: int
    score_breakdown: ScoreBreakdown
    matched_skills: List[str]
    project_summary: str
    github_summary: str
    strengths: List[str]
    concerns: List[str]
    rejection_reasons: List[str]
    evidence: Dict[str, List[str]] = field(default_factory=dict)
    parse_status: str = "parsed"
    error: Optional[str] = None


@dataclass(slots=True)
class BatchSummary:
    total_resumes: int
    successfully_parsed: int
    eligible: int
    rejected: int
    failed_unreadable: int


@dataclass(slots=True)
class GitHubEnrichmentResult:
    username: str
    profile_url: str
    name: Optional[str] = None
    company: Optional[str] = None
    bio: Optional[str] = None
    followers: Optional[int] = None
    public_repos: Optional[int] = None
    recent_activity_points: int = 0
    repo_points: int = 0
    summary: str = ""
    error: Optional[str] = None
