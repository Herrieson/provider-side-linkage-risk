from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

from agent_privacy.attacks.pipeline import run_provider_lowcost_from_features_with_stats
from agent_privacy.evaluation.clustering import clustering_metrics
from agent_privacy.features.extract import RequestFeatures
from agent_privacy.reporting import write_csv


DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "observation_indistinguishability"


def observation_equivalence_pairwise_bound(
    multiplicity: int,
    requests_per_entity: int,
) -> dict[str, float]:
    """Expected pairwise bound when equal entities have exchangeable views.

    If k entities contribute the same number of requests and their provider-visible
    sequences are identical up to exchangeable request identifiers, the observations
    contain no information about which entity generated a request. An observation-
    Every observation-invariant predicted pair has true-match probability
    (m-1)/(km-1). Expected precision therefore cannot exceed that value; recall is
    at most one. Merging the entire equivalence class attains both bounds, yielding
    expected F1 2(m-1)/(m(k+1)-2). These approach 1/k and 2/(k+1) as m grows.
    """

    if multiplicity < 1:
        raise ValueError("multiplicity must be positive")
    if requests_per_entity < 2:
        raise ValueError("requests_per_entity must be at least two")
    precision = (requests_per_entity - 1) / (
        multiplicity * requests_per_entity - 1
    )
    f1 = 2 * precision / (1 + precision)
    return {"precision": precision, "recall": 1.0, "f1": f1}


def summarize_indistinguishability(
    *,
    groups: int = 100,
    multiplicities: tuple[int, ...] = (1, 2, 4, 8, 16),
    turns: int = 4,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, str]:
    rows = [
        _run_condition(groups=groups, multiplicity=multiplicity, turns=turns)
        for multiplicity in multiplicities
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path)}


def _run_condition(*, groups: int, multiplicity: int, turns: int) -> dict[str, Any]:
    features, truth = _exchangeable_features(
        groups=groups,
        multiplicity=multiplicity,
        turns=turns,
    )
    predictions, stats = run_provider_lowcost_from_features_with_stats(features)
    metrics = clustering_metrics(predictions["session"], truth)
    bound = observation_equivalence_pairwise_bound(multiplicity, turns)
    return {
        "entities_per_equivalence_class": multiplicity,
        "equivalence_classes": groups,
        "requests": len(features),
        "requests_per_entity": turns,
        "bayes_entity_accuracy_ceiling": 1.0 / multiplicity,
        "expected_pairwise_precision_upper_bound": bound["precision"],
        "expected_pairwise_recall_upper_bound": bound["recall"],
        "expected_pairwise_f1_upper_bound": bound["f1"],
        "carp_precision": metrics["pairwise_precision"],
        "carp_recall": metrics["pairwise_recall"],
        "carp_f1": metrics["pairwise_f1"],
        "carp_clusters": int(metrics["clusters"]),
        "candidate_pair_events": int(stats["candidate_pairs_considered"]),
    }


def _exchangeable_features(
    *,
    groups: int,
    multiplicity: int,
    turns: int,
) -> tuple[dict[str, RequestFeatures], dict[str, str]]:
    """Build entities whose complete visible sequences are exchangeable within a group."""

    if groups < 1 or multiplicity < 1 or turns < 2:
        raise ValueError("groups and multiplicity must be positive; turns must be at least two")
    features: dict[str, RequestFeatures] = {}
    truth: dict[str, str] = {}
    for group in range(groups):
        shared_handle = f"equivalence-{group:05d}"
        shared_base = {f"{shared_handle}-context-{index}" for index in range(12)}
        for entity in range(multiplicity):
            truth_label = f"entity-{group:05d}-{entity:03d}"
            for turn in range(turns):
                request_id = _opaque_request_id(group, entity, turn)
                # Every entity in the group has the same visible sequence: same time,
                # length, handles, schema, and cumulative text features at each turn.
                shingles = shared_base | {
                    f"{shared_handle}-turn-{prior}-{index}"
                    for prior in range(turn + 1)
                    for index in range(6)
                }
                features[request_id] = RequestFeatures(
                    request_id=request_id,
                    timestamp_minute=group * 20 + turn,
                    token_count=240 + turn * 40,
                    words=frozenset(),
                    shingles=frozenset(shingles),
                    identifiers=frozenset(
                        {
                            f"business_project:case:{shared_handle}",
                            f"trace:{shared_handle}",
                        }
                    ),
                    paths=frozenset(),
                    usernames=frozenset(),
                    domains=frozenset(),
                    traces=frozenset({f"trace-{shared_handle}"}),
                    cache_bucket=f"cache-{group:05d}",
                    semantic_signatures=frozenset(
                        {f"semantic-{shared_handle}-{index}" for index in range(3)}
                    ),
                    tool_fingerprint="shared-tool-schema",
                    system_fingerprint="shared-system-prompt",
                )
                truth[request_id] = truth_label
    return features, truth


def _opaque_request_id(group: int, entity: int, turn: int) -> str:
    # Request IDs are provider-visible, so they must not share a latent-entity prefix.
    payload = f"observation-bound-v1:{group}:{entity}:{turn}".encode()
    return f"req_{hashlib.sha256(payload).hexdigest()[:24]}"


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = list(rows[0]) if rows else []
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        values = []
        for header in headers:
            value = row[header]
            values.append(f"{value:.3f}" if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(
        [
            "",
            "Within each equivalence class, every entity has the same provider-visible sequence, ",
            "with opaque request identifiers independent of entity. With `k` equal entities, closed-set entity ",
            "accuracy is at most `1/k`. Retaining every true within-entity request pair requires ",
            "merging the class. For `m` requests/entity, expected pairwise precision is bounded by ",
            "`(m-1)/(km-1)`, recall by `1`, and F1 by `2(m-1)/(m(k+1)-2)`; merging the whole ",
            "class attains the bound. The large-`m` limits are `1/k` and `2/(k+1)`. ",
            "This is an observation-equivalence limit, not a claim about deployments that expose ",
            "additional side information.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", type=int, default=100)
    parser.add_argument("--multiplicities", type=int, nargs="+", default=[1, 2, 4, 8, 16])
    parser.add_argument("--turns", type=int, default=4)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(
        summarize_indistinguishability(
            groups=args.groups,
            multiplicities=tuple(args.multiplicities),
            turns=args.turns,
            output_dir=args.output_dir,
        )
    )


if __name__ == "__main__":
    main()
