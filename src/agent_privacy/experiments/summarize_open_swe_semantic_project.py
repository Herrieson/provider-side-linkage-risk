from __future__ import annotations

import argparse
import hashlib
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from agent_privacy.evaluation.clustering import clustering_metrics
from agent_privacy.experiments.bootstrap_ci import _quantile, _weighted_pairwise_metrics
from agent_privacy.experiments.semantic_linkage import (
    encode_documents,
    labels_from_scores,
    write_markdown,
)
from agent_privacy.experiments.summarize_open_swe_main_session import (
    _exact_message_nesting_labels,
)
from agent_privacy.experiments.summarize_open_swe_strict_removal import _strict_sanitize
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET_DIR = Path("artifacts/datasets/open_swe_traces_raw_1000")
DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "open_swe_strict_semantic_project_linkage"
TURN_IDS = {3, 6, 9, 12}
TECHNICAL_LINE_RE = re.compile(
    r"(?:error|exception|failed|test|assert|import|class |def |function|module|package|"
    r"build|compile|dependency|config|\.py\b|\.js\b|\.ts\b|\.go\b|\.rs\b|\.java\b|"
    r"pytest|npm|cargo|gradle|maven|makefile|traceback)",
    re.IGNORECASE,
)
THRESHOLDS = tuple(value / 100 for value in range(20, 96, 2))
ALPHAS = (0.25, 0.50, 0.75)
SPARSE_FLOORS = (0.20, 0.30, 0.40)


def summarize_strict_semantic_project(
    *,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    seed: int = 7,
    output_base: str = OUTPUT_BASE,
) -> dict[str, str]:
    truth_rows = [
        row
        for row in read_jsonl(dataset_dir / "ground_truth.jsonl")
        if int(row.get("turn_id", -1)) in TURN_IDS
    ]
    request_ids = {str(row["request_id"]) for row in truth_rows}
    attack_rows = [
        _strict_sanitize(row)
        for row in read_jsonl(dataset_dir / "attack_view.jsonl")
        if str(row["request_id"]) in request_ids
    ]
    session_labels = _exact_message_nesting_labels(attack_rows)
    session_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attack_rows:
        session_rows[session_labels[str(row["request_id"])]].append(row)
    truth_by_request = {str(row["request_id"]): row for row in truth_rows}
    session_truth: dict[str, str] = {}
    session_workflow: dict[str, str] = {}
    for session, rows in session_rows.items():
        projects = {str(truth_by_request[str(row["request_id"])]["project_id"]) for row in rows}
        workflows = {str(truth_by_request[str(row["request_id"])]["workflow_id"]) for row in rows}
        if len(projects) != 1 or len(workflows) != 1:
            raise ValueError("strict exact-nesting sessions must be pure before project linkage")
        session_truth[session] = projects.pop()
        session_workflow[session] = workflows.pop()

    dense_documents = {
        session: _dense_document(rows) for session, rows in session_rows.items()
    }
    sparse_documents = {
        session: _sparse_document(rows) for session, rows in session_rows.items()
    }
    session_ids = sorted(session_rows)
    encode_start = time.perf_counter()
    encoded_ids, dense_vectors = encode_documents(dense_documents)
    embedding_seconds = time.perf_counter() - encode_start
    if encoded_ids != session_ids:
        raise ValueError("semantic encoder returned an unexpected session ordering")
    vectorizer = TfidfVectorizer(
        lowercase=True,
        token_pattern=r"(?u)\b[A-Za-z_][A-Za-z0-9_.:-]{2,}\b",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.60,
        max_features=40_000,
        sublinear_tf=True,
        norm="l2",
    )
    sparse_matrix = vectorizer.fit_transform([sparse_documents[session] for session in session_ids])
    dense_similarity = dense_vectors @ dense_vectors.T
    sparse_similarity = (sparse_matrix @ sparse_matrix.T).toarray().astype(np.float32)

    calibration_ids, test_ids = _project_disjoint_split(session_ids, session_truth, seed=seed)
    calibration_truth = {session: session_truth[session] for session in calibration_ids}
    test_truth = {session: session_truth[session] for session in test_ids}
    index_by_id = {session: index for index, session in enumerate(session_ids)}

    configurations: list[tuple[str, float, float, np.ndarray]] = [
        ("dense_only", 1.0, 0.0, dense_similarity),
        ("structured_tfidf_only", 0.0, 0.0, sparse_similarity),
    ]
    configurations.extend(
        (
            "carp_content_project",
            alpha,
            sparse_floor,
            alpha * dense_similarity + (1.0 - alpha) * sparse_similarity,
        )
        for alpha in ALPHAS
        for sparse_floor in SPARSE_FLOORS
    )
    calibration_rows: list[dict[str, Any]] = []
    for method, alpha, sparse_floor, matrix in configurations:
        pair_scores = _top_k_matrix_pairs(
            calibration_ids,
            matrix,
            index_by_id,
            top_k=24,
            gate_matrix=sparse_similarity if sparse_floor else None,
            gate_threshold=sparse_floor,
        )
        threshold, metrics = _select_threshold(calibration_ids, pair_scores, calibration_truth)
        calibration_rows.append(
            _result_row(
                scope="calibration_project_disjoint",
                method=method,
                alpha=alpha,
                sparse_floor=sparse_floor,
                threshold=threshold,
                metrics=metrics,
                candidates=len(pair_scores),
                sessions=len(calibration_ids),
                projects=len(set(calibration_truth.values())),
                embedding_seconds=embedding_seconds,
                vocabulary_size=len(vectorizer.vocabulary_),
            )
        )
    combined_calibration = [
        row for row in calibration_rows if row["method"] == "carp_content_project"
    ]
    best_combined = max(
        combined_calibration,
        key=lambda row: (
            row["f1"],
            row["precision"],
            row["sparse_floor"],
            row["alpha_dense"],
        ),
    )
    chosen = {
        "dense_only": next(row for row in calibration_rows if row["method"] == "dense_only"),
        "structured_tfidf_only": next(
            row for row in calibration_rows if row["method"] == "structured_tfidf_only"
        ),
        "carp_content_project": best_combined,
    }
    test_rows: list[dict[str, Any]] = []
    for method, calibration in chosen.items():
        alpha = float(calibration["alpha_dense"])
        sparse_floor = float(calibration["sparse_floor"])
        matrix = (
            dense_similarity
            if method == "dense_only"
            else sparse_similarity
            if method == "structured_tfidf_only"
            else alpha * dense_similarity + (1.0 - alpha) * sparse_similarity
        )
        pair_scores = _top_k_matrix_pairs(
            test_ids,
            matrix,
            index_by_id,
            top_k=24,
            gate_matrix=sparse_similarity if sparse_floor else None,
            gate_threshold=sparse_floor,
        )
        labels = labels_from_scores(
            test_ids,
            pair_scores,
            threshold=float(calibration["threshold"]),
            prefix=method,
        )
        metrics = clustering_metrics(labels, test_truth)
        ci = _entity_bootstrap_ci(labels, test_truth, seed=seed)
        test_rows.append(
            _result_row(
                scope="held_out_unseen_projects",
                method=method,
                alpha=alpha,
                sparse_floor=sparse_floor,
                threshold=float(calibration["threshold"]),
                metrics=metrics,
                ci=ci,
                candidates=len(pair_scores),
                sessions=len(test_ids),
                projects=len(set(test_truth.values())),
                embedding_seconds=embedding_seconds,
                vocabulary_size=len(vectorizer.vocabulary_),
            )
        )
    singleton_labels = {session: f"strict_singleton:{session}" for session in test_ids}
    singleton_metrics = clustering_metrics(singleton_labels, test_truth)
    test_rows.insert(
        0,
        _result_row(
            scope="held_out_unseen_projects",
            method="strict_direct_anchor",
            alpha=0.0,
            sparse_floor=0.0,
            threshold=1.0,
            metrics=singleton_metrics,
            ci=_entity_bootstrap_ci(singleton_labels, test_truth, seed=seed),
            candidates=0,
            sessions=len(test_ids),
            projects=len(set(test_truth.values())),
            embedding_seconds=embedding_seconds,
            vocabulary_size=len(vectorizer.vocabulary_),
        ),
    )
    rows = calibration_rows + test_rows
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{output_base}.csv"
    md_path = output_dir / f"{output_base}.md"
    write_csv(csv_path, rows)
    write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path)}


def _dense_document(rows: list[dict[str, Any]]) -> str:
    longest = max(rows, key=lambda row: len(row.get("messages", [])))
    messages = [message for message in longest.get("messages", []) if message.get("role") != "system"]
    first_user = next(
        (str(message.get("content", "")) for message in messages if message.get("role") == "user"),
        "",
    )
    evidence = []
    for message in messages:
        for line in str(message.get("content", "")).splitlines():
            line = line.strip()
            if line and TECHNICAL_LINE_RE.search(line):
                evidence.append(line[:320])
            if len(evidence) >= 24:
                break
        if len(evidence) >= 24:
            break
    return ("task: " + first_user[:1800] + "\ntechnical evidence:\n" + "\n".join(evidence))[:7000]


def _sparse_document(rows: list[dict[str, Any]]) -> str:
    longest = max(rows, key=lambda row: len(row.get("messages", [])))
    return "\n".join(
        str(message.get("content", ""))
        for message in longest.get("messages", [])
        if message.get("role") != "system"
    )[:40_000]


def _project_disjoint_split(
    session_ids: list[str], session_truth: dict[str, str], *, seed: int
) -> tuple[list[str], list[str]]:
    projects = sorted(
        set(session_truth.values()),
        key=lambda project: hashlib.sha256(f"{seed}:project:{project}".encode()).hexdigest(),
    )
    calibration_projects = set(projects[: round(len(projects) * 0.25)])
    calibration = [
        session for session in session_ids if session_truth[session] in calibration_projects
    ]
    test = [session for session in session_ids if session_truth[session] not in calibration_projects]
    return calibration, test


def _top_k_matrix_pairs(
    selected_ids: list[str],
    matrix: np.ndarray,
    index_by_id: dict[str, int],
    *,
    top_k: int,
    gate_matrix: np.ndarray | None = None,
    gate_threshold: float = 0.0,
) -> dict[tuple[str, str], float]:
    pairs: dict[tuple[str, str], float] = {}
    if len(selected_ids) < 2 or top_k <= 0:
        return pairs
    selected_indexes = np.asarray([index_by_id[session] for session in selected_ids])
    scoped = matrix[np.ix_(selected_indexes, selected_indexes)].copy()
    np.fill_diagonal(scoped, -np.inf)
    k = min(top_k, len(selected_ids) - 1)
    for row_index, session in enumerate(selected_ids):
        neighbors = np.argpartition(scoped[row_index], -k)[-k:]
        for neighbor in neighbors:
            if (
                gate_matrix is not None
                and gate_matrix[
                    index_by_id[session],
                    index_by_id[selected_ids[int(neighbor)]],
                ]
                < gate_threshold
            ):
                continue
            left, right = sorted((session, selected_ids[int(neighbor)]))
            pairs[(left, right)] = max(
                float(scoped[row_index, neighbor]),
                pairs.get((left, right), -1.0),
            )
    return pairs


def _select_threshold(
    session_ids: list[str],
    pair_scores: dict[tuple[str, str], float],
    truth: dict[str, str],
) -> tuple[float, dict[str, float]]:
    rows = []
    for threshold in THRESHOLDS:
        labels = labels_from_scores(
            session_ids,
            pair_scores,
            threshold=threshold,
            prefix="project_calibration",
        )
        rows.append((threshold, clustering_metrics(labels, truth)))
    eligible = [row for row in rows if row[1]["pairwise_precision"] >= 0.95]
    pool = eligible or rows
    return max(pool, key=lambda row: (_metric_rank(row[1]), row[0]))


def _metric_rank(metrics: dict[str, float]) -> tuple[float, float]:
    return metrics["pairwise_f1"], metrics["pairwise_precision"]


def _entity_bootstrap_ci(
    predictions: dict[str, str],
    truth: dict[str, str],
    *,
    seed: int,
    iterations: int = 500,
) -> dict[str, float]:
    projects = sorted(set(truth.values()))
    request_to_project = dict(truth)
    rng = random.Random(seed)
    f1_samples = []
    for _ in range(iterations):
        weights = Counter(rng.choices(projects, k=len(projects)))
        metrics = _weighted_pairwise_metrics(
            predictions,
            truth,
            request_to_project,
            weights,
        )
        f1_samples.append(metrics["pairwise_f1"])
    return {
        "f1_ci_low": _quantile(f1_samples, 0.025),
        "f1_ci_high": _quantile(f1_samples, 0.975),
    }


def _result_row(
    *,
    scope: str,
    method: str,
    alpha: float,
    sparse_floor: float,
    threshold: float,
    metrics: dict[str, float],
    candidates: int,
    sessions: int,
    projects: int,
    embedding_seconds: float,
    vocabulary_size: int,
    ci: dict[str, float] | None = None,
) -> dict[str, Any]:
    return {
        "scope": scope,
        "method": method,
        "alpha_dense": alpha,
        "sparse_floor": sparse_floor,
        "threshold": threshold,
        "precision": metrics["pairwise_precision"],
        "recall": metrics["pairwise_recall"],
        "f1": metrics["pairwise_f1"],
        "f1_ci_low": "" if ci is None else ci["f1_ci_low"],
        "f1_ci_high": "" if ci is None else ci["f1_ci_high"],
        "purity": metrics["purity"],
        "split_rate": metrics["split_rate"],
        "merge_rate": metrics["merge_rate"],
        "clusters": int(metrics["clusters"]),
        "candidates": candidates,
        "sessions": sessions,
        "projects": projects,
        "embedding_seconds": embedding_seconds,
        "tfidf_vocabulary": vocabulary_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output-base", type=str, default=OUTPUT_BASE)
    args = parser.parse_args()
    print(
        summarize_strict_semantic_project(
            dataset_dir=args.dataset_dir,
            output_dir=args.output_dir,
            seed=args.seed,
            output_base=args.output_base,
        )
    )


if __name__ == "__main__":
    main()
