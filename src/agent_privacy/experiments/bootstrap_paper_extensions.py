from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.evaluation.clustering import truth_labels
from agent_privacy.experiments.bootstrap_ci import (
    _bootstrap_units,
    _weighted_pairwise_metrics,
)
from agent_privacy.experiments.run_semantic_profile import split_request_ids_by_org
from agent_privacy.experiments.summarize_tau_bench_watchlist import (
    LEVEL_FIELDS,
    build_entity_watchlist,
    entity_watchlist_assignments,
)
from agent_privacy.io import read_jsonl
from agent_privacy.profiling.structured_profiler import AUDITED_TECHNICAL_FIELDS
from agent_privacy.reporting import write_csv


def bootstrap_paper_extensions(
    *,
    t3_dataset_dir: Path,
    t3_baseline_predictions: Path,
    t3_improved_predictions: Path,
    t3_full_dataset_dir: Path,
    semantic_dataset_dir: Path,
    semantic_result_dir: Path,
    output: Path,
    iterations: int = 500,
    seed: int = 7,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(
        _bootstrap_t3_linkage(
            t3_dataset_dir,
            t3_baseline_predictions,
            t3_improved_predictions,
            iterations=iterations,
            seed=seed,
        )
    )
    rows.extend(
        _bootstrap_t3_watchlist(
            t3_dataset_dir,
            t3_full_dataset_dir,
            t3_improved_predictions,
            iterations=iterations,
            seed=seed + 1,
        )
    )
    rows.extend(
        _bootstrap_semantic_profile(
            semantic_dataset_dir,
            semantic_result_dir,
            iterations=iterations,
            seed=seed + 2,
        )
    )
    write_csv(output, rows)
    _write_markdown(output.with_suffix(".md"), rows)
    return rows


def _bootstrap_t3_linkage(
    dataset_dir: Path,
    baseline_path: Path,
    improved_path: Path,
    *,
    iterations: int,
    seed: int,
) -> list[dict[str, Any]]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))["provider_lowcost"]
    improved = json.loads(improved_path.read_text(encoding="utf-8"))["provider_lowcost"]
    units = _bootstrap_units(truth_rows, "session")
    request_to_unit = {
        request_id: unit_id for unit_id, request_ids in units.items() for request_id in request_ids
    }
    rng = random.Random(seed)
    out: list[dict[str, Any]] = []
    unit_ids = sorted(units)
    for level in ("user", "project", "org"):
        truth = truth_labels(truth_rows, level)
        before = _weighted_pairwise_metrics(
            baseline[level], truth, request_to_unit, {unit_id: 1 for unit_id in unit_ids}
        )["pairwise_f1"]
        after = _weighted_pairwise_metrics(
            improved[level], truth, request_to_unit, {unit_id: 1 for unit_id in unit_ids}
        )["pairwise_f1"]
        before_samples: list[float] = []
        after_samples: list[float] = []
        delta_samples: list[float] = []
        for _ in range(iterations):
            weights = Counter(rng.choices(unit_ids, k=len(unit_ids)))
            before_f1 = _weighted_pairwise_metrics(
                baseline[level], truth, request_to_unit, weights
            )["pairwise_f1"]
            after_f1 = _weighted_pairwise_metrics(
                improved[level], truth, request_to_unit, weights
            )["pairwise_f1"]
            before_samples.append(before_f1)
            after_samples.append(after_f1)
            delta_samples.append(after_f1 - before_f1)
        out.append(
            _paired_row(
                experiment="t3_entity_percolation",
                level=level,
                before_method="bucket_local",
                after_method="cross_cache_entity",
                before=before,
                after=after,
                before_samples=before_samples,
                after_samples=after_samples,
                delta_samples=delta_samples,
                units=len(unit_ids),
                iterations=iterations,
            )
        )
    return out


def _bootstrap_t3_watchlist(
    train_dir: Path,
    full_dir: Path,
    predictions_path: Path,
    *,
    iterations: int,
    seed: int,
) -> list[dict[str, Any]]:
    train_rows = read_jsonl(train_dir / "attack_view.jsonl")
    train_truth = read_jsonl(train_dir / "ground_truth.jsonl")
    full_rows = read_jsonl(full_dir / "attack_view.jsonl")
    full_truth = read_jsonl(full_dir / "ground_truth.jsonl")
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))["provider_lowcost"]
    test_rows = full_rows[len(train_rows) :]
    test_truth = full_truth[len(train_truth) :]
    rng = random.Random(seed)
    out: list[dict[str, Any]] = []
    for level, truth_field in LEVEL_FIELDS.items():
        watchlist = build_entity_watchlist(
            train_rows,
            train_truth,
            predictions[level],
            level=level,
            truth_field=truth_field,
        )
        assignments = entity_watchlist_assignments(
            watchlist,
            test_rows,
            test_truth,
            level=level,
            truth_field=truth_field,
        )
        entities = sorted({row["truth"] for row in assignments})
        observed = _watchlist_metrics(assignments, {entity: 1 for entity in entities})
        samples = {"precision": [], "recall": [], "f1": []}
        for _ in range(iterations):
            weights = Counter(rng.choices(entities, k=len(entities)))
            metrics = _watchlist_metrics(assignments, weights)
            for metric in samples:
                samples[metric].append(metrics[metric])
        for metric in ("precision", "recall", "f1"):
            out.append(
                {
                    "experiment": "t3_entity_watchlist",
                    "level": level,
                    "metric": metric,
                    "before_method": "",
                    "after_method": "first2500_watchlist",
                    "before_observed": "",
                    "after_observed": observed[metric],
                    "before_ci_low": "",
                    "before_ci_high": "",
                    "after_ci_low": _quantile(samples[metric], 0.025),
                    "after_ci_high": _quantile(samples[metric], 0.975),
                    "delta_observed": "",
                    "delta_ci_low": "",
                    "delta_ci_high": "",
                    "units": len(entities),
                    "iterations": iterations,
                }
            )
    return out


def _bootstrap_semantic_profile(
    dataset_dir: Path,
    result_dir: Path,
    *,
    iterations: int,
    seed: int,
) -> list[dict[str, Any]]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    summary = json.loads((result_dir / "semantic_profile_summary.json").read_text(encoding="utf-8"))
    _, test_ids = split_request_ids_by_org(
        truth_rows,
        calibration_fraction=float(summary["calibration_fraction"]),
        seed=int(summary["seed"]),
    )
    test_truth = [row for row in truth_rows if row["request_id"] in test_ids]
    structured = json.loads(
        (result_dir / "structured_predicted_clusters.json").read_text(encoding="utf-8")
    )
    semantic = json.loads(
        (result_dir / "semantic_predicted_clusters.json").read_text(encoding="utf-8")
    )
    before_counts = _profile_counts_by_org(structured, test_truth)
    after_counts = _profile_counts_by_org(semantic, test_truth)
    orgs = sorted(set(before_counts) | set(after_counts))
    before = _profile_metrics(before_counts, {org: 1 for org in orgs})
    after = _profile_metrics(after_counts, {org: 1 for org in orgs})
    rng = random.Random(seed)
    before_samples: list[float] = []
    after_samples: list[float] = []
    delta_samples: list[float] = []
    for _ in range(iterations):
        weights = Counter(rng.choices(orgs, k=len(orgs)))
        before_f1 = _profile_metrics(before_counts, weights)["f1"]
        after_f1 = _profile_metrics(after_counts, weights)["f1"]
        before_samples.append(before_f1)
        after_samples.append(after_f1)
        delta_samples.append(after_f1 - before_f1)
    return [
        _paired_row(
            experiment="semantic_profile",
            level="org",
            before_method="structured",
            after_method="minilm_semantic",
            before=before["f1"],
            after=after["f1"],
            before_samples=before_samples,
            after_samples=after_samples,
            delta_samples=delta_samples,
            units=len(orgs),
            iterations=iterations,
        )
    ]


def _profile_counts_by_org(
    profiles: dict[str, dict[str, Any]],
    truth_rows: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    truth_by_request = {row["request_id"]: row for row in truth_rows}
    truth_by_org: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    predicted_by_org: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in truth_rows:
        for field, values in row.get("profile_truth", {}).items():
            if field in AUDITED_TECHNICAL_FIELDS:
                truth_by_org[str(row["org_id"])][field].update(values)
    for profile in profiles.values():
        counts = Counter(
            str(truth_by_request[request_id]["org_id"])
            for request_id in profile.get("request_ids", [])
            if request_id in truth_by_request
        )
        if not counts:
            continue
        org = counts.most_common(1)[0][0]
        for field, values in profile.get("fields", {}).items():
            if field in AUDITED_TECHNICAL_FIELDS:
                predicted_by_org[org][field].update(values)
    out: dict[str, dict[str, int]] = {}
    for org in set(truth_by_org) | set(predicted_by_org):
        tp = fp = fn = 0
        for field in AUDITED_TECHNICAL_FIELDS:
            pred = predicted_by_org[org].get(field, set())
            truth = truth_by_org[org].get(field, set())
            tp += len(pred & truth)
            fp += len(pred - truth)
            fn += len(truth - pred)
        out[org] = {"tp": tp, "fp": fp, "fn": fn}
    return out


def _profile_metrics(
    counts_by_org: dict[str, dict[str, int]], weights: dict[str, int]
) -> dict[str, float]:
    tp = sum(counts_by_org.get(org, {}).get("tp", 0) * weight for org, weight in weights.items())
    fp = sum(counts_by_org.get(org, {}).get("fp", 0) * weight for org, weight in weights.items())
    fn = sum(counts_by_org.get(org, {}).get("fn", 0) * weight for org, weight in weights.items())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def _watchlist_metrics(
    assignments: list[dict[str, Any]], weights: dict[str, int]
) -> dict[str, float]:
    matched = sum(row["matched"] * weights.get(row["truth"], 0) for row in assignments)
    correct = sum(row["correct"] * weights.get(row["truth"], 0) for row in assignments)
    eligible = sum(row["eligible"] * weights.get(row["truth"], 0) for row in assignments)
    precision = correct / matched if matched else 0.0
    recall = correct / eligible if eligible else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def _paired_row(
    *,
    experiment: str,
    level: str,
    before_method: str,
    after_method: str,
    before: float,
    after: float,
    before_samples: list[float],
    after_samples: list[float],
    delta_samples: list[float],
    units: int,
    iterations: int,
) -> dict[str, Any]:
    return {
        "experiment": experiment,
        "level": level,
        "metric": "f1",
        "before_method": before_method,
        "after_method": after_method,
        "before_observed": before,
        "after_observed": after,
        "before_ci_low": _quantile(before_samples, 0.025),
        "before_ci_high": _quantile(before_samples, 0.975),
        "after_ci_low": _quantile(after_samples, 0.025),
        "after_ci_high": _quantile(after_samples, 0.975),
        "delta_observed": after - before,
        "delta_ci_low": _quantile(delta_samples, 0.025),
        "delta_ci_high": _quantile(delta_samples, 0.975),
        "units": units,
        "iterations": iterations,
    }


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = [
        "experiment",
        "level",
        "metric",
        "before_observed",
        "after_observed",
        "after_ci_low",
        "after_ci_high",
        "delta_observed",
        "delta_ci_low",
        "delta_ci_high",
        "units",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                f"{row.get(header):.3f}"
                if isinstance(row.get(header), float)
                else str(row.get(header, ""))
                for header in headers
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap new paper-extension results.")
    parser.add_argument("--t3-dataset-dir", type=Path, required=True)
    parser.add_argument("--t3-baseline-predictions", type=Path, required=True)
    parser.add_argument("--t3-improved-predictions", type=Path, required=True)
    parser.add_argument("--t3-full-dataset-dir", type=Path, required=True)
    parser.add_argument("--semantic-dataset-dir", type=Path, required=True)
    parser.add_argument("--semantic-result-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    rows = bootstrap_paper_extensions(
        t3_dataset_dir=args.t3_dataset_dir,
        t3_baseline_predictions=args.t3_baseline_predictions,
        t3_improved_predictions=args.t3_improved_predictions,
        t3_full_dataset_dir=args.t3_full_dataset_dir,
        semantic_dataset_dir=args.semantic_dataset_dir,
        semantic_result_dir=args.semantic_result_dir,
        output=args.output,
        iterations=args.iterations,
        seed=args.seed,
    )
    print({"rows": len(rows), "output": str(args.output)})


if __name__ == "__main__":
    main()
