from __future__ import annotations

import copy
import random
import re
from datetime import datetime, timedelta
from typing import Any


SECRET_RE = re.compile(r"\b(?:sk|pk|ghp|xoxb|AKIA|ASIA)[-_A-Za-z0-9]{12,}\b")
CONNECTION_RE = re.compile(r"\b(?:postgres|mysql|redis|mongodb)://[^\s]+", re.IGNORECASE)
PATH_RE = re.compile(r"/(?:home|srv|opt|workspace|tmp)/[A-Za-z0-9_./-]+")
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:internal|local|prod|corp)\b", re.IGNORECASE)
HYBRID_ID_RE = re.compile(r"\b[a-z][a-z0-9]+(?:[-_][a-z0-9]+)+\b")
WORKSPACE_PATH_RE = re.compile(r"/workspace/[A-Za-z0-9_.-]+(?:__[A-Za-z0-9_.-]+)?[A-Za-z0-9_./-]*")
WORKSPACE_SLUG_RE = re.compile(r"(?<=/workspace/)[A-Za-z0-9_.-]+(?:__[A-Za-z0-9_.-]+)?")


def apply_defense(rows: list[dict[str, Any]], defense: str, seed: int = 7) -> list[dict[str, Any]]:
    if defense == "M0":
        return copy.deepcopy(rows)
    if defense == "M1":
        return [_map_text(row, _secret_filter, defense) for row in rows]
    if defense == "M2":
        return _entity_redaction(rows, defense)
    if defense == "M3":
        return [_context_minimize(row, defense) for row in rows]
    if defense == "M4":
        return _broker_mix(rows, seed, defense)
    if defense == "M7_WORKSPACE_STABLE":
        return _workspace_slug_pseudonymize(rows, defense=defense, scope="stable")
    if defense == "M8_WORKSPACE_SESSION":
        return _workspace_slug_pseudonymize(rows, defense=defense, scope="session")
    if defense == "M9_PATH_TYPE_ONLY":
        return [_map_text(row, _workspace_path_type_only, defense) for row in rows]
    if defense == "M6":
        current = apply_defense(rows, "M1", seed)
        current = apply_defense(current, "M2", seed)
        current = apply_defense(current, "M3", seed)
        current = apply_defense(current, "M4", seed)
        for row in current:
            row["defense"] = "M6"
        return current
    raise ValueError(f"unknown defense: {defense}")


def _map_text(row: dict[str, Any], func, defense: str) -> dict[str, Any]:
    out = copy.deepcopy(row)
    for message in out.get("messages", []):
        message["content"] = func(message.get("content", ""))
    out["defense"] = defense
    out["token_count"] = _token_count(out)
    return out


def _secret_filter(text: str) -> str:
    text = SECRET_RE.sub("[SECRET]", text)
    return CONNECTION_RE.sub("[CONNECTION_STRING]", text)


def _entity_redaction(rows: list[dict[str, Any]], defense: str) -> list[dict[str, Any]]:
    mapping: dict[str, str] = {}
    counters = {"PATH": 0, "DOMAIN": 0, "ID": 0}

    def repl(kind: str, value: str) -> str:
        key = f"{kind}:{value.lower()}"
        if key not in mapping:
            counters[kind] += 1
            mapping[key] = f"[{kind}_{counters[kind]:04d}]"
        return mapping[key]

    def redact(text: str) -> str:
        text = PATH_RE.sub(lambda m: repl("PATH", m.group(0)), text)
        text = DOMAIN_RE.sub(lambda m: repl("DOMAIN", m.group(0)), text)
        return HYBRID_ID_RE.sub(lambda m: repl("ID", m.group(0)), text)

    return [_map_text(row, redact, defense) for row in rows]


def _workspace_slug_pseudonymize(
    rows: list[dict[str, Any]], *, defense: str, scope: str
) -> list[dict[str, Any]]:
    stable_mapping: dict[str, str] = {}
    counter = 0

    def stable_repl(value: str) -> str:
        nonlocal counter
        key = value.lower()
        if key not in stable_mapping:
            counter += 1
            stable_mapping[key] = f"workspace_{counter:04d}"
        return stable_mapping[key]

    transformed = []
    for row_idx, row in enumerate(rows, start=1):
        row_mapping: dict[str, str] = {}

        def row_repl(value: str) -> str:
            key = value.lower()
            if key not in row_mapping:
                row_mapping[key] = f"workspace_req_{row_idx:06d}_{len(row_mapping) + 1:03d}"
            return row_mapping[key]

        repl = stable_repl if scope == "stable" else row_repl

        def transform(text: str) -> str:
            return WORKSPACE_SLUG_RE.sub(lambda m: repl(m.group(0)), text)

        transformed.append(_map_text(row, transform, defense))
    return transformed


def _workspace_path_type_only(text: str) -> str:
    return WORKSPACE_PATH_RE.sub("[WORKSPACE_PATH]", text)


def _context_minimize(row: dict[str, Any], defense: str) -> dict[str, Any]:
    out = copy.deepcopy(row)
    minimized = []
    for message in out.get("messages", []):
        role = message.get("role")
        content = message.get("content", "")
        if role == "system":
            content = "You are an LLM coding agent. Keep context minimal."
        elif role == "user":
            content = _drop_prior_context(content)
        elif role == "assistant":
            content = "I will inspect only the relevant failure and patch the minimal scope."
        elif role == "tool":
            lines = [line for line in content.splitlines() if line.strip()]
            content = "\n".join(lines[:2])
        new_message = dict(message)
        new_message["content"] = content
        minimized.append(new_message)
    out["messages"] = minimized
    out["defense"] = defense
    out["token_count"] = _token_count(out)
    return out


def _broker_mix(rows: list[dict[str, Any]], seed: int, defense: str) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    mixed = copy.deepcopy(rows)
    for row in mixed:
        dt = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        dt += timedelta(minutes=rng.randint(0, 180))
        row["timestamp"] = dt.isoformat().replace("+00:00", "Z")
        row["token_count"] = _length_bucket(int(row.get("token_count", 0)))
        row["defense"] = defense
    mixed.sort(key=lambda row: (row["timestamp"], row["request_id"]))
    return mixed


def _drop_prior_context(text: str) -> str:
    marker = "\nPrior context:\n"
    if marker in text:
        text = text.split(marker, 1)[0] + "\nPrior context: [LOCAL_SUMMARY_REDACTED]"
    return text


def _length_bucket(value: int) -> int:
    if value <= 64:
        return 64
    if value <= 128:
        return 128
    if value <= 256:
        return 256
    if value <= 512:
        return 512
    return 1024


def _token_count(row: dict[str, Any]) -> int:
    return sum(len(message.get("content", "").split()) for message in row.get("messages", []))
