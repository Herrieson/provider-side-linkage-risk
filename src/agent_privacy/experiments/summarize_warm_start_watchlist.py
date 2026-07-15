from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.features.extract import request_text
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


SNAPSHOTS = [1000, 4000, 8000, 12000]
LEVELS = ["session", "user", "project", "org"]
TRUTH_FIELDS = {
    "session": "workflow_id",
    "user": "user_id",
    "project": "project_id",
    "org": "org_id",
}
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/@-]{3,}")
MAX_TEXT_HEAD_CHARS = 8_000
MAX_TEXT_TAIL_CHARS = 24_000
MAX_TOKENS_PER_REQUEST = 900
MIN_ASSIGNMENT_SCORE = 35.0
MIN_ASSIGNMENT_HITS = 2
MIN_ASSIGNMENT_MARGIN = 1.35
STOP_TOKENS = {
    "assistant",
    "content",
    "error",
    "false",
    "function",
    "github",
    "messages",
    "method",
    "model",
    "none",
    "open",
    "openhands",
    "parameters",
    "request",
    "role",
    "safehttp",
    "system",
    "tests",
    "true",
    "user",
    "workspace",
}


def summarize_warm_start_watchlist(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for overlay, dataset_base, result_prefix in [
        (
            "U3",
            Path("artifacts/datasets/open_swe_user_overlay_u3_mixed_1000_snapshots"),
            Path("results/open_swe_user_overlay_u3"),
        ),
        (
            "U4",
            Path("artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000_snapshots"),
            Path("results/open_swe_user_overlay_u4"),
        ),
    ]:
        for train_count, test_count in [(1000, 4000), (4000, 8000), (8000, 12000)]:
            train_dataset = dataset_base / f"first_{train_count}_requests"
            test_dataset = dataset_base / f"first_{test_count}_requests"
            train_result = Path(f"{result_prefix}_first_{train_count}_provider_lowcost_streamed")
            if not (train_result / "M0" / "predictions.json").exists():
                continue
            rows.extend(
                _summarize_pair(
                    overlay=overlay,
                    train_count=train_count,
                    test_count=test_count,
                    train_dataset=train_dataset,
                    test_dataset=test_dataset,
                    train_predictions=train_result / "M0" / "predictions.json",
                )
            )
    csv_path = output_dir / "open_swe_user_overlay_warm_start_watchlist.csv"
    md_path = output_dir / "open_swe_user_overlay_warm_start_watchlist.md"
    headers = [
        "overlay_level",
        "train_snapshot",
        "test_snapshot",
        "truth_level",
        "train_requests",
        "new_requests",
        "watch_profiles",
        "watch_tokens",
        "target_future_requests",
        "assigned_requests",
        "correct_assignments",
        "assignment_coverage",
        "precision",
        "recall",
        "f1",
    ]
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows, headers)
    return {"warm_start_watchlist": str(csv_path), "rows": str(len(rows))}


def _summarize_pair(
    *,
    overlay: str,
    train_count: int,
    test_count: int,
    train_dataset: Path,
    test_dataset: Path,
    train_predictions: Path,
) -> list[dict[str, Any]]:
    train_rows = read_jsonl(train_dataset / "attack_view.jsonl")
    train_truth = read_jsonl(train_dataset / "ground_truth.jsonl")
    test_rows_all = read_jsonl(test_dataset / "attack_view.jsonl")
    test_truth_all = read_jsonl(test_dataset / "ground_truth.jsonl")
    train_ids = {row["request_id"] for row in train_rows}
    test_rows = [row for row in test_rows_all if row["request_id"] not in train_ids]
    test_truth = [row for row in test_truth_all if row["request_id"] not in train_ids]
    predictions = json.loads(train_predictions.read_text(encoding="utf-8"))["provider_lowcost"]
    train_tokens = _row_tokens(train_rows)
    test_tokens = _row_tokens(test_rows)
    out = []
    for level in LEVELS:
        labels = predictions.get(level, {})
        watchlist = _build_watchlist(train_rows, labels, train_tokens)
        truth_field = TRUTH_FIELDS[level]
        target_by_cluster = _majority_truth_by_cluster(labels, train_truth, truth_field)
        target_truth_values = set(target_by_cluster.values())
        result = _assign_and_score(
            watchlist,
            target_by_cluster,
            test_rows,
            test_truth,
            truth_field,
            test_tokens,
        )
        out.append(
            {
                "overlay_level": overlay,
                "train_snapshot": f"first_{train_count}_requests",
                "test_snapshot": f"first_{test_count}_requests",
                "truth_level": level,
                "train_requests": len(train_rows),
                "new_requests": len(test_rows),
                "watch_profiles": len(watchlist),
                "watch_tokens": sum(len(item["tokens"]) for item in watchlist.values()),
                "target_future_requests": sum(
                    1 for truth in test_truth if str(truth.get(truth_field)) in target_truth_values
                ),
                **result,
            }
        )
    return out


def _build_watchlist(
    rows: list[dict[str, Any]],
    labels: dict[str, str],
    row_tokens: dict[str, set[str]],
    *,
    max_tokens_per_cluster: int = 24,
    max_global_df_ratio: float = 0.35,
) -> dict[str, dict[str, Any]]:
    token_docs: dict[str, set[str]] = defaultdict(set)
    for request_id in labels:
        tokens = row_tokens.get(request_id, set())
        for token in tokens:
            token_docs[token].add(request_id)

    max_df = max(2, int(len(rows) * max_global_df_ratio))
    watchlist: dict[str, dict[str, Any]] = {}
    cluster_token_counts: dict[str, Counter[str]] = defaultdict(Counter)
    cluster_request_counts: Counter[str] = Counter()
    rows_by_id = {row["request_id"]: row for row in rows}
    for request_id, cluster_id in labels.items():
        if request_id not in rows_by_id:
            continue
        cluster_request_counts[cluster_id] += 1
        for token in row_tokens.get(request_id, set()):
            if _is_profile_anchor(token):
                cluster_token_counts[cluster_id][token] += 1

    for cluster_id, counts in cluster_token_counts.items():
        scored = []
        cluster_size = max(1, cluster_request_counts[cluster_id])
        for token, count in counts.items():
            df = len(token_docs.get(token, set()))
            if not df or df > max_df:
                continue
            score = (count / cluster_size) * (len(rows) / df)
            scored.append((score, count, df, token))
        if not scored:
            continue
        scored.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
        tokens = [
            {"token": token, "score": round(score, 6), "cluster_count": count, "global_df": df}
            for score, count, df, token in scored[:max_tokens_per_cluster]
        ]
        watchlist[cluster_id] = {
            "tokens": tokens,
            "train_requests": cluster_size,
        }
    if watchlist:
        return watchlist

    # Fallback for datasets where the rule profiler cannot extract stable fields.
    cluster_token_counts = defaultdict(Counter)
    cluster_request_counts = Counter()
    for request_id, cluster_id in labels.items():
        row = rows_by_id.get(request_id)
        if row is None:
            continue
        cluster_request_counts[cluster_id] += 1
        for token in row_tokens.get(request_id, set()):
            cluster_token_counts[cluster_id][token] += 1
    for cluster_id, counts in cluster_token_counts.items():
        scored = []
        cluster_size = max(1, cluster_request_counts[cluster_id])
        for token, count in counts.items():
            df = len(token_docs[token])
            if df > max_df:
                continue
            min_count = 1 if cluster_size <= 2 else 2
            if count < min_count:
                continue
            # Prefer tokens frequent in the cluster and rare globally.
            score = (count / cluster_size) * (len(rows) / df)
            scored.append((score, count, df, token))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
        tokens = [
            {"token": token, "score": round(score, 6), "cluster_count": count, "global_df": df}
            for score, count, df, token in scored[:max_tokens_per_cluster]
        ]
        if tokens:
            watchlist[cluster_id] = {"tokens": tokens, "train_requests": cluster_size}
    return watchlist


def _tokens(text: str) -> list[str]:
    out = []
    scoped_text = text[:MAX_TEXT_HEAD_CHARS] + "\n" + text[-MAX_TEXT_TAIL_CHARS:]
    for raw in TOKEN_RE.findall(scoped_text.lower()):
        token = raw.strip("._-/:@")
        if len(token) < 4 or token in STOP_TOKENS:
            continue
        if token.isdigit():
            continue
        out.append(token)
        out.extend(_derived_anchor_tokens(token))
        if len(out) >= MAX_TOKENS_PER_REQUEST:
            break
    return out


def _watch_token(value: Any) -> str | None:
    token = str(value).lower().strip().strip("._-/:@")
    if len(token) < 4 or token in STOP_TOKENS or token.isdigit():
        return None
    return token


def _derived_anchor_tokens(token: str) -> list[str]:
    out: list[str] = []
    if "__" in token:
        tail = token.rsplit("__", 1)[-1].strip("._-/:@")
        if len(tail) >= 4:
            out.append(tail)
    if "/" in token:
        tail = token.rsplit("/", 1)[-1].strip("._-/:@")
        if len(tail) >= 4:
            out.append(tail)
    if "." in token and not token.startswith("http"):
        out.append(token.strip("._-/:@"))
    return out


def _is_profile_anchor(token: str) -> bool:
    if len(token) < 4 or token in STOP_TOKENS:
        return False
    return (
        "__" in token
        or ".corp.local" in token
        or ".internal" in token
        or token.endswith("-api")
        or token.endswith("-service")
        or token.endswith("-worker")
        or token.endswith("-frontend")
        or token.endswith("-backend")
        or "/" in token
    )


def _row_tokens(rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    return {row["request_id"]: set(_tokens(request_text(row))) for row in rows}


def _majority_truth_by_cluster(
    labels: dict[str, str],
    truth_rows: list[dict[str, Any]],
    truth_field: str,
) -> dict[str, str]:
    truth_by_id = {row["request_id"]: row for row in truth_rows}
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for request_id, cluster_id in labels.items():
        truth = truth_by_id.get(request_id, {})
        value = truth.get(truth_field)
        if value is not None:
            counts[cluster_id][str(value)] += 1
    return {cluster_id: counter.most_common(1)[0][0] for cluster_id, counter in counts.items() if counter}


def _assign_and_score(
    watchlist: dict[str, dict[str, Any]],
    target_by_cluster: dict[str, str],
    test_rows: list[dict[str, Any]],
    test_truth: list[dict[str, Any]],
    truth_field: str,
    row_tokens: dict[str, set[str]],
) -> dict[str, Any]:
    token_to_clusters: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for cluster_id, item in watchlist.items():
        for token_info in item["tokens"]:
            token_to_clusters[token_info["token"]].append((cluster_id, float(token_info["score"])))

    truth_by_id = {row["request_id"]: row for row in test_truth}
    assigned = 0
    correct = 0
    for row in test_rows:
        scores: Counter[str] = Counter()
        hits: Counter[str] = Counter()
        text_tokens = row_tokens.get(row["request_id"], set())
        for token in text_tokens:
            for cluster_id, score in token_to_clusters.get(token, []):
                scores[cluster_id] += score
                hits[cluster_id] += 1
        if not scores:
            continue
        ranked = scores.most_common(2)
        cluster_id, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        if top_score < MIN_ASSIGNMENT_SCORE or hits[cluster_id] < MIN_ASSIGNMENT_HITS:
            continue
        if second_score and top_score / second_score < MIN_ASSIGNMENT_MARGIN:
            continue
        target = target_by_cluster.get(cluster_id)
        actual = truth_by_id.get(row["request_id"], {}).get(truth_field)
        if target is None or actual is None:
            continue
        assigned += 1
        if str(actual) == target:
            correct += 1

    target_truth_values = set(target_by_cluster.values())
    target_future_requests = sum(
        1 for truth in test_truth if str(truth.get(truth_field)) in target_truth_values
    )
    precision = correct / assigned if assigned else 0.0
    recall = correct / target_future_requests if target_future_requests else 0.0
    return {
        "assigned_requests": assigned,
        "correct_assignments": correct,
        "assignment_coverage": round(assigned / len(test_rows), 3) if test_rows else 0.0,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(2 * precision * recall / (precision + recall), 3)
        if precision + recall
        else 0.0,
    }


def _write_markdown(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format(row.get(header, "")) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Dataset B warm-start watchlist relinking.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(summarize_warm_start_watchlist(args.output_dir))


if __name__ == "__main__":
    main()
