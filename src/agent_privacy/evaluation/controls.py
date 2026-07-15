from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any

from agent_privacy.evaluation.clustering import truth_labels


CONTROL_METHODS = {"random", "oracle_size_random", "same_size_random"}
LEVELS = ["session", "user", "project", "org"]


def split_control_methods(methods: list[str]) -> tuple[list[str], list[str]]:
    feature_methods = [method for method in methods if method not in CONTROL_METHODS]
    control_methods = [method for method in methods if method in CONTROL_METHODS]
    return feature_methods, control_methods


def control_predictions(
    *,
    request_ids: list[str],
    truth_rows: list[dict[str, Any]],
    methods: list[str],
    seed: int = 7,
    levels: list[str] | None = None,
) -> dict[str, dict[str, dict[str, str]]]:
    selected_levels = levels or LEVELS
    predictions: dict[str, dict[str, dict[str, str]]] = {}
    for method in methods:
        rng = random.Random(_method_seed(seed, method))
        level_predictions: dict[str, dict[str, str]] = {}
        for level in selected_levels:
            truth = truth_labels(truth_rows, level)
            scoped_ids = [request_id for request_id in request_ids if request_id in truth]
            if not scoped_ids:
                continue
            if method == "random":
                level_predictions[level] = random_labels(scoped_ids, rng=rng)
            elif method in {"oracle_size_random", "same_size_random"}:
                level_predictions[level] = oracle_size_random_labels(
                    scoped_ids,
                    truth,
                    rng=rng,
                    prefix=method,
                )
        predictions[method] = level_predictions
    return predictions


def random_labels(
    request_ids: list[str],
    *,
    rng: random.Random,
    cluster_count: int | None = None,
    prefix: str = "random",
) -> dict[str, str]:
    if not request_ids:
        return {}
    n_clusters = cluster_count or max(1, int(round(math.sqrt(len(request_ids)))))
    shuffled = sorted(request_ids)
    rng.shuffle(shuffled)
    return {
        request_id: f"{prefix}_{index % n_clusters}"
        for index, request_id in enumerate(shuffled)
    }


def oracle_size_random_labels(
    request_ids: list[str],
    truth: dict[str, str],
    *,
    rng: random.Random,
    prefix: str = "oracle_size_random",
) -> dict[str, str]:
    truth_clusters: dict[str, list[str]] = defaultdict(list)
    request_id_set = set(request_ids)
    for request_id, label in truth.items():
        if request_id in request_id_set:
            truth_clusters[label].append(request_id)
    sizes = sorted((len(members) for members in truth_clusters.values()), reverse=True)
    shuffled = sorted(request_ids)
    rng.shuffle(shuffled)
    labels: dict[str, str] = {}
    cursor = 0
    for cluster_index, size in enumerate(sizes):
        for request_id in shuffled[cursor : cursor + size]:
            labels[request_id] = f"{prefix}_{cluster_index}"
        cursor += size
    for request_id in shuffled[cursor:]:
        labels[request_id] = f"{prefix}_overflow"
    return labels


def _method_seed(seed: int, method: str) -> int:
    return seed + sum(ord(char) for char in method)
