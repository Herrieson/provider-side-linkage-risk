from __future__ import annotations

import argparse
import json
import resource
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from agent_privacy.agent_state.streaming import AgentNativeLinker, LinkerConfig
from agent_privacy.evaluation.clustering import clustering_metrics, truth_labels
from agent_privacy.evaluation.selective import (
    false_merge_amplification,
    selective_linkage_metrics,
)
from agent_privacy.io import iter_jsonl, read_jsonl, write_json


def run_agent_native_dataset(dataset_dir: Path) -> dict[str, Any]:
    start = time.perf_counter()
    result = AgentNativeLinker().run(iter_jsonl(dataset_dir / "attack_view.jsonl"))
    elapsed = time.perf_counter() - start
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    metrics: dict[str, dict[str, float]] = {}
    for level, labels in result.predictions.items():
        truth = truth_labels(truth_rows, level)
        if not truth:
            continue
        level_metrics = clustering_metrics(labels, truth)
        level_metrics.update(false_merge_amplification(labels, truth))
        if level == "session":
            level_metrics.update(selective_linkage_metrics(result.decisions, truth))
        metrics[level] = level_metrics
    return {
        "dataset_dir": str(dataset_dir),
        "method": "agent_native_v0",
        "elapsed_seconds": elapsed,
        "peak_rss_kib": _peak_rss_kib(),
        "stats": result.stats,
        "metrics": metrics,
        "decision_counts": _decision_counts(result.decisions),
    }


def run_scale_gate(requests: int) -> dict[str, Any]:
    smoke_rows = read_jsonl(Path("examples/tool_agent_smoke/dataset/attack_view.jsonl"))
    start = time.perf_counter()
    result = AgentNativeLinker(
        LinkerConfig(retain_debug_states=False)
    ).run(_scale_rows(smoke_rows, requests))
    elapsed = time.perf_counter() - start
    stats = dict(result.stats)
    max_candidates = LinkerConfig().max_candidates_per_request
    max_posting = LinkerConfig().max_posting_size
    gates = {
        "request_count_exact": stats["requests_processed"] == requests,
        "candidate_bound": stats["max_candidates_for_request"] <= max_candidates,
        "comparison_bound": stats["candidates_considered"] <= requests * max_candidates,
        "posting_cap_exercised_or_respected": (
            stats["heavy_hitter_suppressions"] > 0
            or stats["peak_active_postings"] <= requests * max_posting
        ),
    }
    return {
        "method": "agent_native_v0",
        "requests": requests,
        "elapsed_seconds": elapsed,
        "requests_per_second": requests / elapsed if elapsed else 0.0,
        "peak_rss_kib": _peak_rss_kib(),
        "stats": stats,
        "gates": gates,
        "passed": all(gates.values()),
    }


def _scale_rows(base_rows: list[dict[str, Any]], requests: int) -> Iterator[dict[str, Any]]:
    grouped = [base_rows[0:2], base_rows[2:4], base_rows[4:6]]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    emitted = 0
    workflow_index = 0
    while emitted < requests:
        template = grouped[workflow_index % len(grouped)]
        replacements = _workflow_replacements(template, workflow_index)
        for turn_index, source in enumerate(template):
            if emitted >= requests:
                return
            row = deepcopy(source)
            row["request_id"] = f"scale_req_{emitted:09d}"
            timestamp = start + timedelta(seconds=emitted * 3)
            row["timestamp"] = timestamp.isoformat().replace("+00:00", "Z")
            for message in row.get("messages", []):
                content = str(message.get("content", ""))
                for original, replacement in replacements.items():
                    content = content.replace(original, replacement)
                message["content"] = content
            row["provider_metadata"] = {
                **row.get("provider_metadata", {}),
                "controlled_scale_replay": True,
                "turn_index": turn_index,
            }
            emitted += 1
            yield row
        workflow_index += 1


def _workflow_replacements(
    rows: list[dict[str, Any]], workflow_index: int
) -> dict[str, str]:
    values = {
        "customer_alpha001": f"customer_scale{workflow_index:07d}",
        "order_778899": f"order_scale{workflow_index:07d}",
        "customer_beta002": f"customer_scale{workflow_index:07d}",
        "order_554433": f"order_scale{workflow_index:07d}",
        "product_12345": f"product_scale{workflow_index:07d}",
        "product_67890": f"product_alt{workflow_index:07d}",
        "account_gamma003": f"account_scale{workflow_index:07d}",
        "reservation_ABC123": f"reservation_scale{workflow_index:07d}",
        "flight_DL404": f"flight_scale{workflow_index:07d}",
    }
    text = json.dumps(rows)
    return {original: replacement for original, replacement in values.items() if original in text}


def _decision_counts(decisions: Iterable[Any]) -> dict[str, int]:
    counts = {"accept": 0, "reject": 0, "abstain": 0}
    for decision in decisions:
        counts[decision.disposition] += 1
    return counts


def _peak_rss_kib() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the bounded Agent-native linkage feasibility implementation."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dataset-dir", type=Path)
    group.add_argument("--scale-requests", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.dataset_dir:
        report = run_agent_native_dataset(args.dataset_dir)
    else:
        report = run_scale_gate(args.scale_requests)
    if args.output:
        write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
