from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from agent_privacy.features.extract import request_text

MIN_TOKEN_LENGTH = 4
STOP_TOKENS = {
    "api",
    "app",
    "build",
    "core",
    "docs",
    "java",
    "make",
    "node",
    "python",
    "repo",
    "test",
    "tests",
}


def build_profile_watchlist(
    profiles: dict[str, dict[str, Any]],
    *,
    max_tokens_per_profile: int = 20,
) -> dict[str, dict[str, Any]]:
    watchlist: dict[str, dict[str, Any]] = {}
    for cluster_id, profile in profiles.items():
        tokens: list[dict[str, Any]] = []
        evidence = profile.get("evidence", {})
        for field, values in profile.get("fields", {}).items():
            for value in values:
                token = _watch_token(value)
                if token is None:
                    continue
                ids = evidence.get(field, {}).get(value, [])
                tokens.append(
                    {
                        "token": token,
                        "field": field,
                        "evidence_request_ids": ids,
                        "evidence_count": len(ids),
                    }
                )
        tokens.sort(key=lambda row: (-int(row["evidence_count"]), row["field"], row["token"]))
        watchlist[cluster_id] = {
            "request_ids": profile.get("request_ids", []),
            "tokens": tokens[:max_tokens_per_profile],
        }
    return watchlist


def score_watchlist(
    watchlist: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    labels: dict[str, str],
    *,
    truth_level: str = "org",
) -> list[dict[str, Any]]:
    truth_field = {
        "session": "workflow_id",
        "user": "user_id",
        "project": "project_id",
        "org": "org_id",
    }[truth_level]
    truth_by_id = {row["request_id"]: row for row in truth_rows}
    label_to_truth = _majority_truth_by_label(labels, truth_by_id, truth_field)
    truth_to_requests: dict[str, set[str]] = defaultdict(set)
    for request_id, truth in truth_by_id.items():
        value = truth.get(truth_field)
        if value is not None:
            truth_to_requests[str(value)].add(request_id)
    token_index = _token_index(watchlist, rows)

    out: list[dict[str, Any]] = []
    for cluster_id, item in watchlist.items():
        tokens = [token["token"] for token in item.get("tokens", [])]
        target_truth = label_to_truth.get(cluster_id)
        matched = _matched_requests(tokens, token_index)
        target_requests = truth_to_requests.get(target_truth or "", set())
        true_positive = len(matched & target_requests)
        precision = true_positive / len(matched) if matched else 0.0
        recall = true_positive / len(target_requests) if target_requests else 0.0
        out.append(
            {
                "cluster_id": cluster_id,
                "truth_level": truth_level,
                "target_truth": target_truth,
                "watch_tokens": len(tokens),
                "matched_requests": len(matched),
                "target_requests": len(target_requests),
                "true_positive": true_positive,
                "precision": precision,
                "recall": recall,
                "f1": _f1(precision, recall),
            }
        )
    return out


def summarize_watchlist_scores(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    return [
        {
            "profiles": len(rows),
            "mean_precision": _mean([float(row["precision"]) for row in rows]),
            "mean_recall": _mean([float(row["recall"]) for row in rows]),
            "mean_f1": _mean([float(row["f1"]) for row in rows]),
            "matched_requests": sum(int(row["matched_requests"]) for row in rows),
            "true_positive": sum(int(row["true_positive"]) for row in rows),
        }
    ]


def _majority_truth_by_label(
    labels: dict[str, str],
    truth_by_id: dict[str, dict[str, Any]],
    truth_field: str,
) -> dict[str, str]:
    counts_by_label: dict[str, Counter[str]] = defaultdict(Counter)
    for request_id, label in labels.items():
        truth = truth_by_id.get(request_id, {})
        value = truth.get(truth_field)
        if value is not None:
            counts_by_label[label][str(value)] += 1
    return {
        label: counts.most_common(1)[0][0]
        for label, counts in counts_by_label.items()
        if counts
    }


def _token_index(
    watchlist: dict[str, dict[str, Any]], rows: list[dict[str, Any]]
) -> dict[str, set[str]]:
    tokens = {
        token["token"]
        for item in watchlist.values()
        for token in item.get("tokens", [])
        if token.get("token")
    }
    out = {token: set() for token in tokens}
    for row in rows:
        text = request_text(row).lower()
        for token in tokens:
            if token in text:
                out[token].add(row["request_id"])
    return out


def _matched_requests(tokens: list[str], token_index: dict[str, set[str]]) -> set[str]:
    matched: set[str] = set()
    for token in tokens:
        matched.update(token_index.get(token, set()))
    return matched


def _watch_token(value: Any) -> str | None:
    token = str(value).lower().strip()
    if len(token) < MIN_TOKEN_LENGTH or token in STOP_TOKENS:
        return None
    return token


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
