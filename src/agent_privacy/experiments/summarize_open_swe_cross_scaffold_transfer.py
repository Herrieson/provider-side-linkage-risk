from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from agent_privacy.evaluation.clustering import clustering_metrics
from agent_privacy.experiments.semantic_linkage import (
    encode_documents,
    labels_from_scores,
    write_markdown,
)
from agent_privacy.experiments.summarize_open_swe_main_session import (
    _exact_message_nesting_labels,
)
from agent_privacy.experiments.summarize_open_swe_semantic_project import (
    ALPHAS,
    SPARSE_FLOORS,
    _dense_document,
    _entity_bootstrap_ci,
    _project_disjoint_split,
    _select_threshold,
    _sparse_document,
    _top_k_matrix_pairs,
)
from agent_privacy.experiments.summarize_open_swe_strict_removal import _strict_sanitize
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_OPENHANDS_DIR = Path("artifacts/datasets/open_swe_traces_raw_1000")
DEFAULT_SWEAGENT_DIR = Path("artifacts/datasets/open_swe_traces_sweagent_minimax_raw_500")
DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "open_swe_cross_scaffold_zero_tuning"
TURN_IDS = {3, 6, 9, 12}
MUTUAL_MARGINS = (0.00, 0.02, 0.05, 0.10)


@dataclass(frozen=True)
class ScaffoldData:
    name: str
    session_ids: list[str]
    dense_documents: dict[str, str]
    sparse_documents: dict[str, str]
    truth: dict[str, str]
    dense_vectors: np.ndarray


def summarize_cross_scaffold_transfer(
    *,
    openhands_dir: Path = DEFAULT_OPENHANDS_DIR,
    sweagent_dir: Path = DEFAULT_SWEAGENT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    seed: int = 7,
) -> dict[str, str]:
    openhands = _load_scaffold("OpenHands", openhands_dir)
    sweagent = _load_scaffold("SWE-agent", sweagent_dir)
    rows = []
    rows.extend(_transfer_rows(openhands, sweagent, seed=seed))
    rows.extend(_transfer_rows(sweagent, openhands, seed=seed))
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
    write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path)}


def _load_scaffold(name: str, dataset_dir: Path) -> ScaffoldData:
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
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attack_rows:
        grouped[session_labels[str(row["request_id"])]].append(row)
    truth_by_request = {str(row["request_id"]): row for row in truth_rows}
    truth: dict[str, str] = {}
    for session, rows in grouped.items():
        projects = {
            str(truth_by_request[str(row["request_id"])]["project_id"]) for row in rows
        }
        if len(projects) != 1:
            raise ValueError("strict sessions must be project-pure")
        truth[session] = projects.pop()
    dense_documents = {session: _dense_document(rows) for session, rows in grouped.items()}
    sparse_documents = {session: _sparse_document(rows) for session, rows in grouped.items()}
    session_ids, dense_vectors = encode_documents(dense_documents)
    return ScaffoldData(
        name=name,
        session_ids=session_ids,
        dense_documents=dense_documents,
        sparse_documents=sparse_documents,
        truth=truth,
        dense_vectors=dense_vectors,
    )


def _transfer_rows(
    source: ScaffoldData, target: ScaffoldData, *, seed: int
) -> list[dict[str, Any]]:
    calibration_ids, _ = _project_disjoint_split(
        source.session_ids, source.truth, seed=seed
    )
    source_index = {session: index for index, session in enumerate(source.session_ids)}
    calibration_indexes = [source_index[session] for session in calibration_ids]
    calibration_dense = source.dense_vectors[calibration_indexes]
    calibration_dense_similarity = calibration_dense @ calibration_dense.T
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
    calibration_sparse = vectorizer.fit_transform(
        [source.sparse_documents[session] for session in calibration_ids]
    )
    calibration_sparse_similarity = (
        calibration_sparse @ calibration_sparse.T
    ).toarray().astype(np.float32)
    calibration_truth = {session: source.truth[session] for session in calibration_ids}
    calibration_index = {session: index for index, session in enumerate(calibration_ids)}

    configurations: list[tuple[str, float, float, np.ndarray]] = [
        ("dense_only", 1.0, 0.0, calibration_dense_similarity),
        ("structured_tfidf_only", 0.0, 0.0, calibration_sparse_similarity),
    ]
    configurations.extend(
        (
            "carp_content_project",
            alpha,
            sparse_floor,
            alpha * calibration_dense_similarity
            + (1.0 - alpha) * calibration_sparse_similarity,
        )
        for alpha in ALPHAS
        for sparse_floor in SPARSE_FLOORS
    )
    calibrated: list[dict[str, Any]] = []
    for method, alpha, sparse_floor, matrix in configurations:
        pairs = _top_k_matrix_pairs(
            calibration_ids,
            matrix,
            calibration_index,
            top_k=24,
            gate_matrix=calibration_sparse_similarity if sparse_floor else None,
            gate_threshold=sparse_floor,
        )
        threshold, metrics = _select_threshold(
            calibration_ids, pairs, calibration_truth
        )
        threshold_quantile = (
            sum(score <= threshold for score in pairs.values()) / len(pairs)
            if pairs
            else 1.0
        )
        calibrated.append(
            {
                "method": method,
                "alpha_dense": alpha,
                "sparse_floor": sparse_floor,
                "threshold": threshold,
                "threshold_quantile": threshold_quantile,
                "calibration_sessions": len(calibration_ids),
                "calibration_f1": metrics["pairwise_f1"],
                "calibration_precision": metrics["pairwise_precision"],
            }
        )
    combined = [row for row in calibrated if row["method"] == "carp_content_project"]
    mutual_calibrated = []
    for alpha in ALPHAS:
        for sparse_floor in SPARSE_FLOORS:
            matrix = (
                alpha * calibration_dense_similarity
                + (1.0 - alpha) * calibration_sparse_similarity
            )
            for margin in MUTUAL_MARGINS:
                pairs = _mutual_margin_pairs(
                    calibration_ids,
                    matrix,
                    gate_matrix=calibration_sparse_similarity,
                    gate_threshold=sparse_floor,
                    margin=margin,
                )
                labels = labels_from_scores(
                    calibration_ids,
                    pairs,
                    threshold=0.5,
                    prefix="mutual-calibration",
                )
                metrics = clustering_metrics(labels, calibration_truth)
                mutual_calibrated.append(
                    {
                        "method": "carp_content_mutual",
                        "alpha_dense": alpha,
                        "sparse_floor": sparse_floor,
                        "threshold": "",
                        "threshold_quantile": "",
                        "mutual_margin": margin,
                        "calibration_sessions": len(calibration_ids),
                        "calibration_f1": metrics["pairwise_f1"],
                        "calibration_precision": metrics["pairwise_precision"],
                    }
                )
    mutual_eligible = [
        row for row in mutual_calibrated if row["calibration_precision"] >= 0.95
    ]
    selected_mutual = max(
        mutual_eligible or mutual_calibrated,
        key=lambda row: (
            row["calibration_f1"],
            row["calibration_precision"],
            row["mutual_margin"],
        ),
    )
    selected = {
        "dense_only": next(row for row in calibrated if row["method"] == "dense_only"),
        "structured_tfidf_only": next(
            row for row in calibrated if row["method"] == "structured_tfidf_only"
        ),
        "carp_content_project": max(
            combined,
            key=lambda row: (
                row["calibration_f1"],
                row["calibration_precision"],
                row["sparse_floor"],
                row["alpha_dense"],
            ),
        ),
    }

    target_sparse = vectorizer.transform(
        [target.sparse_documents[session] for session in target.session_ids]
    )
    target_sparse_similarity = (target_sparse @ target_sparse.T).toarray().astype(np.float32)
    target_dense_similarity = target.dense_vectors @ target.dense_vectors.T
    target_index = {session: index for index, session in enumerate(target.session_ids)}
    rows = []
    singleton = {session: f"singleton:{session}" for session in target.session_ids}
    rows.append(
        _row(
            source=source,
            target=target,
            method="strict_direct_anchor",
            calibration=None,
            applied_threshold=None,
            labels=singleton,
            candidates=0,
            seed=seed,
            vocabulary_size=len(vectorizer.vocabulary_),
        )
    )
    for method, calibration in selected.items():
        alpha = float(calibration["alpha_dense"])
        sparse_floor = float(calibration["sparse_floor"])
        matrix = (
            target_dense_similarity
            if method == "dense_only"
            else target_sparse_similarity
            if method == "structured_tfidf_only"
            else alpha * target_dense_similarity
            + (1.0 - alpha) * target_sparse_similarity
        )
        pairs = _top_k_matrix_pairs(
            target.session_ids,
            matrix,
            target_index,
            top_k=24,
            gate_matrix=target_sparse_similarity if sparse_floor else None,
            gate_threshold=sparse_floor,
        )
        labels = labels_from_scores(
            target.session_ids,
            pairs,
            threshold=float(calibration["threshold"]),
            prefix=f"{source.name}-to-{target.name}-{method}",
        )
        rows.append(
            _row(
                source=source,
                target=target,
                method=method,
                calibration=calibration,
                applied_threshold=float(calibration["threshold"]),
                labels=labels,
                candidates=len(pairs),
                seed=seed,
                vocabulary_size=len(vectorizer.vocabulary_),
            )
        )
        if method == "carp_content_project" and pairs:
            aligned_threshold = float(
                np.quantile(
                    np.asarray(list(pairs.values()), dtype=np.float32),
                    float(calibration["threshold_quantile"]),
                )
            )
            aligned_labels = labels_from_scores(
                target.session_ids,
                pairs,
                threshold=aligned_threshold,
                prefix=f"{source.name}-to-{target.name}-quantile",
            )
            rows.append(
                _row(
                    source=source,
                    target=target,
                    method="carp_content_quantile_transfer",
                    calibration=calibration,
                    applied_threshold=aligned_threshold,
                    labels=aligned_labels,
                    candidates=len(pairs),
                    seed=seed,
                    vocabulary_size=len(vectorizer.vocabulary_),
                )
            )
    mutual_alpha = float(selected_mutual["alpha_dense"])
    mutual_floor = float(selected_mutual["sparse_floor"])
    mutual_matrix = (
        mutual_alpha * target_dense_similarity
        + (1.0 - mutual_alpha) * target_sparse_similarity
    )
    mutual_pairs = _mutual_margin_pairs(
        target.session_ids,
        mutual_matrix,
        gate_matrix=target_sparse_similarity,
        gate_threshold=mutual_floor,
        margin=float(selected_mutual["mutual_margin"]),
    )
    mutual_labels = labels_from_scores(
        target.session_ids,
        mutual_pairs,
        threshold=0.5,
        prefix=f"{source.name}-to-{target.name}-mutual",
    )
    rows.append(
        _row(
            source=source,
            target=target,
            method="carp_content_mutual_transfer",
            calibration=selected_mutual,
            applied_threshold=None,
            labels=mutual_labels,
            candidates=len(mutual_pairs),
            seed=seed,
            vocabulary_size=len(vectorizer.vocabulary_),
        )
    )
    return rows


def _mutual_margin_pairs(
    session_ids: list[str],
    matrix: np.ndarray,
    *,
    gate_matrix: np.ndarray,
    gate_threshold: float,
    margin: float,
) -> dict[tuple[str, str], float]:
    choices: dict[int, int] = {}
    for index in range(len(session_ids)):
        eligible = np.flatnonzero(gate_matrix[index] >= gate_threshold)
        eligible = eligible[eligible != index]
        if not len(eligible):
            continue
        scores = matrix[index, eligible]
        order = np.argsort(scores)
        best_position = int(order[-1])
        best = int(eligible[best_position])
        best_score = float(scores[best_position])
        second_score = float(scores[int(order[-2])]) if len(order) > 1 else -1.0
        if best_score - second_score >= margin:
            choices[index] = best
    pairs = {}
    for left, right in choices.items():
        if choices.get(right) != left or left >= right:
            continue
        pairs[(session_ids[left], session_ids[right])] = 1.0
    return pairs


def _row(
    *,
    source: ScaffoldData,
    target: ScaffoldData,
    method: str,
    calibration: dict[str, Any] | None,
    applied_threshold: float | None,
    labels: dict[str, str],
    candidates: int,
    seed: int,
    vocabulary_size: int,
) -> dict[str, Any]:
    metrics = clustering_metrics(labels, target.truth)
    ci = _entity_bootstrap_ci(labels, target.truth, seed=seed)
    return {
        "source_scaffold": source.name,
        "target_scaffold": target.name,
        "method": method,
        "source_calibration_sessions": ""
        if calibration is None
        else calibration["calibration_sessions"],
        "target_sessions": len(target.session_ids),
        "target_projects": len(set(target.truth.values())),
        "alpha_dense": "" if calibration is None else calibration["alpha_dense"],
        "sparse_floor": "" if calibration is None else calibration["sparse_floor"],
        "threshold": "" if calibration is None else calibration["threshold"],
        "mutual_margin": ""
        if calibration is None
        else calibration.get("mutual_margin", ""),
        "source_threshold_quantile": ""
        if calibration is None
        else calibration["threshold_quantile"],
        "applied_target_threshold": ""
        if applied_threshold is None
        else applied_threshold,
        "source_calibration_f1": ""
        if calibration is None
        else calibration["calibration_f1"],
        "precision": metrics["pairwise_precision"],
        "recall": metrics["pairwise_recall"],
        "f1": metrics["pairwise_f1"],
        "f1_ci_low": ci["f1_ci_low"],
        "f1_ci_high": ci["f1_ci_high"],
        "purity": metrics["purity"],
        "split_rate": metrics["split_rate"],
        "merge_rate": metrics["merge_rate"],
        "candidates": candidates,
        "source_tfidf_vocabulary": vocabulary_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openhands-dir", type=Path, default=DEFAULT_OPENHANDS_DIR)
    parser.add_argument("--sweagent-dir", type=Path, default=DEFAULT_SWEAGENT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    print(
        summarize_cross_scaffold_transfer(
            openhands_dir=args.openhands_dir,
            sweagent_dir=args.sweagent_dir,
            output_dir=args.output_dir,
            seed=args.seed,
        )
    )


if __name__ == "__main__":
    main()
