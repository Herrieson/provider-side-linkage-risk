from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from agent_privacy.io import iter_jsonl


PATH_RE = re.compile(r"/(?:home|srv|opt|workspace|tmp)/[A-Za-z0-9_./-]+")
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:internal|local|prod|corp)\b")
TRACE_RE = re.compile(r"\btrace-[a-z0-9-]+(?:-[a-z0-9-]+)+\b")
SYNTH_SECRET_RE = re.compile(r"\bsk-test-[A-Za-z0-9]{16,}\b")
IDENT_RE = re.compile(r"\b[a-z][a-z0-9]+(?:[-_][a-z0-9]+)+\b")
REPOSITORY_FIELD_RE = re.compile(r"\brepository=([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)\b")
BUSINESS_KV_RE = re.compile(
    r"\b("
    r"tenant|customer_ref|account_cache|case_id|queue|service_line|internal_domain|"
    r"loyalty_tier|region"
    r")=([A-Za-z0-9_.:/@-]+)"
)
BUSINESS_OBJECT_RE = re.compile(
    r"\b(order|reservation|product)[_-]("
    r"[a-z][a-z0-9]*\d{2}-(?:airline|retail)-[a-z]+(?:-[a-z]+)*-\d+"
    r")\b",
    re.IGNORECASE,
)
NATURAL_HANDLE_RE = re.compile(
    r"\b(?P<kind>user|username|customer|account|order|reservation|booking|case|ticket|"
    r"tenant|organization|org|project|queue|product|item|flight)"
    r"(?:\s+|[_-])(?:(?:id|number|ref(?:erence)?|code)\s*)?"
    r"(?:is\s+|[:=]\s*)(?P<value>[A-Za-z0-9][A-Za-z0-9_.:/@-]{3,})\b",
    re.IGNORECASE,
)
PREFIXED_HANDLE_RE = re.compile(
    r"\b(?P<kind>user|customer|account|order|reservation|booking|case|ticket|"
    r"tenant|organization|org|project|queue|product|item|flight)"
    r"[_-](?P<value>[A-Za-z0-9][A-Za-z0-9_.:/@-]{3,})\b",
    re.IGNORECASE,
)
HANDLE_COMMON_VALUES = {
    "active",
    "available",
    "cancelled",
    "customer",
    "default",
    "economy",
    "false",
    "flight",
    "inactive",
    "none",
    "null",
    "number",
    "pending",
    "product",
    "regular",
    "reservation",
    "service",
    "true",
    "type",
    "unknown",
}
HANDLE_SECRET_MARKERS = {"api_key", "password", "secret", "token"}
HANDLE_USER_KINDS = {"account", "customer", "email", "member", "profile", "user", "username"}
HANDLE_PROJECT_KINDS = {
    "booking",
    "case",
    "order",
    "project",
    "queue",
    "repository",
    "reservation",
    "service",
    "ticket",
    "workspace",
}
HANDLE_ORG_KINDS = {"domain", "namespace", "org", "organization", "tenant"}
HANDLE_CONTEXT_KINDS = {"flight", "item", "product"}
WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_./:-]{2,}")
TEXT_FEATURE_WINDOW_CHARS = 80_000
MAX_SHINGLES = 8_000
MAX_WORDS = 5_000
MAX_STABLE_HANDLES = 512
MAX_SHARED_RESOURCE_HANDLES = 256
HASHED_SHINGLE_HEX_CHARS = 16
STOP_WORDS = {
    "about",
    "after",
    "also",
    "assistant",
    "because",
    "before",
    "content",
    "could",
    "error",
    "from",
    "have",
    "help",
    "into",
    "message",
    "need",
    "please",
    "request",
    "result",
    "should",
    "system",
    "that",
    "there",
    "this",
    "tool",
    "user",
    "using",
    "with",
    "would",
}


@dataclass(frozen=True)
class RequestFeatures:
    request_id: str
    timestamp_minute: int
    token_count: int
    words: frozenset[str]
    shingles: frozenset[str]
    identifiers: frozenset[str]
    paths: frozenset[str]
    usernames: frozenset[str]
    domains: frozenset[str]
    traces: frozenset[str]
    cache_bucket: str
    semantic_signatures: frozenset[str]
    tool_fingerprint: str
    system_fingerprint: str


@dataclass(frozen=True)
class FeatureOptions:
    include_shingles: bool = True
    include_domains: bool = True
    include_traces: bool = True
    include_paths: bool = True
    include_usernames: bool = True
    include_repo_ids: bool = True
    include_identifiers: bool = True
    include_tool_fingerprint: bool = True
    include_system_fingerprint: bool = True
    include_time: bool = True
    include_length: bool = True
    include_cache: bool = True
    include_semantic_signatures: bool = True
    text_feature_window_chars: int = TEXT_FEATURE_WINDOW_CHARS
    max_shingles: int = MAX_SHINGLES
    max_words: int = MAX_WORDS
    hash_shingles: bool = False
    scan_full_text: bool = True


def extract_features(
    rows: list[dict[str, Any]], options: FeatureOptions | None = None
) -> dict[str, RequestFeatures]:
    return extract_features_from_rows(rows, options=options)


def extract_features_from_rows(
    rows: Iterable[dict[str, Any]], options: FeatureOptions | None = None
) -> dict[str, RequestFeatures]:
    options = options or FeatureOptions()
    return {row["request_id"]: extract_request_features(row, options=options) for row in rows}


def extract_features_from_jsonl(
    path: Path,
    options: FeatureOptions | None = None,
    request_ids: set[str] | None = None,
) -> dict[str, RequestFeatures]:
    rows = iter_jsonl(path)
    if request_ids is not None:
        rows = (row for row in rows if row.get("request_id") in request_ids)
    return extract_features_from_rows(rows, options=options)


def extract_request_features(
    row: dict[str, Any], options: FeatureOptions | None = None
) -> RequestFeatures:
    options = options or FeatureOptions()
    text = request_text(row)
    lower = text.lower()
    feature_text = _bounded_text(lower, options.text_feature_window_chars)
    scan_text = lower if options.scan_full_text else feature_text
    paths = frozenset(PATH_RE.findall(scan_text)) if options.include_paths else frozenset()
    usernames = (
        frozenset(_username_from_path(path) for path in paths if _username_from_path(path))
        if options.include_usernames
        else frozenset()
    )
    domains = frozenset(DOMAIN_RE.findall(scan_text)) if options.include_domains else frozenset()
    traces = frozenset(TRACE_RE.findall(scan_text)) if options.include_traces else frozenset()
    identifiers = set(IDENT_RE.findall(feature_text)) if options.include_identifiers else set()
    identifiers.update(paths)
    identifiers.update(domains)
    identifiers.update(traces)
    if options.include_repo_ids:
        identifiers.update(_repo_identifiers(scan_text, paths))
    identifiers.update(_business_identifiers(scan_text))
    identifiers.update(extract_stable_content_handles(row))
    words = (
        frozenset(_words(feature_text, max_words=options.max_words))
        if options.include_semantic_signatures
        else frozenset()
    )
    shingles = (
        frozenset(
            _shingles(
                feature_text,
                5,
                max_shingles=options.max_shingles,
                hash_values=options.hash_shingles,
            )
        )
        if options.include_shingles
        else frozenset()
    )
    system = "\n".join(m.get("content", "") for m in row.get("messages", []) if m.get("role") == "system")
    return RequestFeatures(
        request_id=row["request_id"],
        timestamp_minute=_timestamp_minute(row["timestamp"]) if options.include_time else 0,
        token_count=int(row.get("token_count", 0)) if options.include_length else 0,
        words=words,
        shingles=shingles,
        identifiers=frozenset(i for i in identifiers if not SYNTH_SECRET_RE.fullmatch(i)),
        paths=paths,
        usernames=usernames,
        domains=domains,
        traces=traces,
        cache_bucket=str(row.get("cache_bucket") or "") if options.include_cache else "",
        semantic_signatures=(
            frozenset(_semantic_signatures(words)) if options.include_semantic_signatures else frozenset()
        ),
        tool_fingerprint=_fingerprint(row.get("tool_schemas", []))
        if options.include_tool_fingerprint
        else "",
        system_fingerprint=_fingerprint(system) if options.include_system_fingerprint else "",
    )


def extract_business_identifiers(row: dict[str, Any]) -> frozenset[str]:
    """Extract stable typed linkage anchors without materializing text features."""

    anchors = _business_identifiers(request_text(row).lower())
    anchors.update(extract_stable_content_handles(row))
    return frozenset(anchors)


def extract_stable_content_handles(row: dict[str, Any]) -> frozenset[str]:
    """Extract typed persistent handles from structured tool content and explicit ID phrases."""

    handles: set[str] = set()
    for message in row.get("messages", []):
        if message.get("role") == "system":
            continue
        content = str(message.get("content", ""))
        structured = _maybe_structured_content(content)
        if structured is not None:
            _collect_structured_handles(structured, (), handles)
        for pattern in (NATURAL_HANDLE_RE, PREFIXED_HANDLE_RE):
            for match in pattern.finditer(content):
                _add_stable_handle(
                    handles,
                    kind=match.group("kind"),
                    value=match.group("value"),
                )
    strong = sorted(value for value in handles if not value.startswith("stable_context:"))
    shared = sorted(value for value in handles if value.startswith("stable_context:"))[
        :MAX_SHARED_RESOURCE_HANDLES
    ]
    return frozenset((strong + shared)[:MAX_STABLE_HANDLES])


def request_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for message in row.get("messages", []):
        name = message.get("name")
        role = message.get("role", "")
        content = message.get("content", "")
        parts.append(f"{role}:{name or ''}:{content}")
    return "\n".join(parts)


def jaccard(left: set[str] | frozenset[str], right: set[str] | frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    inter = len(left & right)
    if inter == 0:
        return 0.0
    return inter / len(left | right)


def overlap_count(left: set[str] | frozenset[str], right: set[str] | frozenset[str]) -> int:
    if not left or not right:
        return 0
    return len(left & right)


def _shingles(
    text: str, size: int, max_shingles: int | None = None, *, hash_values: bool = False
) -> set[str]:
    tokens = [w.lower() for w in WORD_RE.findall(text)]
    if len(tokens) < size:
        return {_hash_feature(token) for token in tokens} if hash_values else set(tokens)
    shingles: set[str] = set()
    for i in range(len(tokens) - size + 1):
        shingle = " ".join(tokens[i : i + size])
        shingles.add(_hash_feature(shingle) if hash_values else shingle)
        if max_shingles is not None and len(shingles) >= max_shingles:
            break
    return shingles


def _words(text: str, max_words: int | None = None) -> set[str]:
    words: set[str] = set()
    for raw in WORD_RE.findall(text):
        word = _normalize_word(raw)
        if not word or word in STOP_WORDS:
            continue
        words.add(word)
        if max_words is not None and len(words) >= max_words:
            break
    return words


def _normalize_word(value: str) -> str:
    word = value.lower().strip("._:-/")
    if len(word) < 3 or len(word) > 80:
        return ""
    if "/" in word and not word.startswith(("/workspace/", "/home/", "/tmp/")):
        word = word.rsplit("/", 1)[-1]
    return word


def _semantic_signatures(words: frozenset[str], bands: int = 8) -> set[str]:
    if not words:
        return set()
    signatures: set[str] = set()
    ordered = sorted(words)
    for band in range(bands):
        ranked = sorted(
            ordered,
            key=lambda word, band=band: hashlib.sha1(f"{band}:{word}".encode("utf-8")).hexdigest(),
        )
        head = ranked[:4]
        if len(head) >= 2:
            signatures.add(f"sem:{band}:{_fingerprint('|'.join(head))}")
    return signatures


def _bounded_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n[...middle omitted for feature budget...]\n" + text[-half:]


def _username_from_path(path: str) -> str | None:
    match = re.match(r"/home/([^/]+)/", path)
    return match.group(1) if match else None


def _repo_identifiers(text: str, paths: frozenset[str]) -> set[str]:
    identifiers: set[str] = set()
    for owner, repo in REPOSITORY_FIELD_RE.findall(text):
        identifiers.add(f"repo_owner:{owner.lower()}")
        identifiers.add(f"repo_name:{repo.lower()}")
        identifiers.add(f"repo_full:{owner.lower()}/{repo.lower()}")
    for path in paths:
        match = re.search(r"/workspace/([^/\s]+)", path)
        if not match:
            continue
        slug = match.group(1)
        if "__" in slug:
            owner, repo = slug.split("__", 1)
            identifiers.add(f"repo_owner:{owner.lower()}")
            identifiers.add(f"repo_name:{repo.lower()}")
            identifiers.add(f"repo_full:{owner.lower()}/{repo.lower()}")
    return identifiers


def _business_identifiers(text: str) -> set[str]:
    identifiers: set[str] = set()
    for key, value in BUSINESS_KV_RE.findall(text):
        normalized = _normalize_business_value(value)
        if not normalized:
            continue
        if key in {"customer_ref", "account_cache"}:
            identifiers.add(f"business_user:{key}:{normalized}")
        elif key == "queue":
            identifiers.add(f"business_project:{key}:{normalized}")
        elif key == "internal_domain":
            identifiers.add(f"business_project:{key}:{normalized}")
            identifiers.add(f"business_org:{key}:{normalized}")
        elif key == "tenant":
            identifiers.add(f"business_org:{key}:{normalized}")
        if key == "account_cache":
            tenant = _tenant_from_account_cache(normalized)
            if tenant:
                identifiers.add(f"business_org:tenant:{tenant}")
    for object_type, value in BUSINESS_OBJECT_RE.findall(text):
        normalized = _normalize_business_value(value)
        if normalized:
            identifiers.add(f"business_project:{object_type.lower()}:{normalized}")
    return identifiers


def _maybe_structured_content(content: str) -> Any | None:
    stripped = content.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        return None


def _collect_structured_handles(
    value: Any,
    path: tuple[str, ...],
    handles: set[str],
) -> None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = _normalize_handle_key(str(raw_key))
            child_path = (*path, key)
            if isinstance(child, (str, int)) and not isinstance(child, bool):
                _add_stable_handle(handles, kind=_handle_kind(key, path), value=str(child))
            _collect_structured_handles(child, child_path, handles)
    elif isinstance(value, list):
        for child in value:
            _collect_structured_handles(child, path, handles)


def _normalize_handle_key(key: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
    return key[:-1] if key.endswith("s") and len(key) > 4 else key


def _handle_kind(key: str, path: tuple[str, ...]) -> str:
    if any(marker in key for marker in HANDLE_SECRET_MARKERS):
        return ""
    candidate = key
    for suffix in ("_identifier", "_reference", "_number", "_code", "_ref", "_id"):
        if candidate.endswith(suffix):
            candidate = candidate[: -len(suffix)]
            break
    if candidate == "id":
        for parent in reversed(path):
            parent_kind = _handle_kind(parent, ())
            if parent_kind:
                return parent_kind
        return ""
    aliases = {
        "repo": "repository",
        "organisation": "organization",
        "userid": "user",
    }
    candidate = aliases.get(candidate, candidate)
    supported = HANDLE_USER_KINDS | HANDLE_PROJECT_KINDS | HANDLE_ORG_KINDS | HANDLE_CONTEXT_KINDS
    return candidate if candidate in supported else ""


def _add_stable_handle(handles: set[str], *, kind: str, value: str) -> None:
    normalized_kind = _handle_kind(_normalize_handle_key(kind), ())
    normalized_value = _normalize_stable_handle_value(value)
    if not normalized_kind or not normalized_value:
        return
    if normalized_kind in HANDLE_USER_KINDS:
        level = "user"
    elif normalized_kind in HANDLE_PROJECT_KINDS:
        level = "project"
    elif normalized_kind in HANDLE_ORG_KINDS:
        level = "org"
    else:
        level = "context"
    handles.add(f"stable_{level}:{normalized_kind}:{normalized_value}")


def _normalize_stable_handle_value(value: str) -> str:
    raw = value.strip().strip("._-/:@;,'\"`()[]{}")
    normalized = raw.lower()
    if (
        len(normalized) < 4
        or len(normalized) > 120
        or normalized in HANDLE_COMMON_VALUES
        or any(character.isspace() for character in normalized)
    ):
        return ""
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.:/@-]*", normalized):
        return ""
    stable_shape = (
        any(character.isdigit() for character in normalized)
        or any(character in "_.:/@-" for character in normalized)
        or (raw.isupper() and len(raw) >= 5)
    )
    return normalized if stable_shape else ""


def _normalize_business_value(value: str) -> str:
    value = value.lower().strip().strip("._-/:@;,'\"`()[]{}")
    if len(value) < 3 or len(value) > 120:
        return ""
    return value


def _tenant_from_account_cache(value: str) -> str:
    if ":acct:" not in value:
        return ""
    tenant = value.split(":acct:", 1)[0]
    return tenant.rsplit(":", 1)[-1]


def _timestamp_minute(value: str) -> int:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(dt.timestamp() // 60)


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()[:12]


def _hash_feature(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:HASHED_SHINGLE_HEX_CHARS]
