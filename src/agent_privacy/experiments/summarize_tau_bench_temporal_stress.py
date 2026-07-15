from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

from agent_privacy.attacks.pipeline import run_attacks_from_features
from agent_privacy.evaluation.clustering import clustering_metrics, truth_labels
from agent_privacy.experiments.semantic_linkage import (
    encode_documents,
    exact_anchor_pairs,
    labels_from_scores,
    top_k_cosine_pairs,
    write_markdown,
)
from agent_privacy.experiments.summarize_tau_bench_historical_evidence import (
    _metric_rows,
    _split_rows,
)
from agent_privacy.features.extract import extract_features_from_rows, extract_stable_content_handles
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET_DIR = Path("artifacts/datasets/tau_bench_historical_sample200")
DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "tau_bench_temporal_stress"
ABLATION_BASE = "tau_bench_content_linkage_ablation"
ENTITY_RE = re.compile(
    r"\b(user|customer|account|order|reservation|booking|flight|product|item|ticket)"
    r"[_-]?([A-Za-z0-9-]{3,})\b",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"\b\d{3,}\b")
THRESHOLDS = tuple(value / 100 for value in range(50, 100, 2))
SCHEDULES = (
    ("original", None, 0),
    ("concurrent_8", 60, 120),
    ("concurrent_32", 15, 300),
    ("burst_160", 0, 600),
)
REPHRASE_MAP = {
    "cancel": "terminate",
    "change": "modify",
    "check": "verify",
    "find": "locate",
    "need": "require",
    "order": "purchase",
    "please": "kindly",
    "refund": "reimburse",
    "reservation": "booking",
    "return": "send back",
    "want": "would like",
}


def summarize_temporal_stress(
    *,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    iterations: int = 200,
    seed: int = 7,
) -> dict[str, str]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    attack_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    calibration_truth, test_truth = _split_rows(truth_rows, seed=seed)
    attack_by_id = {str(row["request_id"]): row for row in attack_rows}
    calibration_rows = [attack_by_id[str(row["request_id"])] for row in calibration_truth]
    test_rows = [attack_by_id[str(row["request_id"])] for row in test_truth]

    documents = {
        str(row["request_id"]): _semantic_document(row) for row in calibration_rows + test_rows
    }
    encode_start = time.perf_counter()
    document_ids, vectors = encode_documents(documents)
    embedding_seconds = time.perf_counter() - encode_start
    vector_by_id = {request_id: vectors[index] for index, request_id in enumerate(document_ids)}

    calibration_content = _content_predictions(
        calibration_rows,
        vector_by_id,
        calibration_truth,
        calibrate=True,
    )
    selected = calibration_content["thresholds"]
    test_content = _content_predictions(
        test_rows,
        vector_by_id,
        test_truth,
        thresholds=selected,
    )
    rephrased_documents = {
        str(row["request_id"]): _semantic_document(row, rephrase=True)
        for row in calibration_rows + test_rows
    }
    rephrased_ids, rephrased_vectors = encode_documents(rephrased_documents)
    rephrased_vector_by_id = {
        request_id: rephrased_vectors[index]
        for index, request_id in enumerate(rephrased_ids)
    }
    rephrased_test_content = _content_predictions(
        test_rows,
        rephrased_vector_by_id,
        test_truth,
        thresholds=selected,
    )

    stress_rows: list[dict[str, Any]] = []
    for condition, spacing_seconds, jitter_seconds in SCHEDULES:
        scheduled = (
            test_rows
            if spacing_seconds is None
            else _reschedule_rows(
                test_rows,
                test_truth,
                spacing_seconds=spacing_seconds,
                jitter_seconds=jitter_seconds,
                seed=seed,
            )
        )
        features = extract_features_from_rows(scheduled)
        predictions = run_attacks_from_features(
            features,
            methods=["temporal", "provider_lowcost"],
        )
        predictions.update(
            {
                "intent_hash": {
                    "session": _intent_hash_labels(test_rows, rephrase=False)
                },
                "carp_content_semantic": {
                    "session": test_content["semantic_labels"]
                },
                "carp_content": {"session": test_content["combined_labels"]},
            }
        )
        metrics = _metric_rows(
            predictions=predictions,
            truth_rows=test_truth,
            iterations=iterations,
            seed=seed,
        )
        schedule_stats = _schedule_stats(scheduled, test_truth)
        for row in metrics:
            if row["scope"] != "overall":
                continue
            stress_rows.append(
                {
                    "condition": condition,
                    "method": row["method"],
                    "arrival_spacing_seconds": "original"
                    if spacing_seconds is None
                    else spacing_seconds,
                    "jitter_seconds": jitter_seconds,
                    "peak_active_workflows": schedule_stats["peak_active_workflows"],
                    "precision": row["precision"],
                    "recall": row["recall"],
                    "f1": row["f1"],
                    "f1_ci_low": row["f1_ci_low"],
                    "f1_ci_high": row["f1_ci_high"],
                    "workflows": row["workflows"],
                    "requests": row["requests"],
                }
            )

    rephrased_schedule = _reschedule_rows(
        test_rows,
        test_truth,
        spacing_seconds=15,
        jitter_seconds=300,
        seed=seed,
    )
    rephrased_predictions = {
        "intent_hash": {"session": _intent_hash_labels(test_rows, rephrase=True)},
        "carp_content": {"session": rephrased_test_content["combined_labels"]},
    }
    for row in _metric_rows(
        predictions=rephrased_predictions,
        truth_rows=test_truth,
        iterations=iterations,
        seed=seed,
    ):
        if row["scope"] != "overall":
            continue
        stress_rows.append(
            {
                "condition": "concurrent_32_rephrased_intent",
                "method": row["method"],
                "arrival_spacing_seconds": 15,
                "jitter_seconds": 300,
                "peak_active_workflows": _schedule_stats(
                    rephrased_schedule, test_truth
                )["peak_active_workflows"],
                "precision": row["precision"],
                "recall": row["recall"],
                "f1": row["f1"],
                "f1_ci_low": row["f1_ci_low"],
                "f1_ci_high": row["f1_ci_high"],
                "workflows": row["workflows"],
                "requests": row["requests"],
            }
        )

    ablation_rows = _ablation_rows(
        calibration_content=calibration_content,
        test_content=test_content,
        calibration_truth=calibration_truth,
        test_truth=test_truth,
        embedding_seconds=embedding_seconds,
        iterations=iterations,
        seed=seed,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    stress_csv = output_dir / f"{OUTPUT_BASE}.csv"
    stress_md = output_dir / f"{OUTPUT_BASE}.md"
    ablation_csv = output_dir / f"{ABLATION_BASE}.csv"
    ablation_md = output_dir / f"{ABLATION_BASE}.md"
    write_csv(stress_csv, stress_rows)
    write_markdown(stress_md, stress_rows)
    write_csv(ablation_csv, ablation_rows)
    write_markdown(ablation_md, ablation_rows)
    return {
        "stress_csv": str(stress_csv),
        "stress_markdown": str(stress_md),
        "ablation_csv": str(ablation_csv),
        "ablation_markdown": str(ablation_md),
        "selected_thresholds": json.dumps(selected, sort_keys=True),
    }


def _content_predictions(
    attack_rows: list[dict[str, Any]],
    vector_by_id: dict[str, Any],
    truth_rows: list[dict[str, Any]],
    *,
    calibrate: bool = False,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    request_ids = sorted(str(row["request_id"]) for row in attack_rows)
    vectors = np.asarray([vector_by_id[request_id] for request_id in request_ids])
    cache_by_id = {
        str(row["request_id"]): str(row.get("cache_bucket") or "cache_unavailable")
        for row in attack_rows
    }
    semantic_pairs = {
        pair: score
        for pair, score in top_k_cosine_pairs(request_ids, vectors, top_k=24).items()
        if cache_by_id[pair[0]] == cache_by_id[pair[1]]
    }
    anchors = {str(row["request_id"]): _typed_anchors(row) for row in attack_rows}
    anchor_pairs = exact_anchor_pairs(anchors, max_bucket_size=20)
    strong_anchor_pairs = {
        pair: shared
        for pair, shared in anchor_pairs.items()
        if any(_is_strong_process_handle(anchor) for anchor in shared)
    }
    combined_pairs = dict(semantic_pairs)
    for pair, shared in anchor_pairs.items():
        dense = semantic_pairs.get(pair, 0.0)
        strong = any(_is_strong_process_handle(anchor) for anchor in shared)
        anchor_score = 0.90 if strong else 0.78
        combined_pairs[pair] = max(dense, anchor_score)

    if calibrate:
        semantic_threshold = _select_threshold(request_ids, semantic_pairs, truth_rows)
        combined_threshold = _select_threshold(request_ids, combined_pairs, truth_rows)
        thresholds = {
            "semantic": semantic_threshold,
            "combined": combined_threshold,
        }
    if thresholds is None:
        raise ValueError("thresholds are required outside calibration")
    return {
        "semantic_labels": labels_from_scores(
            request_ids,
            semantic_pairs,
            threshold=thresholds["semantic"],
            prefix="tau_semantic",
        ),
        "combined_labels": labels_from_scores(
            request_ids,
            combined_pairs,
            threshold=thresholds["combined"],
            prefix="tau_content",
        ),
        "typed_labels": labels_from_scores(
            request_ids,
            {pair: 1.0 for pair in strong_anchor_pairs},
            threshold=1.0,
            prefix="tau_typed",
        ),
        "semantic_candidates": len(semantic_pairs),
        "typed_candidates": len(anchor_pairs),
        "strong_typed_candidates": len(strong_anchor_pairs),
        "combined_candidates": len(set(semantic_pairs) | set(anchor_pairs)),
        "thresholds": thresholds,
    }


def _select_threshold(
    request_ids: list[str],
    pair_scores: dict[tuple[str, str], float],
    truth_rows: list[dict[str, Any]],
) -> float:
    truth = truth_labels(truth_rows, "session")
    rows = []
    for threshold in THRESHOLDS:
        labels = labels_from_scores(
            request_ids,
            pair_scores,
            threshold=threshold,
            prefix="calibration",
        )
        metrics = clustering_metrics(labels, truth)
        rows.append((threshold, metrics))
    eligible = [row for row in rows if row[1]["pairwise_precision"] >= 0.8]
    pool = eligible or rows
    return max(
        pool,
        key=lambda row: (
            row[1]["pairwise_f1"],
            row[1]["pairwise_precision"],
            row[0],
        ),
    )[0]


def _semantic_document(row: dict[str, Any], *, rephrase: bool = False) -> str:
    messages = [message for message in row.get("messages", []) if message.get("role") != "system"]
    first_user = next(
        (str(message.get("content", "")) for message in messages if message.get("role") == "user"),
        "",
    )
    tool_names = sorted(
        {
            str(schema.get("name", ""))
            for schema in row.get("tool_schemas", [])
            if schema.get("name")
        }
    )
    if rephrase:
        first_user = _rephrase_intent(first_user, str(row["request_id"]))
    text = f"task intent: {first_user[:2400]}\ntool vocabulary: {' '.join(tool_names)}".lower()
    text = ENTITY_RE.sub(lambda match: f" {match.group(1).lower()}_id ", text)
    return NUMBER_RE.sub(" number ", text)[:3600]


def _intent_hash_labels(
    attack_rows: list[dict[str, Any]], *, rephrase: bool
) -> dict[str, str]:
    labels = {}
    for row in attack_rows:
        document = _semantic_document(row, rephrase=rephrase)
        digest = hashlib.sha256(document.encode("utf-8")).hexdigest()[:20]
        labels[str(row["request_id"])] = f"intent_hash:{digest}"
    return labels


def _rephrase_intent(text: str, request_id: str) -> str:
    normalized = ENTITY_RE.sub(lambda match: f" {match.group(1).lower()}_id ", text.lower())
    normalized = NUMBER_RE.sub(" number ", normalized)
    for source, target in REPHRASE_MAP.items():
        normalized = re.sub(rf"\b{re.escape(source)}\b", target, normalized)
    clauses = [clause.strip() for clause in re.split(r"(?<=[.!?;])\s+", normalized) if clause.strip()]
    if len(clauses) > 1:
        shift = int(hashlib.sha256(request_id.encode()).hexdigest()[:4], 16) % len(clauses)
        clauses = clauses[shift:] + clauses[:shift]
    words = " ".join(clauses).split()
    variant = int(hashlib.sha256(f"variant:{request_id}".encode()).hexdigest()[:4], 16) % 3
    if variant == 1:
        words = [word for index, word in enumerate(words) if index % 11 != 3]
    elif variant == 2:
        words = ["request:", *words]
    return " ".join(words)


def _typed_anchors(row: dict[str, Any]) -> set[str]:
    return set(extract_stable_content_handles(row))


def _is_strong_process_handle(anchor: str) -> bool:
    return anchor.startswith("stable_project:")


def _reschedule_rows(
    attack_rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    *,
    spacing_seconds: int,
    jitter_seconds: int,
    seed: int,
) -> list[dict[str, Any]]:
    truth_by_id = {str(row["request_id"]): row for row in truth_rows}
    by_workflow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attack_rows:
        truth = truth_by_id[str(row["request_id"])]
        by_workflow[str(truth["workflow_id"])].append(row)
    workflow_order = sorted(
        by_workflow,
        key=lambda workflow: hashlib.sha256(f"{seed}:{workflow}".encode()).hexdigest(),
    )
    base = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
    scheduled: list[dict[str, Any]] = []
    for workflow_index, workflow in enumerate(workflow_order):
        rng = random.Random(f"{seed}:{workflow}")
        start = base + timedelta(seconds=workflow_index * spacing_seconds)
        previous = start - timedelta(seconds=1)
        members = sorted(
            by_workflow[workflow],
            key=lambda row: int(truth_by_id[str(row["request_id"])].get("turn_id", 0)),
        )
        for turn_index, row in enumerate(members):
            jitter = rng.randint(-jitter_seconds, jitter_seconds) if jitter_seconds else 0
            timestamp = start + timedelta(seconds=45 * turn_index + jitter)
            timestamp = max(timestamp, previous + timedelta(seconds=1))
            previous = timestamp
            copied = dict(row)
            copied["timestamp"] = timestamp.isoformat().replace("+00:00", "Z")
            scheduled.append(copied)
    return sorted(scheduled, key=lambda row: (row["timestamp"], row["request_id"]))


def _schedule_stats(
    attack_rows: list[dict[str, Any]], truth_rows: list[dict[str, Any]]
) -> dict[str, int]:
    truth_by_id = {str(row["request_id"]): row for row in truth_rows}
    intervals: dict[str, list[datetime]] = defaultdict(list)
    for row in attack_rows:
        workflow = str(truth_by_id[str(row["request_id"])]["workflow_id"])
        intervals[workflow].append(datetime.fromisoformat(str(row["timestamp"]).replace("Z", "+00:00")))
    events = []
    for timestamps in intervals.values():
        events.append((min(timestamps), 1))
        events.append((max(timestamps) + timedelta(microseconds=1), -1))
    active = 0
    peak = 0
    for _, delta in sorted(events, key=lambda item: (item[0], item[1])):
        active += delta
        peak = max(peak, active)
    return {"peak_active_workflows": peak}


def _ablation_rows(
    *,
    calibration_content: dict[str, Any],
    test_content: dict[str, Any],
    calibration_truth: list[dict[str, Any]],
    test_truth: list[dict[str, Any]],
    embedding_seconds: float,
    iterations: int,
    seed: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scope, content, truth in (
        ("calibration", calibration_content, calibration_truth),
        ("held_out", test_content, test_truth),
    ):
        predictions = {
            "semantic_only": {"session": content["semantic_labels"]},
            "stable_process_handle_only": {"session": content["typed_labels"]},
            "carp_content": {"session": content["combined_labels"]},
        }
        metrics = _metric_rows(
            predictions=predictions,
            truth_rows=truth,
            iterations=iterations,
            seed=seed,
        )
        for row in metrics:
            if row["scope"] != "overall":
                continue
            rows.append(
                {
                    "scope": scope,
                    "method": row["method"],
                    "precision": row["precision"],
                    "recall": row["recall"],
                    "f1": row["f1"],
                    "f1_ci_low": row["f1_ci_low"],
                    "f1_ci_high": row["f1_ci_high"],
                    "semantic_threshold": content["thresholds"]["semantic"],
                    "combined_threshold": content["thresholds"]["combined"],
                    "semantic_candidates": content["semantic_candidates"],
                    "typed_candidates": content["typed_candidates"],
                    "strong_typed_candidates": content["strong_typed_candidates"],
                    "combined_candidates": content["combined_candidates"],
                    "embedding_seconds_all_requests": embedding_seconds,
                    "workflows": row["workflows"],
                    "requests": row["requests"],
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    print(
        summarize_temporal_stress(
            dataset_dir=args.dataset_dir,
            output_dir=args.output_dir,
            iterations=args.iterations,
            seed=args.seed,
        )
    )


if __name__ == "__main__":
    main()
