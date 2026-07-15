from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from agent_privacy.attacks.cluster import UnionFind
from agent_privacy.evaluation.clustering import clustering_metrics, truth_labels
from agent_privacy.evaluation.ordering import evaluate_turn_ordering
from agent_privacy.experiments.bootstrap_ci import _bootstrap_units, _weighted_pairwise_metrics
from agent_privacy.io import iter_jsonl, read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000")
DEFAULT_DEVELOPMENT_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000_sample100")
DEFAULT_BASELINE_PREDICTIONS = Path(
    "results/open_swe_traces_raw_1000_turns_3_6_9_12_m0_fast/M0/predictions.json"
)
DEFAULT_CARP_PREDICTIONS = Path(
    "results/open_swe_provider_lowcost_longitudinal_full_first_12000_turns/"
    "M0/feature_no_semantic/predictions.json"
)
DEFAULT_NO_WORKSPACE_PREDICTIONS = Path(
    "results/open_swe_traces_raw_1000_turns_3_6_9_12_no_workspace_fast/M0/predictions.json"
)
DEFAULT_TURN_DELTA_DATASET = Path(
    "artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12"
)
DEFAULT_TURN_DELTA_PREDICTIONS = Path(
    "results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_m0_fast/M0/predictions.json"
)
DEFAULT_CARP_TURN_DELTA_PREDICTIONS = Path(
    "results/open_swe_carp_turn_delta_3_6_9_12/M0/feature_no_semantic/predictions.json"
)
DEFAULT_CONTEXT_PREDICTIONS = Path(
    "results/open_swe_context_only_sample100_turns/M0/feature_no_semantic/predictions.json"
)
DEFAULT_DEVELOPMENT_CARP_PREDICTIONS = Path(
    "results/open_swe_provider_lowcost_cumulative_sample100_cluster/M0/"
    "feature_no_semantic/predictions.json"
)
TURN_IDS = {3, 6, 9, 12}


def summarize_main_session(
    *,
    dataset_dir: Path,
    development_dataset_dir: Path,
    baseline_predictions_path: Path,
    carp_predictions_path: Path,
    no_workspace_predictions_path: Path,
    turn_delta_dataset_dir: Path,
    turn_delta_predictions_path: Path,
    carp_turn_delta_predictions_path: Path,
    context_predictions_path: Path,
    development_carp_predictions_path: Path,
    iterations: int = 200,
    seed: int = 7,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    development_truth = read_jsonl(development_dataset_dir / "ground_truth.jsonl")
    development_workflows = {str(row["workflow_id"]) for row in development_truth}
    truth_rows = [
        row
        for row in truth_rows
        if int(row.get("turn_id", -1)) in TURN_IDS
        and str(row["workflow_id"]) not in development_workflows
    ]
    baseline_predictions = json.loads(baseline_predictions_path.read_text(encoding="utf-8"))
    carp_predictions = json.loads(carp_predictions_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    roles = {
        "temporal": "time-only baseline",
        "rare": "rare-trace baseline",
        "tool": "tool-fingerprint baseline",
        "hybrid": "high-fidelity baseline",
        "provider_lowcost": "CARP",
    }
    for method, predictions in (
        ("temporal", baseline_predictions["temporal"]),
        ("rare", baseline_predictions["rare"]),
        ("tool", baseline_predictions["tool"]),
        ("hybrid", baseline_predictions["hybrid"]),
        ("provider_lowcost", carp_predictions["provider_lowcost"]),
    ):
        rows.append(
            _session_row(
                scope="heldout_900_workflows",
                method=method,
                role=roles[method],
                predictions=predictions["session"],
                truth_rows=truth_rows,
                iterations=iterations,
                seed=seed,
            )
        )

    no_workspace_predictions = json.loads(
        no_workspace_predictions_path.read_text(encoding="utf-8")
    )["hybrid"]
    rows.append(
        _session_row(
            scope="heldout_900_workflows",
            method="hybrid_no_workspace",
            role="workspace-removal control",
            predictions=no_workspace_predictions["session"],
            truth_rows=truth_rows,
            iterations=iterations,
            seed=seed,
        )
    )

    turn_delta_truth = [
        row
        for row in read_jsonl(turn_delta_dataset_dir / "ground_truth.jsonl")
        if str(row["workflow_id"]) not in development_workflows
    ]
    turn_delta_predictions = json.loads(turn_delta_predictions_path.read_text(encoding="utf-8"))
    carp_turn_delta_predictions = json.loads(
        carp_turn_delta_predictions_path.read_text(encoding="utf-8")
    )
    for method, role, predictions in (
        (
            "hybrid_turn_delta",
            "non-cumulative Hybrid control",
            turn_delta_predictions["hybrid"]["session"],
        ),
        (
            "carp_turn_delta",
            "non-cumulative CARP control",
            carp_turn_delta_predictions["provider_lowcost"]["session"],
        ),
    ):
        rows.append(
            _session_row(
                scope="heldout_900_workflows",
                method=method,
                role=role,
                predictions=predictions,
                truth_rows=turn_delta_truth,
                iterations=iterations,
                seed=seed,
            )
        )

    development_truth = [
        row for row in development_truth if int(row.get("turn_id", -1)) in TURN_IDS
    ]
    context_predictions = json.loads(context_predictions_path.read_text(encoding="utf-8"))[
        "context_only"
    ]
    development_carp_predictions = json.loads(
        development_carp_predictions_path.read_text(encoding="utf-8")
    )["provider_lowcost"]
    for method, role, predictions in (
        ("context_only", "bounded context-only", context_predictions["session"]),
        ("provider_lowcost", "CARP diagnostic", development_carp_predictions["session"]),
    ):
        rows.append(
            _session_row(
                scope="development_100_workflows",
                method=method,
                role=role,
                predictions=predictions,
                truth_rows=development_truth,
                iterations=iterations,
                seed=seed,
            )
        )

    heldout_ids = {row["request_id"] for row in truth_rows}
    attack_rows = [
        row
        for row in iter_jsonl(dataset_dir / "attack_view.jsonl")
        if row.get("request_id") in heldout_ids
    ]
    rows.append(
        _session_row(
            scope="heldout_900_workflows",
            method="exact_message_nesting",
            role="exact cumulative-prefix baseline",
            predictions=_exact_message_nesting_labels(attack_rows),
            truth_rows=truth_rows,
            iterations=iterations,
            seed=seed,
        )
    )
    rows.append(
        _paired_difference_row(
            left_method="provider_lowcost",
            right_method="hybrid",
            left_predictions=carp_predictions["provider_lowcost"]["session"],
            right_predictions=baseline_predictions["hybrid"]["session"],
            truth_rows=truth_rows,
            iterations=iterations,
            seed=seed,
        )
    )
    ordering = evaluate_turn_ordering(
        attack_rows,
        carp_predictions["provider_lowcost"]["session"],
        truth_rows,
    )
    return rows, ordering


def _session_row(
    *,
    scope: str,
    method: str,
    role: str,
    predictions: dict[str, str],
    truth_rows: list[dict[str, Any]],
    iterations: int,
    seed: int,
) -> dict[str, Any]:
    truth = truth_labels(truth_rows, "session")
    observed = clustering_metrics(predictions, truth)
    units = _bootstrap_units(truth_rows, "session")
    workflow_ids = sorted(units)
    request_to_workflow = {
        request_id: workflow_id
        for workflow_id, request_ids in units.items()
        for request_id in request_ids
    }
    rng = random.Random(seed)
    samples = []
    for _ in range(iterations):
        weights = Counter(rng.choices(workflow_ids, k=len(workflow_ids)))
        samples.append(
            _weighted_pairwise_metrics(
                predictions,
                truth,
                request_to_workflow,
                weights,
            )["pairwise_f1"]
        )
    return {
        "scope": scope,
        "method": method,
        "role": role,
        "workflows": len(units),
        "requests": sum(len(request_ids) for request_ids in units.values()),
        "precision": observed["pairwise_precision"],
        "recall": observed["pairwise_recall"],
        "f1": observed["pairwise_f1"],
        "purity": observed["purity"],
        "split_rate": observed["split_rate"],
        "merge_rate": observed["merge_rate"],
        "clusters": int(observed["clusters"]),
        "f1_ci_low": _quantile(samples, 0.025),
        "f1_ci_high": _quantile(samples, 0.975),
        "bootstrap_iterations": iterations,
    }


def _paired_difference_row(
    *,
    left_method: str,
    right_method: str,
    left_predictions: dict[str, str],
    right_predictions: dict[str, str],
    truth_rows: list[dict[str, Any]],
    iterations: int,
    seed: int,
) -> dict[str, Any]:
    truth = truth_labels(truth_rows, "session")
    units = _bootstrap_units(truth_rows, "session")
    workflow_ids = sorted(units)
    request_to_workflow = {
        request_id: workflow_id
        for workflow_id, request_ids in units.items()
        for request_id in request_ids
    }
    left_observed = clustering_metrics(left_predictions, truth)["pairwise_f1"]
    right_observed = clustering_metrics(right_predictions, truth)["pairwise_f1"]
    rng = random.Random(seed)
    samples = []
    for _ in range(iterations):
        weights = Counter(rng.choices(workflow_ids, k=len(workflow_ids)))
        left = _weighted_pairwise_metrics(
            left_predictions, truth, request_to_workflow, weights
        )["pairwise_f1"]
        right = _weighted_pairwise_metrics(
            right_predictions, truth, request_to_workflow, weights
        )["pairwise_f1"]
        samples.append(left - right)
    return {
        "scope": "heldout_900_workflows",
        "method": f"{left_method}_minus_{right_method}",
        "role": "paired session-F1 difference",
        "workflows": len(units),
        "requests": sum(len(request_ids) for request_ids in units.values()),
        "precision": "",
        "recall": "",
        "f1": left_observed - right_observed,
        "purity": "",
        "split_rate": "",
        "merge_rate": "",
        "clusters": "",
        "f1_ci_low": _quantile(samples, 0.025),
        "f1_ci_high": _quantile(samples, 0.975),
        "bootstrap_iterations": iterations,
    }


def _exact_message_nesting_labels(attack_rows: list[dict[str, Any]]) -> dict[str, str]:
    request_ids = [str(row["request_id"]) for row in attack_rows]
    uf = UnionFind(request_ids)
    full_digests: dict[str, list[str]] = {}
    for row in attack_rows:
        digest = _message_prefix_digests(row.get("messages", []))[-1]
        full_digests.setdefault(digest, []).append(str(row["request_id"]))
    for row in attack_rows:
        request_id = str(row["request_id"])
        for digest in _message_prefix_digests(row.get("messages", [])):
            for other in full_digests.get(digest, []):
                if other != request_id:
                    uf.union(request_id, other)
    return uf.labels("exact_nested")


def _message_prefix_digests(messages: list[dict[str, Any]]) -> list[str]:
    hasher = hashlib.sha256()
    digests: list[str] = []
    for message in messages:
        encoded = json.dumps(
            [message.get("role"), message.get("name"), message.get("content")],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        hasher.update(len(encoded).to_bytes(8, "big"))
        hasher.update(encoded)
        digests.append(hasher.hexdigest())
    return digests or [hashlib.sha256(b"").hexdigest()]


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _write_markdown(
    path: Path,
    rows: list[dict[str, Any]],
    ordering: dict[str, Any],
) -> None:
    headers = [
        "scope",
        "method",
        "role",
        "workflows",
        "requests",
        "precision",
        "recall",
        "f1",
        "purity",
        "split_rate",
        "merge_rate",
        "clusters",
        "f1_ci_low",
        "f1_ci_high",
    ]
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
    lines.extend(
        [
            "",
            (
                "Held-out CARP ordering on "
                f"{ordering['pure_session_clusters']} pure session clusters: adjacent accuracy "
                f"{ordering['adjacent_pair_accuracy']:.3f} and pairwise accuracy "
                f"{ordering['pairwise_order_accuracy']:.3f} over "
                f"{ordering['adjacent_pairs']}/{ordering['ordered_pairs']} ordered pairs."
            ),
            "",
            (
                "The development context-only row isolates bounded cumulative-context and "
                "identifier rules; it does not form project, owner, or cross-cache entity links."
            ),
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize held-out Open-SWE session evidence.")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--development-dataset-dir", type=Path, default=DEFAULT_DEVELOPMENT_DATASET
    )
    parser.add_argument(
        "--baseline-predictions", type=Path, default=DEFAULT_BASELINE_PREDICTIONS
    )
    parser.add_argument("--carp-predictions", type=Path, default=DEFAULT_CARP_PREDICTIONS)
    parser.add_argument(
        "--no-workspace-predictions",
        type=Path,
        default=DEFAULT_NO_WORKSPACE_PREDICTIONS,
    )
    parser.add_argument(
        "--turn-delta-dataset-dir", type=Path, default=DEFAULT_TURN_DELTA_DATASET
    )
    parser.add_argument(
        "--turn-delta-predictions", type=Path, default=DEFAULT_TURN_DELTA_PREDICTIONS
    )
    parser.add_argument(
        "--carp-turn-delta-predictions",
        type=Path,
        default=DEFAULT_CARP_TURN_DELTA_PREDICTIONS,
    )
    parser.add_argument(
        "--context-predictions", type=Path, default=DEFAULT_CONTEXT_PREDICTIONS
    )
    parser.add_argument(
        "--development-carp-predictions",
        type=Path,
        default=DEFAULT_DEVELOPMENT_CARP_PREDICTIONS,
    )
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    rows, ordering = summarize_main_session(
        dataset_dir=args.dataset_dir,
        development_dataset_dir=args.development_dataset_dir,
        baseline_predictions_path=args.baseline_predictions,
        carp_predictions_path=args.carp_predictions,
        no_workspace_predictions_path=args.no_workspace_predictions,
        turn_delta_dataset_dir=args.turn_delta_dataset_dir,
        turn_delta_predictions_path=args.turn_delta_predictions,
        carp_turn_delta_predictions_path=args.carp_turn_delta_predictions,
        context_predictions_path=args.context_predictions,
        development_carp_predictions_path=args.development_carp_predictions,
        iterations=args.iterations,
        seed=args.seed,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "open_swe_main_session_evidence.csv"
    md_path = args.output_dir / "open_swe_main_session_evidence.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows, ordering)
    print({"rows": len(rows), "output": str(md_path)})


if __name__ == "__main__":
    main()
