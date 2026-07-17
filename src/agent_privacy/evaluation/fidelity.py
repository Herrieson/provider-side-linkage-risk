from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


HANDLE_RE = re.compile(
    r"\b(?:user|customer|account|order|reservation|booking|case|ticket|tenant|"
    r"organization|org|project|queue|product|item|flight)[_-]"
    r"(?=[A-Za-z0-9_.:/@-]*\d)[A-Za-z0-9][A-Za-z0-9_.:/@-]{3,}\b",
    re.I,
)


def fidelity_audit(
    source_rows: list[dict[str, Any]], transformed_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    if len(source_rows) != len(transformed_rows):
        raise ValueError("source and transformed row counts differ")
    source_categorical = [_categorical(row) for row in source_rows]
    transformed_categorical = [_categorical(row) for row in transformed_rows]
    source_numeric = np.asarray([_numeric(row) for row in source_rows], dtype=float)
    transformed_numeric = np.asarray([_numeric(row) for row in transformed_rows], dtype=float)
    categorical_js = {
        field: _js_divergence(
            Counter(value[field] for value in source_categorical),
            Counter(value[field] for value in transformed_categorical),
        )
        for field in ("role_sequence", "tool_sequence", "cache_bucket", "model")
    }
    numeric_names = (
        "message_count",
        "tool_message_count",
        "content_characters",
        "token_count",
        "handle_count",
        "context_growth",
    )
    numeric_ks = {
        name: _ks_statistic(source_numeric[:, index], transformed_numeric[:, index])
        for index, name in enumerate(numeric_names)
    } if len(source_rows) else {name: 0.0 for name in numeric_names}
    exact_role_sequences = sum(
        left["role_sequence"] == right["role_sequence"]
        for left, right in zip(source_categorical, transformed_categorical, strict=True)
    )
    exact_tool_sequences = sum(
        left["tool_sequence"] == right["tool_sequence"]
        for left, right in zip(source_categorical, transformed_categorical, strict=True)
    )
    length_ratios = [
        (_numeric(right)[2] / _numeric(left)[2]) if _numeric(left)[2] else 1.0
        for left, right in zip(source_rows, transformed_rows, strict=True)
    ]
    return {
        "requests": len(source_rows),
        "role_sequence_preservation": (
            exact_role_sequences / len(source_rows) if source_rows else 1.0
        ),
        "tool_sequence_preservation": (
            exact_tool_sequences / len(source_rows) if source_rows else 1.0
        ),
        "mean_length_ratio": sum(length_ratios) / len(length_ratios) if length_ratios else 1.0,
        "categorical_js": categorical_js,
        "numeric_ks": numeric_ks,
        "two_sample_auc": _two_sample_auc(source_numeric, transformed_numeric),
    }


def _categorical(row: dict[str, Any]) -> dict[str, str]:
    messages = row.get("messages", [])
    return {
        "role_sequence": "|".join(str(message.get("role", "")) for message in messages),
        "tool_sequence": "|".join(
            str(message.get("name", ""))
            for message in messages
            if message.get("role") == "tool"
        ),
        "cache_bucket": str(row.get("cache_bucket") or ""),
        "model": str(row.get("model") or ""),
    }


def _numeric(row: dict[str, Any]) -> tuple[float, ...]:
    messages = row.get("messages", [])
    contents = [str(message.get("content", "")) for message in messages]
    first_user_index = next(
        (index for index, message in enumerate(messages) if message.get("role") == "user"),
        len(messages),
    )
    return (
        float(len(messages)),
        float(sum(message.get("role") == "tool" for message in messages)),
        float(sum(len(content) for content in contents)),
        float(row.get("token_count", 0)),
        float(sum(len(HANDLE_RE.findall(content)) for content in contents)),
        float(max(len(messages) - first_user_index - 1, 0)),
    )


def _js_divergence(left: Counter[str], right: Counter[str]) -> float:
    keys = set(left) | set(right)
    left_total = sum(left.values())
    right_total = sum(right.values())
    if not keys or not left_total or not right_total:
        return 0.0
    divergence = 0.0
    for key in keys:
        p = left[key] / left_total
        q = right[key] / right_total
        midpoint = (p + q) / 2
        if p:
            divergence += 0.5 * p * math.log2(p / midpoint)
        if q:
            divergence += 0.5 * q * math.log2(q / midpoint)
    return divergence


def _ks_statistic(left: np.ndarray, right: np.ndarray) -> float:
    if not len(left) or not len(right):
        return 0.0
    values = np.sort(np.unique(np.concatenate((left, right))))
    left_sorted = np.sort(left)
    right_sorted = np.sort(right)
    return float(
        max(
            abs(
                np.searchsorted(left_sorted, value, side="right") / len(left_sorted)
                - np.searchsorted(right_sorted, value, side="right") / len(right_sorted)
            )
            for value in values
        )
    )


def _two_sample_auc(source: np.ndarray, transformed: np.ndarray) -> float:
    if not len(source) or not len(transformed):
        return 0.5
    if source.shape == transformed.shape and np.array_equal(
        np.sort(source, axis=0), np.sort(transformed, axis=0)
    ):
        return 0.5
    features = np.vstack((source, transformed))
    labels = np.concatenate((np.zeros(len(source)), np.ones(len(transformed))))
    minimum_class = min(len(source), len(transformed))
    if minimum_class < 2:
        return 0.5
    folds = min(5, minimum_class)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, random_state=7))
    predictions = cross_val_predict(
        model,
        features,
        labels,
        cv=StratifiedKFold(n_splits=folds, shuffle=True, random_state=7),
        method="predict_proba",
    )[:, 1]
    auc = float(roc_auc_score(labels, predictions))
    return max(auc, 1.0 - auc)
