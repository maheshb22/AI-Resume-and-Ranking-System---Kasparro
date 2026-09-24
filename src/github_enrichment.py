from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, Optional

import requests

from schemas import GitHubEnrichmentResult


class GitHubEnricher:
    def __init__(self, token: Optional[str] = None, timeout: int = 15) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.timeout = timeout
        self.session = requests.Session()
        self.cache: Dict[str, GitHubEnrichmentResult] = {}

    def enrich(self, username: Optional[str]) -> GitHubEnrichmentResult | None:
        if not username:
            return None
        normalized = username.strip().lstrip("@").lower()
        if normalized in self.cache:
            return self.cache[normalized]

        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            profile = self._get_json(f"https://api.github.com/users/{normalized}", headers)
            repos = self._get_json(f"https://api.github.com/users/{normalized}/repos?per_page=100&sort=updated", headers)
            events = self._get_json(f"https://api.github.com/users/{normalized}/events/public?per_page=30", headers)

            recent_activity_points = self._score_recent_activity(events)
            repo_points = self._score_repositories(repos)
            summary = self._build_summary(recent_activity_points, repo_points, repos)

            result = GitHubEnrichmentResult(
                username=profile.get("login", normalized),
                profile_url=profile.get("html_url", f"https://github.com/{normalized}"),
                name=profile.get("name"),
                company=profile.get("company"),
                bio=profile.get("bio"),
                followers=profile.get("followers"),
                public_repos=profile.get("public_repos"),
                recent_activity_points=recent_activity_points,
                repo_points=repo_points,
                summary=summary,
            )
        except Exception as exc:  # noqa: BLE001 - we want graceful per-candidate failure handling
            result = GitHubEnrichmentResult(
                username=normalized,
                profile_url=f"https://github.com/{normalized}",
                error=str(exc),
                summary=f"GitHub enrichment failed: {exc}",
            )

        self.cache[normalized] = result
        return result

    def _get_json(self, url: str, headers: dict[str, str]):
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _score_recent_activity(self, events) -> int:
        score = 0
        now = datetime.now(timezone.utc)
        for event in events or []:
            created_at = event.get("created_at")
            if not created_at:
                continue
            try:
                event_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            if (now - event_time).days <= 90 and event.get("type") in {"PushEvent", "CreateEvent", "PullRequestEvent", "IssuesEvent"}:
                score += 1
        return min(5, score)

    def _score_repositories(self, repos) -> int:
        score = 0
        now = datetime.now(timezone.utc)
        for repo in repos or []:
            updated_at = repo.get("updated_at")
            if not updated_at:
                continue
            try:
                updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            if (now - updated).days > 180:
                continue
            lower_blob = " ".join(
                str(repo.get(field, "") or "") for field in ("name", "description", "language")
            ).lower()
            if any(keyword in lower_blob for keyword in ("python", "ai", "ml", "llm", "rag", "agent", "fastapi", "flask", "django", "pytorch", "langchain")):
                score += 1
        return min(5, score)

    def _build_summary(self, recent_activity_points: int, repo_points: int, repos) -> str:
        repo_count = len(repos or [])
        if recent_activity_points == 0 and repo_points == 0:
            return f"Public GitHub profile found; no strong recent activity signal from {repo_count} repositories."
        return (
            f"Recent activity score {recent_activity_points}/5 and maintained/relevant repo score {repo_points}/5 "
            f"from {repo_count} public repositories."
        )


def enrich_github_profile(username: str, token: Optional[str] = None) -> GitHubEnrichmentResult | None:
    return GitHubEnricher(token=token).enrich(username)
