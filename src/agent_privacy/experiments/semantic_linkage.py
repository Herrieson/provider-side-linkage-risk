from __future__ import annotations

from collections.abc import Callable
import time
from typing import Any

import numpy as np

from agent_privacy.attacks.cluster import UnionFind


DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def encode_documents(
    documents: dict[str, str],
    *,
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 64,
    encoder: Callable[[list[str]], np.ndarray] | None = None,
) -> tuple[list[str], np.ndarray]:
    request_ids = sorted(documents)
    texts = [documents[request_id] for request_id in request_ids]
    unique_texts = list(dict.fromkeys(texts))
    if encoder is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name, local_files_only=True)

        def encoder(values: list[str]) -> np.ndarray:
            return np.asarray(
                model.encode(
                    values,
                    batch_size=batch_size,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                ),
                dtype=np.float32,
            )

    unique_vectors = np.asarray(encoder(unique_texts), dtype=np.float32)
    if unique_vectors.ndim != 2 or unique_vectors.shape[0] != len(unique_texts):
        raise ValueError("encoder must return one vector per unique document")
    vector_by_text = {text: unique_vectors[index] for index, text in enumerate(unique_texts)}
    vectors = np.asarray([vector_by_text[text] for text in texts], dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / np.maximum(norms, 1e-12)
    return request_ids, vectors


def top_k_cosine_pairs(
    request_ids: list[str],
    vectors: np.ndarray,
    *,
    top_k: int,
) -> dict[tuple[str, str], float]:
    if len(request_ids) != len(vectors):
        raise ValueError("request IDs and vectors must have equal length")
    if len(request_ids) < 2 or top_k <= 0:
        return {}
    similarities = vectors @ vectors.T
    np.fill_diagonal(similarities, -np.inf)
    pairs: dict[tuple[str, str], float] = {}
    k = min(top_k, len(request_ids) - 1)
    for index, request_id in enumerate(request_ids):
        neighbors = np.argpartition(similarities[index], -k)[-k:]
        for neighbor in neighbors:
            score = float(similarities[index, neighbor])
            left, right = sorted((request_id, request_ids[int(neighbor)]))
            pairs[(left, right)] = max(score, pairs.get((left, right), -1.0))
    return pairs


def hnsw_cosine_pairs(
    request_ids: list[str],
    vectors: np.ndarray,
    *,
    top_k: int,
    ef_search: int,
    ef_construction: int = 200,
    max_connections: int = 16,
    seed: int = 7,
) -> tuple[dict[tuple[str, str], float], dict[str, float | int]]:
    if len(request_ids) != len(vectors):
        raise ValueError("request IDs and vectors must have equal length")
    if len(request_ids) < 2 or top_k <= 0:
        return {}, {"build_seconds": 0.0, "query_seconds": 0.0, "index_bytes": 0}
    import hnswlib

    dimension = int(vectors.shape[1])
    index = hnswlib.Index(space="cosine", dim=dimension)
    build_start = time.perf_counter()
    index.init_index(
        max_elements=len(request_ids),
        ef_construction=ef_construction,
        M=max_connections,
        random_seed=seed,
    )
    item_indexes = np.arange(len(request_ids))
    index.add_items(vectors, item_indexes, num_threads=1)
    build_seconds = time.perf_counter() - build_start
    index.set_ef(max(ef_search, top_k + 1))
    query_start = time.perf_counter()
    neighbors, distances = index.knn_query(
        vectors,
        k=min(top_k + 1, len(request_ids)),
        num_threads=1,
    )
    query_seconds = time.perf_counter() - query_start
    pairs: dict[tuple[str, str], float] = {}
    for row_index, request_id in enumerate(request_ids):
        kept = 0
        for neighbor, distance in zip(neighbors[row_index], distances[row_index], strict=True):
            neighbor = int(neighbor)
            if neighbor == row_index:
                continue
            left, right = sorted((request_id, request_ids[neighbor]))
            score = 1.0 - float(distance)
            pairs[(left, right)] = max(score, pairs.get((left, right), -1.0))
            kept += 1
            if kept >= top_k:
                break
    return pairs, {
        "build_seconds": build_seconds,
        "query_seconds": query_seconds,
        "index_bytes": int(index.index_file_size()),
        "ef_search": ef_search,
        "ef_construction": ef_construction,
        "max_connections": max_connections,
        "top_k": top_k,
    }


def labels_from_scores(
    request_ids: list[str],
    pair_scores: dict[tuple[str, str], float],
    *,
    threshold: float,
    prefix: str,
) -> dict[str, str]:
    union_find = UnionFind(request_ids)
    for (left, right), score in pair_scores.items():
        if score >= threshold:
            union_find.union(left, right)
    return union_find.labels(prefix)


def exact_anchor_pairs(
    anchors: dict[str, set[str]],
    *,
    max_bucket_size: int,
) -> dict[tuple[str, str], set[str]]:
    inverted: dict[str, list[str]] = {}
    for request_id, values in anchors.items():
        for value in values:
            inverted.setdefault(value, []).append(request_id)
    pairs: dict[tuple[str, str], set[str]] = {}
    for anchor, members in inverted.items():
        unique_members = sorted(set(members))
        if not 1 < len(unique_members) <= max_bucket_size:
            continue
        for left_index, left in enumerate(unique_members):
            for right in unique_members[left_index + 1 :]:
                pairs.setdefault((left, right), set()).add(anchor)
    return pairs


def write_markdown(path: Any, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0])
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
