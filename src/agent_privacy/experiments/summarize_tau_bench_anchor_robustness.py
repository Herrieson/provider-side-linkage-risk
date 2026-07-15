from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

from agent_privacy.features.extract import extract_business_identifiers
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET = Path("artifacts/datasets/tau_bench_overlay_t3")
DEFAULT_TRAIN_SNAPSHOT = Path("artifacts/datasets/tau_bench_overlay_t3_snapshots/first_2500_requests")
DEFAULT_PREDICTIONS = Path(
    "results/tau_bench_overlay_t3_first_2500_provider_lowcost_entity_percolation/"
    "M0/predictions.json"
)
LEVEL_FIELDS = {"user": "user_id", "project": "project_id", "org": "org_id"}
RETENTION_RATES = (1.0, 0.75, 0.50, 0.25, 0.0)
ROTATION_RATES = (0.0, 0.25, 0.50, 0.75, 1.0)
COLLISION_RATES = (0.0, 0.05, 0.10, 0.25)


def summarize_anchor_robustness(
    *,
    dataset_dir: Path = DEFAULT_DATASET,
    train_snapshot_dir: Path = DEFAULT_TRAIN_SNAPSHOT,
    predictions_path: Path = DEFAULT_PREDICTIONS,
    output_dir: Path = Path("docs/tables"),
    seed: int = 7,
) -> dict[str, str]:
    all_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    all_truth = read_jsonl(dataset_dir / "ground_truth.jsonl")
    train_rows = read_jsonl(train_snapshot_dir / "attack_view.jsonl")
    train_truth = read_jsonl(train_snapshot_dir / "ground_truth.jsonl")
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))["provider_lowcost"]
    train_count = len(train_rows)
    test_rows = all_rows[train_count:]
    test_truth = all_truth[train_count:]
    stats_rows = _anchor_statistics(all_rows, all_truth)
    stress_rows: list[dict[str, Any]] = []
    for level, truth_field in LEVEL_FIELDS.items():
        train_anchors = _anchors_by_request(train_rows, level)
        test_anchors = _anchors_by_request(test_rows, level)
        for retention in RETENTION_RATES:
            stress_rows.append(
                _stress_score(
                    level=level,
                    truth_field=truth_field,
                    condition="retention",
                    value=retention,
                    train_anchors=_retain_occurrences(train_anchors, retention, seed),
                    test_anchors=_retain_occurrences(test_anchors, retention, seed),
                    train_truth=train_truth,
                    test_truth=test_truth,
                    labels=predictions[level],
                )
            )
        for rotation in ROTATION_RATES:
            stress_rows.append(
                _stress_score(
                    level=level,
                    truth_field=truth_field,
                    condition="later_alias_rotation",
                    value=rotation,
                    train_anchors=train_anchors,
                    test_anchors=_rotate_later_anchors(test_anchors, rotation, seed),
                    train_truth=train_truth,
                    test_truth=test_truth,
                    labels=predictions[level],
                )
            )
        for collision in COLLISION_RATES:
            stress_rows.append(
                _stress_score(
                    level=level,
                    truth_field=truth_field,
                    condition="shared_anchor_collision",
                    value=collision,
                    train_anchors=_collide_anchors(train_anchors, collision, seed),
                    test_anchors=_collide_anchors(test_anchors, collision, seed),
                    train_truth=train_truth,
                    test_truth=test_truth,
                    labels=predictions[level],
                )
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    stats_csv = output_dir / "tau_bench_t3_anchor_statistics.csv"
    stats_md = output_dir / "tau_bench_t3_anchor_statistics.md"
    stress_csv = output_dir / "tau_bench_t3_anchor_robustness.csv"
    stress_md = output_dir / "tau_bench_t3_anchor_robustness.md"
    write_csv(stats_csv, stats_rows)
    write_csv(stress_csv, stress_rows)
    _write_markdown(stats_md, stats_rows)
    _write_markdown(stress_md, stress_rows)
    return {
        "statistics": str(stats_md),
        "robustness": str(stress_md),
    }


def _anchor_statistics(
    rows: list[dict[str, Any]], truth_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    truth_by_request = {row["request_id"]: row for row in truth_rows}
    output: list[dict[str, Any]] = []
    for level, truth_field in LEVEL_FIELDS.items():
        records: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"requests": 0, "entities": set(), "workflows": set(), "times": []}
        )
        covered = 0
        for row in rows:
            anchors = _level_anchors(extract_business_identifiers(row), level)
            covered += bool(anchors)
            truth = truth_by_request[row["request_id"]]
            for anchor in anchors:
                record = records[anchor]
                record["requests"] += 1
                record["entities"].add(str(truth[truth_field]))
                record["workflows"].add(str(truth["workflow_id"]))
                record["times"].append(_timestamp(row["timestamp"]))
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for anchor, record in records.items():
            anchor_type = anchor.split(":", 2)[1] if ":" in anchor else "unknown"
            by_type[anchor_type].append(record)
        for anchor_type, type_records in sorted(by_type.items()):
            frequencies = [record["requests"] for record in type_records]
            lifecycle_days = [
                (max(record["times"]) - min(record["times"])).total_seconds() / 86400
                for record in type_records
            ]
            output.append(
                {
                    "level": level,
                    "anchor_type": anchor_type,
                    "requests": len(rows),
                    "request_coverage": covered / len(rows),
                    "unique_anchors": len(type_records),
                    "median_occurrences": median(frequencies),
                    "max_occurrences": max(frequencies),
                    "ambiguous_anchor_rate": sum(
                        len(record["entities"]) > 1 for record in type_records
                    )
                    / len(type_records),
                    "cross_workflow_anchor_rate": sum(
                        len(record["workflows"]) > 1 for record in type_records
                    )
                    / len(type_records),
                    "median_lifecycle_days": median(lifecycle_days),
                    "max_lifecycle_days": max(lifecycle_days),
                }
            )
    return output


def _stress_score(
    *,
    level: str,
    truth_field: str,
    condition: str,
    value: float,
    train_anchors: dict[str, set[str]],
    test_anchors: dict[str, set[str]],
    train_truth: list[dict[str, Any]],
    test_truth: list[dict[str, Any]],
    labels: dict[str, str],
) -> dict[str, Any]:
    watchlist = _build_watchlist(train_anchors, train_truth, labels, truth_field)
    truth_by_request = {row["request_id"]: row for row in test_truth}
    seen_truth = set(watchlist["cluster_to_truth"].values())
    eligible = matched = correct = ambiguous = 0
    for request_id, anchors in test_anchors.items():
        truth = str(truth_by_request[request_id][truth_field])
        eligible += truth in seen_truth
        votes = Counter(
            watchlist["anchor_to_cluster"][anchor]
            for anchor in anchors
            if anchor in watchlist["anchor_to_cluster"]
        )
        if not votes:
            continue
        ranked = votes.most_common()
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            ambiguous += 1
            continue
        matched += 1
        correct += watchlist["cluster_to_truth"].get(ranked[0][0]) == truth
    precision = correct / matched if matched else 0.0
    recall = correct / eligible if eligible else 0.0
    return {
        "level": level,
        "condition": condition,
        "value": value,
        "test_requests": len(test_truth),
        "eligible_requests": eligible,
        "matched_requests": matched,
        "ambiguous_requests": ambiguous,
        "watch_anchors": len(watchlist["anchor_to_cluster"]),
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def _build_watchlist(
    anchors_by_request: dict[str, set[str]],
    truth_rows: list[dict[str, Any]],
    labels: dict[str, str],
    truth_field: str,
) -> dict[str, Any]:
    truth_by_request = {row["request_id"]: row for row in truth_rows}
    clusters_by_anchor: dict[str, set[str]] = defaultdict(set)
    truth_by_cluster: dict[str, Counter[str]] = defaultdict(Counter)
    for request_id, anchors in anchors_by_request.items():
        cluster = labels.get(request_id)
        if cluster is None:
            continue
        for anchor in anchors:
            clusters_by_anchor[anchor].add(cluster)
        truth_by_cluster[cluster][str(truth_by_request[request_id][truth_field])] += 1
    return {
        "anchor_to_cluster": {
            anchor: next(iter(clusters))
            for anchor, clusters in clusters_by_anchor.items()
            if len(clusters) == 1
        },
        "cluster_to_truth": {
            cluster: counts.most_common(1)[0][0]
            for cluster, counts in truth_by_cluster.items()
            if counts
        },
    }


def _anchors_by_request(rows: list[dict[str, Any]], level: str) -> dict[str, set[str]]:
    return {
        row["request_id"]: _level_anchors(extract_business_identifiers(row), level)
        for row in rows
    }


def _retain_occurrences(
    anchors_by_request: dict[str, set[str]], rate: float, seed: int
) -> dict[str, set[str]]:
    return {
        request_id: {
            anchor
            for anchor in anchors
            if _fraction(f"retain:{seed}:{request_id}:{anchor}") < rate
        }
        for request_id, anchors in anchors_by_request.items()
    }


def _rotate_later_anchors(
    anchors_by_request: dict[str, set[str]], rate: float, seed: int
) -> dict[str, set[str]]:
    output: dict[str, set[str]] = {}
    for request_id, anchors in anchors_by_request.items():
        values = set()
        for anchor in anchors:
            if _fraction(f"rotate:{seed}:{anchor}") < rate:
                values.add(f"{anchor}:rotated:{_digest(request_id)[:8]}")
            else:
                values.add(anchor)
        output[request_id] = values
    return output


def _collide_anchors(
    anchors_by_request: dict[str, set[str]], rate: float, seed: int
) -> dict[str, set[str]]:
    output: dict[str, set[str]] = {}
    for request_id, anchors in anchors_by_request.items():
        values = set()
        for anchor in anchors:
            if _fraction(f"collide:{seed}:{anchor}") < rate:
                prefix = anchor.rsplit(":", 1)[0]
                values.add(f"{prefix}:shared-collision")
            else:
                values.add(anchor)
        output[request_id] = values
    return output


def _level_anchors(identifiers: frozenset[str], level: str) -> set[str]:
    prefix = f"business_{level}:"
    return {value for value in identifiers if value.startswith(prefix)}


def _fraction(value: str) -> float:
    return int(_digest(value)[:16], 16) / float(0xFFFFFFFFFFFFFFFF)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = list(rows[0]) if rows else []
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                f"{row[header]:.3f}" if isinstance(row[header], float) else str(row[header])
                for header in headers
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit T3 anchors and watchlist robustness.")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--train-snapshot-dir", type=Path, default=DEFAULT_TRAIN_SNAPSHOT)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    print(
        summarize_anchor_robustness(
            dataset_dir=args.dataset_dir,
            train_snapshot_dir=args.train_snapshot_dir,
            predictions_path=args.predictions,
            output_dir=args.output_dir,
            seed=args.seed,
        )
    )


if __name__ == "__main__":
    main()
