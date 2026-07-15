from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.features.extract import extract_business_identifiers
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


LEVEL_FIELDS = {"user": "user_id", "project": "project_id", "org": "org_id"}


def summarize_tau_bench_watchlist(
    dataset_dir: Path,
    train_snapshot_dir: Path,
    predictions_path: Path,
    output_dir: Path,
    *,
    method: str = "provider_lowcost",
) -> dict[str, Any]:
    all_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    all_truth = read_jsonl(dataset_dir / "ground_truth.jsonl")
    train_rows = read_jsonl(train_snapshot_dir / "attack_view.jsonl")
    train_truth = read_jsonl(train_snapshot_dir / "ground_truth.jsonl")
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))[method]
    train_count = len(train_rows)
    windows = [
        (f"after_{train_count}_to_5000", all_rows[train_count:5000], all_truth[train_count:5000]),
        (f"after_{train_count}_to_full", all_rows[train_count:], all_truth[train_count:]),
    ]
    rows: list[dict[str, Any]] = []
    for level, truth_field in LEVEL_FIELDS.items():
        watchlist = build_entity_watchlist(
            train_rows,
            train_truth,
            predictions[level],
            level=level,
            truth_field=truth_field,
        )
        for window, test_rows, test_truth in windows:
            row = score_entity_watchlist(
                watchlist,
                test_rows,
                test_truth,
                level=level,
                truth_field=truth_field,
            )
            row.update(
                {
                    "dataset": dataset_dir.name,
                    "train_snapshot": train_snapshot_dir.name,
                    "test_window": window,
                    "method": method,
                }
            )
            rows.append(row)
    csv_path = output_dir / "tau_bench_t3_entity_watchlist.csv"
    md_path = output_dir / "tau_bench_t3_entity_watchlist.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path), "rows": len(rows)}


def build_entity_watchlist(
    rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    labels: dict[str, str],
    *,
    level: str,
    truth_field: str,
) -> dict[str, Any]:
    truth_by_request = {row["request_id"]: row for row in truth_rows}
    anchors_by_request = {
        row["request_id"]: _level_anchors(extract_business_identifiers(row), level)
        for row in rows
    }
    if level == "user":
        ambiguous = _ambiguous_account_caches(anchors_by_request)
        anchors_by_request = {
            request_id: anchors - ambiguous
            for request_id, anchors in anchors_by_request.items()
        }
    clusters_by_anchor: dict[str, set[str]] = defaultdict(set)
    truth_by_cluster: dict[str, Counter[str]] = defaultdict(Counter)
    for request_id, anchors in anchors_by_request.items():
        cluster = labels.get(request_id)
        truth = truth_by_request.get(request_id, {}).get(truth_field)
        if cluster is None:
            continue
        for anchor in anchors:
            clusters_by_anchor[anchor].add(cluster)
        if truth not in (None, "", "N/A"):
            truth_by_cluster[cluster][str(truth)] += 1
    anchor_to_cluster = {
        anchor: next(iter(clusters))
        for anchor, clusters in clusters_by_anchor.items()
        if len(clusters) == 1
    }
    cluster_to_truth = {
        cluster: counts.most_common(1)[0][0]
        for cluster, counts in truth_by_cluster.items()
        if counts
    }
    cluster_purity = {
        cluster: counts.most_common(1)[0][1] / sum(counts.values())
        for cluster, counts in truth_by_cluster.items()
        if counts
    }
    return {
        "level": level,
        "anchor_to_cluster": anchor_to_cluster,
        "cluster_to_truth": cluster_to_truth,
        "cluster_purity": cluster_purity,
        "seen_truth": sorted(set(cluster_to_truth.values())),
    }


def score_entity_watchlist(
    watchlist: dict[str, Any],
    rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    *,
    level: str,
    truth_field: str,
) -> dict[str, Any]:
    assignments = entity_watchlist_assignments(
        watchlist,
        rows,
        truth_rows,
        level=level,
        truth_field=truth_field,
    )
    eligible = sum(row["eligible"] for row in assignments)
    matched = sum(row["matched"] for row in assignments)
    correct = sum(row["correct"] for row in assignments)
    ambiguous = sum(row["ambiguous"] for row in assignments)
    matched_targets = {row["truth"] for row in assignments if row["correct"]}
    eligible_targets = {row["truth"] for row in assignments if row["eligible"]}
    precision = correct / matched if matched else 0.0
    recall = correct / eligible if eligible else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "level": level,
        "test_requests": len(rows),
        "eligible_seen_entity_requests": eligible,
        "matched_requests": matched,
        "correct_matches": correct,
        "ambiguous_matches": ambiguous,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "assignment_coverage": matched / len(rows) if rows else 0.0,
        "eligible_target_coverage": (
            len(matched_targets) / len(eligible_targets) if eligible_targets else 0.0
        ),
        "watch_anchors": len(watchlist["anchor_to_cluster"]),
        "watch_clusters": len(set(watchlist["anchor_to_cluster"].values())),
        "mean_train_cluster_purity": (
            sum(watchlist["cluster_purity"].values()) / len(watchlist["cluster_purity"])
            if watchlist["cluster_purity"]
            else 0.0
        ),
    }


def entity_watchlist_assignments(
    watchlist: dict[str, Any],
    rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    *,
    level: str,
    truth_field: str,
) -> list[dict[str, Any]]:
    truth_by_request = {row["request_id"]: row for row in truth_rows}
    anchor_to_cluster = watchlist["anchor_to_cluster"]
    cluster_to_truth = watchlist["cluster_to_truth"]
    seen_truth = set(watchlist["seen_truth"])
    assignments: list[dict[str, Any]] = []
    for row in rows:
        truth = str(truth_by_request[row["request_id"]][truth_field])
        eligible = truth in seen_truth
        votes = Counter(
            anchor_to_cluster[anchor]
            for anchor in _level_anchors(extract_business_identifiers(row), level)
            if anchor in anchor_to_cluster
        )
        if not votes:
            assignments.append(
                {
                    "request_id": row["request_id"],
                    "truth": truth,
                    "eligible": int(eligible),
                    "matched": 0,
                    "correct": 0,
                    "ambiguous": 0,
                }
            )
            continue
        ranked = votes.most_common()
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            assignments.append(
                {
                    "request_id": row["request_id"],
                    "truth": truth,
                    "eligible": int(eligible),
                    "matched": 0,
                    "correct": 0,
                    "ambiguous": 1,
                }
            )
            continue
        predicted_truth = cluster_to_truth.get(ranked[0][0])
        assignments.append(
            {
                "request_id": row["request_id"],
                "truth": truth,
                "eligible": int(eligible),
                "matched": 1,
                "correct": int(predicted_truth == truth),
                "ambiguous": 0,
            }
        )
    return assignments


def _level_anchors(identifiers: frozenset[str], level: str) -> set[str]:
    prefix = f"business_{level}:"
    return {value for value in identifiers if value.startswith(prefix)}


def _ambiguous_account_caches(anchors_by_request: dict[str, set[str]]) -> set[str]:
    customers_by_cache: dict[str, set[str]] = defaultdict(set)
    for anchors in anchors_by_request.values():
        customers = {a for a in anchors if a.startswith("business_user:customer_ref:")}
        for cache in (a for a in anchors if a.startswith("business_user:account_cache:")):
            customers_by_cache[cache].update(customers)
    return {cache for cache, customers in customers_by_cache.items() if len(customers) != 1}


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "train_snapshot",
        "test_window",
        "level",
        "precision",
        "recall",
        "f1",
        "assignment_coverage",
        "eligible_target_coverage",
        "watch_anchors",
        "watch_clusters",
    ]
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        values = [f"{row[field]:.3f}" if isinstance(row[field], float) else str(row[field]) for field in fields]
        lines.append("| " + " | ".join(values) + " |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate T3 cross-snapshot entity watchlists.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--train-snapshot-dir", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--method", default="provider_lowcost")
    args = parser.parse_args()
    print(
        json.dumps(
            summarize_tau_bench_watchlist(
                args.dataset_dir,
                args.train_snapshot_dir,
                args.predictions,
                args.output_dir,
                method=args.method,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
