from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from agent_privacy.attacks.pipeline import group_by_label
from agent_privacy.profiling.structured_profiler import profile_clusters_structured


DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SPAN_CHARS = 480
MAX_SPANS_PER_REQUEST = 8
SEMANTIC_FIELDS = {
    "languages",
    "frameworks",
    "package_managers",
    "build_tools",
    "ci_cd_systems",
}

ONTOLOGY: dict[str, dict[str, str]] = {
    "languages": {
        "python": "Python programming language, Python source files, interpreter, packages, tracebacks, or pyproject configuration",
        "javascript": "JavaScript programming language, Node.js source, npm packages, or JavaScript runtime",
        "typescript": "TypeScript programming language, typed JavaScript source, tsconfig, TS or TSX files",
        "java": "Java programming language, JVM source, Maven or Gradle Java project",
        "go": "Go programming language, Golang source, go modules, or go test commands",
        "rust": "Rust programming language, Cargo crates, Rust source, compiler, or borrow checker",
        "ruby": "Ruby programming language, gems, Bundler, Ruby source, or Rails project",
        "c": "C programming language, C source, headers, compiler, gcc, clang, make, or native library",
        "php": "PHP programming language, Composer packages, PHP source, PHPUnit, or Laravel-style application",
    },
    "frameworks": {
        "pytest": "pytest Python testing framework, fixtures, parametrized tests, conftest, or pytest plugins",
        "django": "Django Python web framework, manage.py, models, views, settings, or migrations",
        "flask": "Flask Python web framework, routes, blueprints, WSGI, or Flask application",
        "react": "React JavaScript user interface framework, components, hooks, JSX, or react-dom",
        "nextjs": "Next.js React web framework, next.config, pages, app router, or server rendering",
        "spring": "Spring Java application framework, Spring Boot, dependency injection, controllers, or beans",
        "rails": "Ruby on Rails web framework, ActiveRecord, Rails controllers, models, or migrations",
    },
    "package_managers": {
        "pip": "pip Python package manager, requirements files, wheels, or pip install commands",
        "poetry": "Poetry Python dependency manager, pyproject dependencies, poetry lock, or poetry commands",
        "npm": "npm Node.js package manager, package.json, package-lock, or npm commands",
        "pnpm": "pnpm Node.js package manager, pnpm lockfile, workspace, or pnpm commands",
        "yarn": "Yarn Node.js package manager, yarn lockfile, workspace, or yarn commands",
        "maven": "Maven Java dependency and build manager, pom.xml, mvn commands, or Maven plugins",
        "gradle": "Gradle build and dependency manager, build.gradle, Gradle wrapper, tasks, or plugins",
        "go mod": "Go modules dependency management, go.mod, go.sum, or go mod commands",
        "cargo": "Cargo Rust package and build manager, Cargo.toml, crates, or cargo commands",
    },
    "build_tools": {
        "pytest": "running Python tests with pytest, fixtures, test discovery, or pytest configuration",
        "tox": "tox Python test environment automation, tox.ini, environments, or tox commands",
        "make": "Make build automation, Makefile targets, native compilation, or make commands",
        "maven": "building or testing a Java project with Maven or mvn commands",
        "gradle": "building or testing a project with Gradle tasks or Gradle wrapper",
        "go test": "building or testing Go packages with go test",
        "cargo": "building or testing Rust crates with cargo build or cargo test",
    },
    "ci_cd_systems": {
        "github_actions": "GitHub Actions continuous integration workflows, actions runners, or .github workflows",
        "gitlab_ci": "GitLab CI continuous integration pipelines, jobs, runners, or gitlab-ci configuration",
        "jenkins": "Jenkins continuous integration, Jenkinsfile, pipeline stages, agents, or jobs",
        "circleci": "CircleCI continuous integration, CircleCI configuration, workflows, jobs, or executors",
    },
}

TECHNICAL_CUE_RE = re.compile(
    r"(?:\.py\b|\.js\b|\.ts\b|\.tsx\b|\.java\b|\.go\b|\.rs\b|\.rb\b|\.php\b|"
    r"pyproject|requirements|package\.json|tsconfig|pom\.xml|build\.gradle|go\.mod|cargo\.toml|"
    r"pytest|django|flask|react|next\.js|spring|rails|pip\s|poetry|npm\s|pnpm|yarn|mvn\s|"
    r"gradle|go test|cargo|makefile|jenkins|circleci|github/workflows|gitlab-ci|"
    r"import\s|dependency|dependencies|build|compile|runtime|framework|test|error|exception)",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(
    r"\b(?:not|never|without|remove|removed|removing|replace|replaced|migrate|migrating|"
    r"deprecated|deprecate|avoid|unused|unrelated)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EvidenceSpan:
    request_id: str
    role: str
    source_type: str
    text: str


@dataclass(frozen=True)
class SemanticCandidate:
    field: str
    value: str
    score: float
    span: str
    role: str
    source_type: str


@dataclass(frozen=True)
class SemanticOptions:
    model_name: str = DEFAULT_MODEL
    batch_size: int = 128
    candidate_floor: float = 0.25
    top_k_per_field: int = 2
    max_spans_per_request: int = MAX_SPANS_PER_REQUEST


def encode_request_evidence(
    rows: list[dict[str, Any]],
    options: SemanticOptions | None = None,
    encoder: Callable[[list[str]], np.ndarray] | None = None,
) -> tuple[dict[str, list[SemanticCandidate]], dict[str, Any]]:
    options = options or SemanticOptions()
    extract_start = time.perf_counter()
    spans = [
        span
        for row in rows
        for span in extract_evidence_spans(
            row,
            max_spans=options.max_spans_per_request,
        )
    ]
    unique_texts = list(dict.fromkeys(span.text for span in spans))
    extract_seconds = time.perf_counter() - extract_start
    if encoder is None:
        encoder = _sentence_transformer_encoder(options.model_name, options.batch_size)
    ontology_items = [
        (field, value, description)
        for field, values in ONTOLOGY.items()
        for value, description in values.items()
    ]
    encode_start = time.perf_counter()
    span_embeddings = encoder(unique_texts) if unique_texts else np.empty((0, 0))
    ontology_embeddings = encoder([item[2] for item in ontology_items])
    encode_seconds = time.perf_counter() - encode_start
    text_index = {text: index for index, text in enumerate(unique_texts)}
    request_candidates: dict[str, dict[tuple[str, str], SemanticCandidate]] = defaultdict(dict)
    score_start = time.perf_counter()
    ontology_by_field: dict[str, list[int]] = defaultdict(list)
    for index, (field, _, _) in enumerate(ontology_items):
        ontology_by_field[field].append(index)
    for span in spans:
        vector = span_embeddings[text_index[span.text]]
        scores = ontology_embeddings @ vector
        for field, indexes in ontology_by_field.items():
            ranked = sorted(indexes, key=lambda index: float(scores[index]), reverse=True)[
                : options.top_k_per_field
            ]
            for index in ranked:
                score = float(scores[index])
                if score < options.candidate_floor:
                    continue
                _, value, _ = ontology_items[index]
                if _contradicted(span.text, value):
                    continue
                key = (field, value)
                current = request_candidates[span.request_id].get(key)
                if current is None or score > current.score:
                    request_candidates[span.request_id][key] = SemanticCandidate(
                        field=field,
                        value=value,
                        score=score,
                        span=span.text,
                        role=span.role,
                        source_type=span.source_type,
                    )
    score_seconds = time.perf_counter() - score_start
    candidates = {
        request_id: sorted(values.values(), key=lambda item: item.score, reverse=True)
        for request_id, values in request_candidates.items()
    }
    return candidates, {
        "model": options.model_name,
        "requests": len(rows),
        "spans": len(spans),
        "unique_spans": len(unique_texts),
        "semantic_candidates": sum(len(values) for values in candidates.values()),
        "extract_seconds": extract_seconds,
        "encode_seconds": encode_seconds,
        "score_seconds": score_seconds,
        "total_seconds": extract_seconds + encode_seconds + score_seconds,
    }


def profile_clusters_semantic(
    rows: list[dict[str, Any]],
    labels: dict[str, str],
    request_candidates: dict[str, list[SemanticCandidate]],
    *,
    threshold: float,
    min_request_support: int,
    high_confidence_margin: float = 0.10,
) -> dict[str, dict[str, Any]]:
    structured = profile_clusters_structured(rows, labels)
    profiles: dict[str, dict[str, Any]] = {}
    for cluster_id, request_ids in group_by_label(labels).items():
        base = structured.get(
            cluster_id,
            {"request_ids": request_ids, "fields": {}, "evidence": {}, "confidence": {}},
        )
        fields = {field: set(values) for field, values in base.get("fields", {}).items()}
        evidence = {
            field: {value: list(ids) for value, ids in values.items()}
            for field, values in base.get("evidence", {}).items()
        }
        confidence = {
            field: {value: dict(item) for value, item in values.items()}
            for field, values in base.get("confidence", {}).items()
        }
        semantic: dict[tuple[str, str], list[tuple[str, SemanticCandidate]]] = defaultdict(list)
        for request_id in request_ids:
            for candidate in request_candidates.get(request_id, []):
                if candidate.score >= threshold:
                    semantic[(candidate.field, candidate.value)].append((request_id, candidate))
        for (field, value), items in semantic.items():
            distinct_requests = sorted({request_id for request_id, _ in items})
            best = max((candidate for _, candidate in items), key=lambda item: item.score)
            accepted = (
                len(distinct_requests) >= min_request_support
                or best.score >= threshold + high_confidence_margin
            )
            if not accepted:
                continue
            fields.setdefault(field, set()).add(value)
            existing = evidence.setdefault(field, {}).setdefault(value, [])
            evidence[field][value] = sorted(set(existing) | set(distinct_requests))[:5]
            confidence.setdefault(field, {})[value] = {
                "score": round(best.score, 4),
                "request_count": len(distinct_requests),
                "sources": sorted(
                    {"semantic_embedding"} | {candidate.source_type for _, candidate in items}
                ),
                "best_span": best.span[:SPAN_CHARS],
                "best_span_role": best.role,
            }
        profiles[cluster_id] = {
            "request_ids": request_ids,
            "profiler": "semantic_evidence",
            "threshold": threshold,
            "min_request_support": min_request_support,
            "fields": {field: sorted(values) for field, values in fields.items()},
            "evidence": evidence,
            "confidence": confidence,
        }
    return profiles


def extract_evidence_spans(row: dict[str, Any], *, max_spans: int) -> list[EvidenceSpan]:
    spans: list[EvidenceSpan] = []
    seen: set[str] = set()
    for message in row.get("messages", []):
        role = str(message.get("role", ""))
        content = str(message.get("content", ""))
        source_type = _source_type(content, role)
        for raw_line in content.splitlines():
            line = " ".join(raw_line.split())
            if len(line) < 12 or not TECHNICAL_CUE_RE.search(line):
                continue
            for chunk in _chunks(line, SPAN_CHARS):
                normalized = chunk.lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                spans.append(
                    EvidenceSpan(
                        request_id=str(row["request_id"]),
                        role=role,
                        source_type=source_type,
                        text=chunk,
                    )
                )
                if len(spans) >= max_spans:
                    return spans
    return spans


def _sentence_transformer_encoder(
    model_name: str,
    batch_size: int,
) -> Callable[[list[str]], np.ndarray]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)

    def encode(texts: list[str]) -> np.ndarray:
        if not texts:
            dimension = int(model.get_sentence_embedding_dimension())
            return np.empty((0, dimension), dtype=np.float32)
        return np.asarray(
            model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            ),
            dtype=np.float32,
        )

    return encode


def _source_type(content: str, role: str) -> str:
    lower = content.lower()
    if any(value in lower for value in ("pyproject.toml", "package.json", "go.mod", "cargo.toml")):
        return "manifest"
    if role == "tool":
        return "tool_output"
    if any(value in lower for value in ("traceback", "exception", "error:")):
        return "error"
    return "message"


def _chunks(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    return [text[index : index + size] for index in range(0, len(text), size)]


def _contradicted(text: str, value: str) -> bool:
    lower = text.lower().replace("_", " ")
    value_lower = value.lower().replace("_", " ")
    position = lower.find(value_lower)
    if position < 0:
        return False
    context = lower[max(0, position - 48) : position + len(value_lower) + 48]
    return bool(NEGATION_RE.search(context))
