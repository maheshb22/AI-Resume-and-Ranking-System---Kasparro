from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Iterable, List, Tuple

from pypdf import PdfReader

from schemas import ParsedResume


SECTION_HEADINGS = {
    "summary",
    "professional summary",
    "profile",
    "skills",
    "technical skills",
    "tech stack",
    "work experience",
    "experience",
    "professional experience",
    "internship",
    "internships",
    "projects",
    "key projects",
    "project experience",
    "education",
    "certifications",
}

SKILL_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("Python", ("python",)),
    ("FastAPI", ("fastapi",)),
    ("Flask", ("flask",)),
    ("Django", ("django",)),
    ("PostgreSQL", ("postgresql", "postgres")),
    ("Redis", ("redis",)),
    ("Docker", ("docker",)),
    ("GCP", ("gcp", "google cloud", "google cloud platform")),
    ("AWS", ("aws", "amazon web services")),
    ("CI/CD", ("ci/cd", "cicd", "github actions", "gitlab ci", "azure devops", "deployment pipeline")),
    ("React", ("react.js", "reactjs", "react ", "react,")),
    ("Next.js", ("next.js", "nextjs")),
    ("TypeScript", ("typescript",)),
    ("Node.js", ("node.js", "nodejs")),
    ("Express", ("express.js", "express")),
    ("MongoDB", ("mongodb",)),
    ("MySQL", ("mysql",)),
    ("LangChain", ("langchain",)),
    ("LangGraph", ("langgraph",)),
    ("LlamaIndex", ("llamaindex",)),
    ("RAG", ("rag", "retrieval augmented generation", "retrieval-augmented generation")),
    ("Vector Search", ("vector search", "vector database", "embeddings", "embedding")),
    ("Agents", ("agentic", "multi-agent", "tool calling", "function calling", "agents", "agent framework", "agent workflow")),
    ("LLM", ("llm", "large language model", "openai", "gemini", "anthropic")),
    ("PyTorch", ("pytorch",)),
    ("TensorFlow", ("tensorflow",)),
    ("scikit-learn", ("scikit-learn", "sklearn")),
    ("Testing", ("pytest", "unit test", "integration test", "test coverage")),
    ("Concurrency", ("async", "asyncio", "concurrency", "parallel")),
    ("Caching", ("cache", "caching", "redis")),
    ("Observability", ("logging", "metrics", "monitoring", "observability", "tracing")),
    ("Queues", ("queue", "queues", "rabbitmq", "kafka", "celery")),
    ("Kubernetes", ("kubernetes", "k8s")),
    ("Streamlit", ("streamlit",)),
]

ACTION_VERBS = (
    "built",
    "developed",
    "implemented",
    "engineered",
    "designed",
    "created",
    "integrated",
    "deployed",
    "optimized",
    "architected",
    "led",
    "owned",
    "maintained",
    "reduced",
    "improved",
    "delivered",
)

AI_SHALLOW_PHRASES = (
    "ai-assisted development",
    "github copilot",
    "copilot",
    "chatgpt",
    "used ai tools",
)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def read_resume_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        with zipfile.ZipFile(path) as archive:
            document = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        document = document.replace("</w:p>", "\n")
        return re.sub(r"<[^>]+>", "", document)
    raise ValueError(f"Unsupported resume format: {path.suffix}")


def split_lines(text: str) -> List[str]:
    lines = []
    for raw_line in text.splitlines():
        line = normalize_whitespace(raw_line.replace("•", " "))
        if line:
            lines.append(line)
    return lines


def extract_email(text: str) -> str | None:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else None


def extract_github_identity(text: str) -> tuple[str | None, str | None]:
    url_match = re.search(r"github\.com/([A-Za-z0-9_-]+)", text, flags=re.IGNORECASE)
    if url_match:
        username = url_match.group(1)
        return username, f"https://github.com/{username}"
    handle_match = re.search(r"(?:github\s*[:|]?\s*)([A-Za-z0-9_-]{2,39})", text, flags=re.IGNORECASE)
    if handle_match:
        username = handle_match.group(1)
        return username, f"https://github.com/{username}"
    return None, None


def is_heading(line: str) -> bool:
    normalized = normalize_whitespace(line).lower().rstrip(":")
    if normalized in SECTION_HEADINGS:
        return True
    if ":" in normalized:
        prefix = normalized.split(":", 1)[0].strip()
        return prefix in SECTION_HEADINGS
    return False


def extract_candidate_name(lines: List[str]) -> str | None:
    for line in lines[:6]:
        lower = line.lower()
        if any(token in lower for token in ("@", "phone", "email", "linkedin", "github", "portfolio", "summary", "skills")):
            continue
        words = line.split()
        if 1 < len(words) <= 5 and all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word) for word in words):
            return line
    return None


def detect_skills(text: str) -> List[str]:
    lowered = text.lower()
    matched: List[str] = []
    for skill_name, variants in SKILL_PATTERNS:
        if any(variant in lowered for variant in variants):
            matched.append(skill_name)
    return matched


def parse_resume(path: Path) -> ParsedResume:
    text = read_resume_text(path)
    lines = split_lines(text)
    return ParsedResume(
        file_name=path.name,
        file_path=str(path),
        text=text,
        lines=lines,
        candidate_name=extract_candidate_name(lines),
        email=extract_email(text),
        github_username=extract_github_identity(text)[0],
        github_url=extract_github_identity(text)[1],
        matched_skills=detect_skills(text),
    )


def section_lines(lines: List[str]) -> List[tuple[str, str]]:
    current_section = ""
    output: List[tuple[str, str]] = []
    for line in lines:
        normalized = normalize_whitespace(line).lower()
        if is_heading(line):
            current_section = normalized.split(":", 1)[0].strip().rstrip(":")
        output.append((current_section, line))
    return output


def contains_action_verb(text: str) -> bool:
    lower = text.lower()
    return any(verb in lower for verb in ACTION_VERBS)


def looks_like_shallow_ai(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in AI_SHALLOW_PHRASES)


def summarize_line(line: str, limit: int = 150) -> str:
    summary = normalize_whitespace(line)
    if len(summary) <= limit:
        return summary
    return summary[: limit - 3].rstrip() + "..."


def collect_evidence_lines(lines: List[str], keywords: Iterable[str], sections: Iterable[str] | None = None, require_action: bool = False) -> List[str]:
    allowed_sections = {section.lower() for section in sections} if sections else None
    evidence: List[str] = []
    for section, line in section_lines(lines):
        if allowed_sections is not None and section not in allowed_sections:
            continue
        lower = line.lower()
        if any(keyword in lower for keyword in keywords):
            if require_action and not contains_action_verb(lower):
                continue
            evidence.append(line)
    return evidence


def has_python_evidence(lines: List[str], text: str) -> bool:
    lower = text.lower()
    python_markers = ("python", "fastapi", "flask", "django", "pytorch", "pandas", "numpy", "scikit-learn", "sklearn")
    return any(marker in lower for marker in python_markers) and bool(collect_evidence_lines(lines, python_markers, sections={"skills", "projects", "project", "experience", "work experience", "internship", "professional experience"}))


def ai_evidence_lines(lines: List[str]) -> List[str]:
    ai_keywords = (
        "langchain",
        "langgraph",
        "llamaindex",
        "rag",
        "retrieval augmented generation",
        "retrieval-augmented generation",
        "vector database",
        "vector search",
        "embedding",
        "embeddings",
        "agentic",
        "multi-agent",
        "tool calling",
        "function calling",
        "llm",
        "large language model",
        "openai",
        "gemini",
        "anthropic",
        "ai-driven",
        "machine learning",
        "nlp",
        "prompt orchestration",
    )
    evidence: List[str] = []
    for section, line in section_lines(lines):
        lower = line.lower()
        if section in {"skills", "technical skills", "tech stack"}:
            continue
        if looks_like_shallow_ai(lower):
            continue
        if any(keyword in lower for keyword in ai_keywords) and (contains_action_verb(lower) or section in {"projects", "key projects", "project experience", "experience", "work experience", "internship", "professional experience"}):
            evidence.append(line)
    return evidence
