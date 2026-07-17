from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from agent_privacy.data.fidelity import FidelityLevel, RequestLineage, TransformationEdit


WORKSPACE_RE = re.compile(r"(?<=/workspace/)[A-Za-z0-9_.-]+")
REPOSITORY_RE = re.compile(r"(?<=repository=)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:internal|local|prod|corp)\b", re.I)
HANDLE_RE = re.compile(
    r"\b(?:user|customer|account|order|reservation|booking|case|ticket|tenant|"
    r"organization|org|project|queue|product|item|flight)[_-]"
    r"(?=[A-Za-z0-9_.:/@-]*\d)[A-Za-z0-9][A-Za-z0-9_.:/@-]{3,}\b",
    re.I,
)


@dataclass(frozen=True)
class TraceTransformOptions:
    scope: str = "dataset"
    categories: tuple[str, ...] = ("workspace", "repository", "domain", "typed_handle")


def transform_trace_rows(
    rows: list[dict[str, Any]], options: TraceTransformOptions | None = None
) -> tuple[list[dict[str, Any]], list[RequestLineage]]:
    options = options or TraceTransformOptions()
    counters: dict[str, int] = defaultdict(int)
    mapping: dict[tuple[str, str, str], str] = {}
    transformed_rows: list[dict[str, Any]] = []
    lineage_rows: list[RequestLineage] = []
    for row in rows:
        transformed = deepcopy(row)
        edits: list[TransformationEdit] = []
        scope = options.scope if options.scope == "dataset" else str(row["request_id"])
        for message_index, message in enumerate(transformed.get("messages", [])):
            source_content = str(message.get("content", ""))
            content_hash = _hash(source_content)
            candidates = _span_candidates(source_content, options.categories)
            accepted = _non_overlapping(candidates)
            replacements: list[tuple[int, int, str, str, str]] = []
            for start, end, category, original in accepted:
                key = (scope, category, original.lower())
                if key not in mapping:
                    counters[category] += 1
                    mapping[key] = _replacement(category, original, counters[category])
                replacement = mapping[key]
                replacements.append((start, end, category, original, replacement))
                edits.append(
                    TransformationEdit(
                        message_index=message_index,
                        category=category,
                        start=start,
                        end=end,
                        original=original,
                        replacement=replacement,
                        source_content_hash=content_hash,
                    )
                )
            message["content"] = apply_content_edits(source_content, replacements)
        transformed_rows.append(transformed)
        lineage_rows.append(
            RequestLineage(
                request_id=str(row["request_id"]),
                source_request_hash=_request_hash(row),
                transformed_request_hash=_request_hash(transformed),
                fidelity_level=FidelityLevel.F0,
                edits=tuple(edits),
            )
        )
    return transformed_rows, lineage_rows


def apply_content_edits(
    content: str, edits: list[tuple[int, int, str, str, str]]
) -> str:
    transformed = content
    for start, end, _category, original, replacement in sorted(edits, reverse=True):
        if content[start:end] != original:
            raise ValueError("edit no longer matches its declared source span")
        transformed = transformed[:start] + replacement + transformed[end:]
    return transformed


def validate_trace_preservation(
    source_rows: list[dict[str, Any]],
    transformed_rows: list[dict[str, Any]],
    lineage_rows: list[RequestLineage],
) -> dict[str, int | float]:
    if not (len(source_rows) == len(transformed_rows) == len(lineage_rows)):
        raise ValueError("source, transformed, and lineage row counts differ")
    total_chars = 0
    edited_chars = 0
    total_edits = 0
    for source, transformed, lineage in zip(
        source_rows, transformed_rows, lineage_rows, strict=True
    ):
        if not (
            source["request_id"] == transformed["request_id"] == lineage.request_id
        ):
            raise ValueError("request identities are not aligned")
        if _request_hash(source) != lineage.source_request_hash:
            raise ValueError("source request hash mismatch")
        if _request_hash(transformed) != lineage.transformed_request_hash:
            raise ValueError("transformed request hash mismatch")
        if source.get("tool_schemas", []) != transformed.get("tool_schemas", []):
            raise ValueError("tool schemas changed")
        source_messages = source.get("messages", [])
        transformed_messages = transformed.get("messages", [])
        if len(source_messages) != len(transformed_messages):
            raise ValueError("message count changed")
        for source_message, transformed_message in zip(
            source_messages, transformed_messages, strict=True
        ):
            if source_message.get("role") != transformed_message.get("role"):
                raise ValueError("message role changed")
            if source_message.get("name") != transformed_message.get("name"):
                raise ValueError("message/tool name changed")
            total_chars += len(str(source_message.get("content", "")))
        for message_index in range(len(source_messages)):
            source_content = str(source_messages[message_index].get("content", ""))
            declared = [
                edit for edit in lineage.edits if edit.message_index == message_index
            ]
            replacements = [
                (edit.start, edit.end, edit.category, edit.original, edit.replacement)
                for edit in declared
            ]
            reproduced = apply_content_edits(source_content, replacements)
            if reproduced != str(transformed_messages[message_index].get("content", "")):
                raise ValueError("declared edits do not reproduce transformed content")
            if any(_hash(source_content) != edit.source_content_hash for edit in declared):
                raise ValueError("edit source content hash mismatch")
            edited_chars += sum(edit.end - edit.start for edit in declared)
            total_edits += len(declared)
    return {
        "requests": len(source_rows),
        "edits": total_edits,
        "source_characters": total_chars,
        "edited_source_characters": edited_chars,
        "edited_character_ratio": edited_chars / total_chars if total_chars else 0.0,
    }


def _span_candidates(
    content: str, categories: tuple[str, ...]
) -> list[tuple[int, int, str, str]]:
    patterns = {
        "workspace": WORKSPACE_RE,
        "repository": REPOSITORY_RE,
        "domain": DOMAIN_RE,
        "typed_handle": HANDLE_RE,
    }
    candidates: list[tuple[int, int, str, str]] = []
    for category in categories:
        pattern = patterns.get(category)
        if pattern is None:
            raise ValueError(f"unsupported transformation category: {category}")
        for match in pattern.finditer(content):
            candidates.append((match.start(), match.end(), category, match.group(0)))
    return candidates


def _non_overlapping(
    candidates: list[tuple[int, int, str, str]],
) -> list[tuple[int, int, str, str]]:
    accepted: list[tuple[int, int, str, str]] = []
    for candidate in sorted(candidates, key=lambda item: (item[0], -(item[1] - item[0]), item[2])):
        start, end, _category, _original = candidate
        if any(start < other_end and end > other_start for other_start, other_end, *_ in accepted):
            continue
        accepted.append(candidate)
    return accepted


def _replacement(category: str, original: str, index: int) -> str:
    if category == "workspace":
        return f"workspace_{index:04d}"
    if category == "repository":
        return f"owner_{index:04d}/repo_{index:04d}"
    if category == "domain":
        return f"service-{index:04d}.internal"
    kind = re.split(r"[_-]", original, maxsplit=1)[0].lower()
    return f"{kind}_p{index:06d}"


def _request_hash(row: dict[str, Any]) -> str:
    return _hash(json.dumps(row, sort_keys=True, separators=(",", ":")))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
