from __future__ import annotations

import re
from typing import Any

from agent_privacy.features.extract import DOMAIN_RE, PATH_RE, request_text


RAW_SECRET_RE = re.compile(r"\b(?:sk|pk|ghp|xoxb|AKIA|ASIA)[-_A-Za-z0-9]{12,}\b")
SECRET_PLACEHOLDER_RE = re.compile(r"\[(?:SECRET|CONNECTION_STRING)\]")
REPOSITORY_FIELD_RE = re.compile(r"\brepository=(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+|\[REPO_REMOVED\])\b")
WORKSPACE_PATH_RE = re.compile(r"/workspace/[A-Za-z0-9_.-]+(?:__[A-Za-z0-9_.-]+)?[A-Za-z0-9_./-]*")


def summarize_utility(
    original_rows: list[dict[str, Any]],
    transformed_rows: list[dict[str, Any]],
    *,
    defense: str,
    ablation: str,
) -> dict[str, Any]:
    original_by_id = {row["request_id"]: row for row in original_rows}
    kept_pairs = [
        (original_by_id[row["request_id"]], row)
        for row in transformed_rows
        if row.get("request_id") in original_by_id
    ]
    original_token_count = sum(_token_count(row) for row, _ in kept_pairs)
    transformed_token_count = sum(_token_count(row) for _, row in kept_pairs)
    original_message_count = sum(len(row.get("messages", [])) for row, _ in kept_pairs)
    transformed_message_count = sum(len(row.get("messages", [])) for _, row in kept_pairs)
    original_chars = sum(len(request_text(row)) for row, _ in kept_pairs)
    transformed_chars = sum(len(request_text(row)) for _, row in kept_pairs)
    original_tool_chars = sum(_tool_chars(row) for row, _ in kept_pairs)
    transformed_tool_chars = sum(_tool_chars(row) for _, row in kept_pairs)

    original_markers = _marker_counts(row for row, _ in kept_pairs)
    transformed_markers = _marker_counts(row for _, row in kept_pairs)
    row: dict[str, Any] = {
        "defense": defense,
        "ablation": ablation,
        "requests_original": len(original_rows),
        "requests_transformed": len(transformed_rows),
        "requests_compared": len(kept_pairs),
        "tokens_original": original_token_count,
        "tokens_transformed": transformed_token_count,
        "token_retention": _ratio(transformed_token_count, original_token_count),
        "messages_original": original_message_count,
        "messages_transformed": transformed_message_count,
        "message_retention": _ratio(transformed_message_count, original_message_count),
        "chars_original": original_chars,
        "chars_transformed": transformed_chars,
        "char_retention": _ratio(transformed_chars, original_chars),
        "tool_chars_original": original_tool_chars,
        "tool_chars_transformed": transformed_tool_chars,
        "tool_char_retention": _ratio(transformed_tool_chars, original_tool_chars),
    }
    for key, original_value in original_markers.items():
        transformed_value = transformed_markers[key]
        row[f"{key}_original"] = original_value
        row[f"{key}_transformed"] = transformed_value
        row[f"{key}_removed"] = max(0, original_value - transformed_value)
    return row


def _marker_counts(rows: Any) -> dict[str, int]:
    counts = {
        "path_count": 0,
        "workspace_path_count": 0,
        "domain_count": 0,
        "repository_field_count": 0,
        "raw_secret_count": 0,
        "secret_placeholder_count": 0,
    }
    for row in rows:
        text = request_text(row)
        counts["path_count"] += len(PATH_RE.findall(text.lower()))
        counts["workspace_path_count"] += len(WORKSPACE_PATH_RE.findall(text))
        counts["domain_count"] += len(DOMAIN_RE.findall(text.lower()))
        counts["repository_field_count"] += len(REPOSITORY_FIELD_RE.findall(text))
        counts["raw_secret_count"] += len(RAW_SECRET_RE.findall(text))
        counts["secret_placeholder_count"] += len(SECRET_PLACEHOLDER_RE.findall(text))
    return counts


def _tool_chars(row: dict[str, Any]) -> int:
    return sum(
        len(message.get("content", ""))
        for message in row.get("messages", [])
        if message.get("role") == "tool"
    )


def _token_count(row: dict[str, Any]) -> int:
    return sum(len(message.get("content", "").split()) for message in row.get("messages", []))


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
