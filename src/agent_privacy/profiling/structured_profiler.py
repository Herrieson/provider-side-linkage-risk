from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from agent_privacy.attacks.pipeline import group_by_label
from agent_privacy.features.extract import DOMAIN_RE, REPOSITORY_FIELD_RE, request_text
from agent_privacy.profiling.rule_profiler import (
    FIELD_KEYWORDS,
    REPO_SERVICE_RE,
    SERVICE_FIELD_RE,
    TARGET_SERVICE_RE,
    WORKSPACE_SLUG_RE,
    _repo_from_workspace_slug,
)


AUDITED_TECHNICAL_FIELDS = {
    "languages",
    "frameworks",
    "package_managers",
    "build_tools",
    "ci_cd_systems",
    "repo_names",
    "service_names",
}

STRUCTURED_CLUES = {
    "languages": {
        "python": (".py", "pyproject.toml", "requirements.txt", "python "),
        "javascript": (".js", "package.json", "npm "),
        "typescript": (".ts", ".tsx", "tsconfig.json", "pnpm "),
        "java": (".java", "pom.xml", "mvn ", "gradle "),
        "go": (".go", "go.mod", "go test"),
        "rust": (".rs", "cargo.toml", "cargo "),
        "ruby": (".rb", "gemfile", "bundle exec"),
    },
    "package_managers": {
        "pip": ("requirements.txt", "pip install"),
        "poetry": ("poetry.lock", "pyproject.toml", "poetry "),
        "npm": ("package.json", "package-lock.json", "npm "),
        "pnpm": ("pnpm-lock.yaml", "pnpm "),
        "yarn": ("yarn.lock", "yarn "),
        "maven": ("pom.xml", "mvn "),
        "gradle": ("build.gradle", "gradle "),
        "go mod": ("go.mod", "go mod"),
        "cargo": ("cargo.toml", "cargo "),
    },
    "frameworks": {
        "pytest": ("pytest.ini", "pytest ", "pytest-"),
        "django": ("django", "manage.py"),
        "flask": ("flask",),
        "react": ("react", "react-dom"),
        "nextjs": ("next.js", "nextjs", "next.config"),
        "spring": ("spring",),
        "rails": ("rails",),
    },
    "build_tools": {
        "pytest": ("pytest.ini", "pytest ", "pytest-"),
        "tox": ("tox.ini", "tox "),
        "make": ("makefile", "make "),
        "maven": ("pom.xml", "mvn "),
        "gradle": ("build.gradle", "gradle "),
        "go test": ("go test",),
        "cargo": ("cargo test", "cargo build"),
    },
    "ci_cd_systems": {
        "github_actions": (".github/workflows", "github actions"),
        "gitlab_ci": (".gitlab-ci.yml", "gitlab ci"),
        "jenkins": ("jenkinsfile", "jenkins"),
        "circleci": (".circleci", "circleci"),
    },
}


@dataclass
class EvidenceValue:
    request_ids: set[str]
    sources: set[str]
    score: float = 0.0


def profile_clusters_structured(
    rows: list[dict[str, Any]],
    labels: dict[str, str],
    min_cluster_size: int = 2,
    min_score: float = 2.0,
) -> dict[str, dict[str, Any]]:
    """Aggregate independent lexical and structural detectors into evidenced profiles."""

    row_by_id = {row["request_id"]: row for row in rows}
    profiles: dict[str, dict[str, Any]] = {}
    for cluster_id, request_ids in group_by_label(labels).items():
        if len(request_ids) < min_cluster_size:
            continue
        evidence: dict[str, dict[str, EvidenceValue]] = defaultdict(dict)
        for request_id in request_ids:
            row = row_by_id.get(request_id)
            if row is None:
                continue
            text = request_text(row).lower()
            _observe_lexical(text, request_id, evidence)
            _observe_structured(text, request_id, evidence)
            _observe_entities(text, request_id, evidence)
        kept = {
            field: {
                value: item
                for value, item in values.items()
                if item.score >= min_score or len(item.request_ids) >= 2
            }
            for field, values in evidence.items()
        }
        kept = {field: values for field, values in kept.items() if values}
        profiles[cluster_id] = {
            "request_ids": request_ids,
            "profiler": "structured_evidence",
            "fields": {field: sorted(values) for field, values in kept.items()},
            "evidence": {
                field: {value: sorted(item.request_ids)[:5] for value, item in values.items()}
                for field, values in kept.items()
            },
            "confidence": {
                field: {
                    value: {
                        "score": round(item.score, 3),
                        "request_count": len(item.request_ids),
                        "sources": sorted(item.sources),
                    }
                    for value, item in values.items()
                }
                for field, values in kept.items()
            },
        }
    return profiles


def _observe_lexical(
    text: str,
    request_id: str,
    evidence: dict[str, dict[str, EvidenceValue]],
) -> None:
    normalized = text.replace("-", "_")
    tokens = set(re.findall(r"[a-z][a-z0-9_]+", normalized))
    for field, values in FIELD_KEYWORDS.items():
        if field not in AUDITED_TECHNICAL_FIELDS:
            continue
        for value in values:
            normalized_value = value.replace("-", "_")
            matched = (
                normalized_value in normalized
                if " " in normalized_value
                else normalized_value in tokens
            )
            if matched:
                _add(evidence, field, value, request_id, "lexical", 1.0)


def _observe_structured(
    text: str,
    request_id: str,
    evidence: dict[str, dict[str, EvidenceValue]],
) -> None:
    for field, values in STRUCTURED_CLUES.items():
        for value, needles in values.items():
            for needle in needles:
                if needle in text:
                    source = "manifest" if "." in needle and " " not in needle else "command"
                    _add(evidence, field, value, request_id, source, 2.0)
                    break


def _observe_entities(
    text: str,
    request_id: str,
    evidence: dict[str, dict[str, EvidenceValue]],
) -> None:
    repos: set[str] = set()
    for _, repo in REPOSITORY_FIELD_RE.findall(text):
        repos.add(repo.lower())
    for slug in WORKSPACE_SLUG_RE.findall(text):
        repo = _repo_from_workspace_slug(slug)
        if repo:
            repos.add(repo)
    for repo, service in REPO_SERVICE_RE.findall(text):
        repos.add(repo.lower())
        _add(evidence, "service_names", service.lower(), request_id, "explicit_service", 2.0)
    for repo in repos:
        _add(evidence, "repo_names", repo, request_id, "explicit_repo", 2.0)
        _add(evidence, "service_names", repo, request_id, "repo_service_proxy", 2.0)
    for pattern in (SERVICE_FIELD_RE, TARGET_SERVICE_RE):
        for service in pattern.findall(text):
            _add(evidence, "service_names", service.lower(), request_id, "explicit_service", 2.0)
    for domain in DOMAIN_RE.findall(text):
        _add(evidence, "internal_domains", domain.lower(), request_id, "explicit_domain", 2.0)


def _add(
    evidence: dict[str, dict[str, EvidenceValue]],
    field: str,
    value: str,
    request_id: str,
    source: str,
    weight: float,
) -> None:
    item = evidence[field].get(value)
    if item is None:
        item = EvidenceValue(request_ids=set(), sources=set())
        evidence[field][value] = item
    if source not in item.sources or request_id not in item.request_ids:
        item.score += weight
    item.request_ids.add(request_id)
    item.sources.add(source)
