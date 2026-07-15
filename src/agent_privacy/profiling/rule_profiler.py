from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from agent_privacy.attacks.pipeline import group_by_label
from agent_privacy.features.extract import DOMAIN_RE, REPOSITORY_FIELD_RE, request_text


WORKSPACE_SLUG_RE = re.compile(r"/workspace/([^/\s]+)")
SERVICE_FIELD_RE = re.compile(r"\bservice=([a-z][a-z0-9_.-]{2,})\b")
TARGET_SERVICE_RE = re.compile(r"\btarget service ([a-z][a-z0-9_.-]{2,})\b")
REPO_SERVICE_RE = re.compile(r"\bfor ([a-z][a-z0-9_.-]{2,})/([a-z][a-z0-9_.-]{2,})\b")


FIELD_KEYWORDS = {
    "industries": ["finance", "healthcare", "ecommerce", "saas", "security", "logistics"],
    "languages": ["python", "typescript", "javascript", "java", "go", "rust", "ruby"],
    "frameworks": [
        "fastapi",
        "django",
        "flask",
        "pytest",
        "jest",
        "nestjs",
        "nextjs",
        "react",
        "spring",
        "gin",
        "rails",
    ],
    "databases": ["postgresql", "mysql", "clickhouse", "redis"],
    "cloud_providers": ["aws", "gcp", "azure", "self_hosted"],
    "ci_cd_systems": ["github_actions", "gitlab_ci", "jenkins", "circleci"],
    "auth_systems": ["oauth2", "oidc", "saml", "jwt", "ldap"],
    "package_managers": ["pip", "poetry", "npm", "pnpm", "yarn", "maven", "gradle", "go mod", "cargo"],
    "build_tools": ["pytest", "tox", "make", "cmake", "bazel", "maven", "gradle", "go test", "cargo"],
    "security_clues": ["permission bypass", "ssrf", "xss", "audit log", "rbac", "token rotation"],
}
FIELD_PATTERNS = {
    field: [(value, re.compile(rf"\b{re.escape(value.replace('-', '_'))}\b")) for value in values]
    for field, values in FIELD_KEYWORDS.items()
}
DOMAIN_FIELDS = {"internal_domains"}
ID_STOP = {
    "trace",
    "synthetic_token",
    "sk-test",
    "generic-agent-model",
    "maxfail",
    "dry-run",
}


def profile_clusters(
    rows: list[dict[str, Any]], labels: dict[str, str], min_cluster_size: int = 2
) -> dict[str, dict[str, Any]]:
    row_by_id = {row["request_id"]: row for row in rows}
    profiles: dict[str, dict[str, Any]] = {}
    for cluster_id, request_ids in group_by_label(labels).items():
        if len(request_ids) < min_cluster_size:
            continue
        evidence: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for request_id in request_ids:
            text = request_text(row_by_id[request_id]).lower()
            _extract_keywords(text, request_id, evidence)
            _extract_domains(text, request_id, evidence)
            _extract_repo_and_service_names(text, request_id, evidence)
        profiles[cluster_id] = {
            "request_ids": request_ids,
            "fields": {
                field: sorted(values)
                for field, values in evidence.items()
                if field != "_evidence"
            },
            "evidence": {
                field: {value: sorted(ids)[:5] for value, ids in values.items()}
                for field, values in evidence.items()
            },
        }
    return profiles


def _extract_keywords(text: str, request_id: str, evidence: dict[str, dict[str, list[str]]]) -> None:
    normalized = text.replace("-", "_")
    for field, patterns in FIELD_PATTERNS.items():
        for value, pattern in patterns:
            if pattern.search(normalized):
                evidence[field][value].append(request_id)


def _extract_domains(text: str, request_id: str, evidence: dict[str, dict[str, list[str]]]) -> None:
    for domain in DOMAIN_RE.findall(text):
        evidence["internal_domains"][domain.lower()].append(request_id)


def _extract_repo_and_service_names(
    text: str,
    request_id: str,
    evidence: dict[str, dict[str, list[str]]],
) -> None:
    for _, repo in REPOSITORY_FIELD_RE.findall(text):
        evidence["repo_names"][repo.lower()].append(request_id)
    for slug in WORKSPACE_SLUG_RE.findall(text):
        repo = _repo_from_workspace_slug(slug)
        if repo:
            evidence["repo_names"][repo].append(request_id)
    for repo, service in REPO_SERVICE_RE.findall(text):
        evidence["repo_names"][repo.lower()].append(request_id)
        evidence["service_names"][service.lower()].append(request_id)
    for service in SERVICE_FIELD_RE.findall(text):
        evidence["service_names"][service.lower()].append(request_id)
    for service in TARGET_SERVICE_RE.findall(text):
        evidence["service_names"][service.lower()].append(request_id)


def _skip_id(identifier: str) -> bool:
    return (
        identifier in ID_STOP
        or identifier.startswith("trace-")
        or identifier.startswith("sk-test")
        or len(identifier) > 80
    )


def _repo_from_workspace_slug(slug: str) -> str | None:
    parts = slug.lower().split("__")
    if len(parts) < 2:
        return None
    repo = parts[1]
    return repo if repo and not repo.replace(".", "").isdigit() else None
