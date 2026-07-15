from __future__ import annotations

import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Iterator

from agent_privacy.attacks.cluster import UnionFind, candidate_pairs, connect_by_bucket, inverted_index
from agent_privacy.features.extract import (
    FeatureOptions,
    RequestFeatures,
    extract_business_identifiers,
    extract_features,
    extract_request_features,
    jaccard,
    overlap_count,
)
from agent_privacy.io import iter_jsonl


PredictionSet = dict[str, dict[str, str]]
EdgeDiagnostics = list[dict[str, Any]]
LOWCOST_MAX_PAIRS_PER_REQUEST = 400
LOWCOST_SHINGLE_BUCKET_SIZE = 35
LOWCOST_SEMANTIC_BUCKET_SIZE = 20


def run_attacks(rows: list[dict[str, Any]], methods: list[str] | None = None) -> dict[str, PredictionSet]:
    features = extract_features(rows)
    return run_attacks_from_features(features, methods=methods)


def run_attacks_from_features(
    features: dict[str, RequestFeatures], methods: list[str] | None = None
) -> dict[str, PredictionSet]:
    selected = methods or ["temporal", "rare", "prefix", "tool", "hybrid"]
    attacks = {
        "temporal": _temporal,
        "rare": _rare,
        "prefix": _prefix,
        "context_only": _context_only,
        "tool": _tool,
        "hybrid": _hybrid,
        "provider_lowcost": _provider_lowcost,
    }
    return {method: attacks[method](features) for method in selected}


def run_provider_lowcost_from_jsonl(
    path: Path,
    *,
    options: FeatureOptions,
    request_ids: set[str] | None = None,
) -> tuple[PredictionSet, dict[str, Any]]:
    """Run the provider-lowcost attack by cache partition without materializing all features."""

    selected_ids: list[str] = []
    cache_buckets: dict[str, int] = defaultdict(int)
    business_identifiers: dict[str, frozenset[str]] = {}
    cache_scan_start = time.perf_counter()
    for row in iter_jsonl(path):
        request_id = row.get("request_id")
        if request_ids is not None and request_id not in request_ids:
            continue
        selected_ids.append(str(request_id))
        cache_buckets[_row_cache_bucket(row)] += 1
        anchors = extract_business_identifiers(row)
        if anchors:
            business_identifiers[str(request_id)] = anchors
    cache_scan_seconds = time.perf_counter() - cache_scan_start

    session_uf = UnionFind(selected_ids)
    user_uf = UnionFind(selected_ids)
    project_uf = UnionFind(selected_ids)
    org_uf = UnionFind(selected_ids)
    bucket_stats: list[dict[str, Any]] = []
    counters: dict[str, int] = defaultdict(int)
    feature_extract_seconds = 0.0
    linkage_seconds = 0.0

    for cache_bucket in sorted(cache_buckets):
        scoped: dict[str, RequestFeatures] = {}
        feature_start = time.perf_counter()
        for row in iter_jsonl(path):
            request_id = row.get("request_id")
            if request_ids is not None and request_id not in request_ids:
                continue
            if _row_cache_bucket(row) != cache_bucket:
                continue
            feature = extract_request_features(row, options=options)
            scoped[feature.request_id] = feature
        bucket_feature_seconds = time.perf_counter() - feature_start
        feature_extract_seconds += bucket_feature_seconds
        linkage_start = time.perf_counter()
        before = dict(counters)
        _connect_lowcost_rare(scoped, session_uf, user_uf, project_uf, org_uf, counters)
        _connect_lowcost_semantic(scoped, session_uf, counters)
        _connect_lowcost_context(scoped, session_uf, counters)
        _connect_lowcost_refine(scoped, session_uf, user_uf, project_uf, org_uf, counters)
        bucket_linkage_seconds = time.perf_counter() - linkage_start
        linkage_seconds += bucket_linkage_seconds
        bucket_stats.append(
            {
                "cache_bucket": cache_bucket,
                "requests": len(scoped),
                "feature_extract_seconds": bucket_feature_seconds,
                "linkage_seconds": bucket_linkage_seconds,
                "candidate_pairs_considered": counters["candidate_pairs_considered"]
                - before.get("candidate_pairs_considered", 0),
                "candidate_pairs_linked": counters["candidate_pairs_linked"]
                - before.get("candidate_pairs_linked", 0),
            }
        )
        scoped.clear()

    _connect_global_business_entities(
        business_identifiers,
        user_uf,
        project_uf,
        org_uf,
        counters,
    )

    predictions = {
        "session": session_uf.labels("plc_s"),
        "user": user_uf.labels("plc_u"),
        "project": project_uf.labels("plc_p"),
        "org": org_uf.labels("plc_o"),
    }
    stats = {
        "requests": len(selected_ids),
        "cache_buckets": bucket_stats,
        "cache_bucket_count": len(bucket_stats),
        "max_cache_bucket_requests": max(cache_buckets.values()) if cache_buckets else 0,
        "cache_scan_seconds": cache_scan_seconds,
        "feature_extract_seconds": feature_extract_seconds,
        "linkage_seconds": linkage_seconds,
        "total_stream_seconds": cache_scan_seconds + feature_extract_seconds + linkage_seconds,
        "candidate_pairs_considered": counters["candidate_pairs_considered"],
        "candidate_pairs_linked": counters["candidate_pairs_linked"],
        "semantic_candidate_pairs": counters["semantic_candidate_pairs"],
        "semantic_links": counters["semantic_links"],
        "context_candidate_pairs": counters["context_candidate_pairs"],
        "context_links": counters["context_links"],
        "refine_candidate_pairs": counters["refine_candidate_pairs"],
        "refine_session_links": counters["refine_session_links"],
        "refine_user_links": counters["refine_user_links"],
        "refine_project_links": counters["refine_project_links"],
        "refine_org_links": counters["refine_org_links"],
        "rare_bucket_links": counters["rare_bucket_links"],
        "global_business_candidate_pairs": counters["global_business_candidate_pairs"],
        "global_business_links": counters["global_business_links"],
        "global_business_ambiguous_anchors": counters[
            "global_business_ambiguous_anchors"
        ],
    }
    return predictions, stats


def hybrid_candidate_edges(rows: list[dict[str, Any]], limit: int | None = None) -> EdgeDiagnostics:
    features = extract_features(rows)
    return hybrid_candidate_edges_from_features(features, limit=limit)


def hybrid_candidate_edges_from_features(
    features: dict[str, RequestFeatures], limit: int | None = None
) -> EdgeDiagnostics:
    return _hybrid_candidate_edges(features, limit=limit)


def _temporal(features: dict[str, RequestFeatures]) -> PredictionSet:
    labels: PredictionSet = {"session": {}, "user": {}, "project": {}, "org": {}}
    for request_id, feat in features.items():
        labels["session"][request_id] = f"t10_{feat.timestamp_minute // 10}"
        labels["user"][request_id] = f"t60_{feat.timestamp_minute // 60}"
        labels["project"][request_id] = f"tday_{feat.timestamp_minute // (60 * 24)}"
        labels["org"][request_id] = f"tday_{feat.timestamp_minute // (60 * 24)}"
    return labels


def _tool(features: dict[str, RequestFeatures]) -> PredictionSet:
    labels: PredictionSet = {"session": {}, "user": {}, "project": {}, "org": {}}
    for request_id, feat in features.items():
        labels["session"][request_id] = f"tool_{feat.tool_fingerprint}_{feat.system_fingerprint}"
        labels["user"][request_id] = f"tool_{feat.tool_fingerprint}_{feat.system_fingerprint}"
        labels["project"][request_id] = f"tool_{feat.tool_fingerprint}_{feat.system_fingerprint}"
        labels["org"][request_id] = f"tool_{feat.tool_fingerprint}_{feat.system_fingerprint}"
    return labels


def _rare(features: dict[str, RequestFeatures]) -> PredictionSet:
    request_ids = list(features)
    id_features = {rid: set(feat.traces) for rid, feat in features.items()}
    buckets = inverted_index(id_features)
    session_uf = connect_by_bucket(request_ids, buckets, max_bucket_size=12)

    user_buckets = inverted_index({rid: set(feat.usernames) for rid, feat in features.items()})
    user_uf = connect_by_bucket(request_ids, user_buckets, max_bucket_size=500)

    project_buckets = inverted_index(
        {
            rid: {value for value in feat.identifiers if value.startswith("repo_full:")}
            for rid, feat in features.items()
        }
    )
    project_uf = connect_by_bucket(request_ids, project_buckets, max_bucket_size=2000)

    org_buckets = inverted_index(
        {
            rid: set(feat.domains)
            | {value for value in feat.identifiers if value.startswith("repo_owner:")}
            | _public_orgish_ids(feat.identifiers)
            for rid, feat in features.items()
        }
    )
    org_uf = connect_by_bucket(request_ids, org_buckets, max_bucket_size=2000)
    return {
        "session": session_uf.labels("rare_s"),
        "user": user_uf.labels("rare_u"),
        "project": project_uf.labels("rare_p"),
        "org": org_uf.labels("rare_o"),
    }


def _prefix(features: dict[str, RequestFeatures]) -> PredictionSet:
    request_ids = list(features)
    shingle_buckets = inverted_index({rid: feat.shingles for rid, feat in features.items()})
    pairs = candidate_pairs(shingle_buckets, max_bucket_size=40)
    session_uf = UnionFind(request_ids)
    user_uf = UnionFind(request_ids)
    project_uf = UnionFind(request_ids)
    org_uf = UnionFind(request_ids)
    for left, right in pairs:
        left_feat = features[left]
        right_feat = features[right]
        score = jaccard(left_feat.shingles, right_feat.shingles)
        if score >= 0.22:
            session_uf.union(left, right)
        if score >= 0.12 and overlap_count(left_feat.identifiers, right_feat.identifiers) >= 3:
            user_uf.union(left, right)
        if (
            score >= 0.08
            and overlap_count(
                _repo_full_ids(left_feat.identifiers), _repo_full_ids(right_feat.identifiers)
            )
            >= 1
        ):
            project_uf.union(left, right)
        if (
            score >= 0.08
            and overlap_count(
                left_feat.domains | left_feat.identifiers, right_feat.domains | right_feat.identifiers
            )
            >= 3
        ):
            org_uf.union(left, right)
    return {
        "session": session_uf.labels("prefix_s"),
        "user": user_uf.labels("prefix_u"),
        "project": project_uf.labels("prefix_p"),
        "org": org_uf.labels("prefix_o"),
    }


def _hybrid(features: dict[str, RequestFeatures]) -> PredictionSet:
    request_ids = list(features)
    session_uf = UnionFind(request_ids)
    user_uf = UnionFind(request_ids)
    project_uf = UnionFind(request_ids)
    org_uf = UnionFind(request_ids)

    for bucket in inverted_index({rid: feat.traces for rid, feat in features.items()}).values():
        _connect_members(session_uf, bucket, max_bucket_size=20)
    for bucket in inverted_index({rid: feat.usernames for rid, feat in features.items()}).values():
        _connect_members(user_uf, bucket, max_bucket_size=400)
    for bucket in inverted_index({rid: feat.domains for rid, feat in features.items()}).values():
        _connect_members(org_uf, bucket, max_bucket_size=1200)
    owner_features = {
        rid: {value for value in feat.identifiers if value.startswith("repo_owner:")}
        for rid, feat in features.items()
    }
    for bucket in inverted_index(owner_features).values():
        _connect_members(org_uf, bucket, max_bucket_size=1200)
    project_features = {
        rid: {value for value in feat.identifiers if value.startswith("repo_full:")}
        for rid, feat in features.items()
    }
    for bucket in inverted_index(project_features).values():
        _connect_members(project_uf, bucket, max_bucket_size=1200)

    buckets = inverted_index(
        {
            rid: _informative_identifiers(feat.identifiers)
            | feat.traces
            | feat.domains
            | feat.usernames
            for rid, feat in features.items()
        }
    )
    for left, right in candidate_pairs(buckets, max_bucket_size=15):
        left_feat = features[left]
        right_feat = features[right]
        scores = _hybrid_pair_scores(left_feat, right_feat)
        links = _hybrid_pair_links(left_feat, right_feat, scores)
        if "session" in links:
            session_uf.union(left, right)
        if "user" in links:
            user_uf.union(left, right)
        if "project" in links:
            project_uf.union(left, right)
        if "org" in links:
            org_uf.union(left, right)

    return {
        "session": session_uf.labels("hybrid_s"),
        "user": user_uf.labels("hybrid_u"),
        "project": project_uf.labels("hybrid_p"),
        "org": org_uf.labels("hybrid_o"),
    }


def _context_only(features: dict[str, RequestFeatures]) -> PredictionSet:
    """Bounded context/identifier baseline without rare, semantic, or entity propagation."""

    request_ids = list(features)
    session_uf = UnionFind(request_ids)
    _connect_lowcost_context(features, session_uf)
    _connect_lowcost_refine(
        features,
        session_uf,
        UnionFind(request_ids),
        UnionFind(request_ids),
        UnionFind(request_ids),
    )
    return {
        "session": session_uf.labels("context_s"),
        "user": UnionFind(request_ids).labels("context_u"),
        "project": UnionFind(request_ids).labels("context_p"),
        "org": UnionFind(request_ids).labels("context_o"),
    }


def _provider_lowcost(features: dict[str, RequestFeatures]) -> PredictionSet:
    """Provider-side low-cost pipeline: cache gating, rare buckets, semantic proxy, refine."""

    predictions, _ = run_provider_lowcost_from_features_with_stats(features)
    return predictions


def run_provider_lowcost_from_features_with_stats(
    features: dict[str, RequestFeatures],
) -> tuple[PredictionSet, dict[str, Any]]:
    """Run CARP over pre-extracted features and retain sparse-stage diagnostics."""

    request_ids = list(features)
    session_uf = UnionFind(request_ids)
    user_uf = UnionFind(request_ids)
    project_uf = UnionFind(request_ids)
    org_uf = UnionFind(request_ids)

    counters: dict[str, int] = defaultdict(int)
    cache_groups = _cache_groups(features)
    linkage_start = time.perf_counter()
    for members in cache_groups.values():
        scoped = {request_id: features[request_id] for request_id in members}
        _connect_lowcost_rare(
            scoped, session_uf, user_uf, project_uf, org_uf, counters
        )
        _connect_lowcost_semantic(scoped, session_uf, counters)
        _connect_lowcost_context(scoped, session_uf, counters)
        _connect_lowcost_refine(
            scoped, session_uf, user_uf, project_uf, org_uf, counters
        )

    _connect_global_business_entities(
        {request_id: feat.identifiers for request_id, feat in features.items()},
        user_uf,
        project_uf,
        org_uf,
        counters,
    )
    linkage_seconds = time.perf_counter() - linkage_start
    predictions = {
        "session": session_uf.labels("plc_s"),
        "user": user_uf.labels("plc_u"),
        "project": project_uf.labels("plc_p"),
        "org": org_uf.labels("plc_o"),
    }
    stats = {
        "requests": len(request_ids),
        "cache_bucket_count": len(cache_groups),
        "max_cache_bucket_requests": max(map(len, cache_groups.values()), default=0),
        "linkage_seconds": linkage_seconds,
        "candidate_pairs_considered": counters["candidate_pairs_considered"],
        "candidate_pairs_linked": counters["candidate_pairs_linked"],
        "rare_bucket_links": counters["rare_bucket_links"],
        "semantic_candidate_pairs": counters["semantic_candidate_pairs"],
        "context_candidate_pairs": counters["context_candidate_pairs"],
        "refine_candidate_pairs": counters["refine_candidate_pairs"],
        "global_business_candidate_pairs": counters["global_business_candidate_pairs"],
        "global_business_links": counters["global_business_links"],
        "global_business_ambiguous_anchors": counters[
            "global_business_ambiguous_anchors"
        ],
    }
    return predictions, stats


def _cache_groups(features: dict[str, RequestFeatures]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for request_id, feat in features.items():
        bucket = feat.cache_bucket or "cache_unavailable"
        groups[bucket].append(request_id)
    return dict(groups)


def _row_cache_bucket(row: dict[str, Any]) -> str:
    return str(row.get("cache_bucket") or "cache_unavailable")


def _connect_lowcost_rare(
    features: dict[str, RequestFeatures],
    session_uf: UnionFind,
    user_uf: UnionFind,
    project_uf: UnionFind,
    org_uf: UnionFind,
    counters: dict[str, int] | None = None,
) -> None:
    rare_session = {
        rid: set(feat.traces)
        for rid, feat in features.items()
    }
    rare_user = {
        rid: set(feat.usernames) | set(feat.traces) | _business_user_ids(feat.identifiers)
        for rid, feat in features.items()
    }
    rare_project = {
        rid: _repo_full_ids(feat.identifiers) | _business_project_ids(feat.identifiers)
        for rid, feat in features.items()
    }
    rare_org = {
        rid: set(feat.domains)
        | {value for value in feat.identifiers if value.startswith("repo_owner:")}
        | _ownerish_path_ids(feat.paths)
        | _business_org_ids(feat.identifiers)
        for rid, feat in features.items()
    }
    for bucket in inverted_index(rare_session).values():
        _connect_members(session_uf, bucket, max_bucket_size=20, counters=counters)
    for bucket in inverted_index(rare_user).values():
        _connect_members(user_uf, bucket, max_bucket_size=80, counters=counters)
    for bucket in inverted_index(rare_project).values():
        _connect_members(project_uf, bucket, max_bucket_size=400, counters=counters)
    for bucket in inverted_index(rare_org).values():
        _connect_members(org_uf, bucket, max_bucket_size=400, counters=counters)


def _connect_lowcost_semantic(
    features: dict[str, RequestFeatures],
    session_uf: UnionFind,
    counters: dict[str, int] | None = None,
) -> None:
    semantic_buckets = (
        inverted_index({rid: feat.semantic_signatures for rid, feat in features.items()})
        if any(feat.semantic_signatures for feat in features.values())
        else {}
    )
    if not semantic_buckets:
        return
    pair_counts: dict[str, int] = defaultdict(int)
    for left, right in _iter_bounded_candidate_pairs(
        semantic_buckets,
        max_bucket_size=LOWCOST_SEMANTIC_BUCKET_SIZE,
        pair_counts=pair_counts,
        max_pairs_per_item=LOWCOST_MAX_PAIRS_PER_REQUEST,
    ):
        _count(counters, "candidate_pairs_considered")
        _count(counters, "semantic_candidate_pairs")
        left_feat = features[left]
        right_feat = features[right]
        sem_overlap = overlap_count(left_feat.semantic_signatures, right_feat.semantic_signatures)
        if sem_overlap < 2:
            continue
        shingle_score = jaccard(left_feat.shingles, right_feat.shingles)
        id_overlap = overlap_count(
            _non_stable_identifiers(left_feat.identifiers),
            _non_stable_identifiers(right_feat.identifiers),
        )
        time_gap = abs(left_feat.timestamp_minute - right_feat.timestamp_minute)
        if shingle_score >= 0.32 and id_overlap >= 3 and time_gap <= 90:
            session_uf.union(left, right)
            _count(counters, "candidate_pairs_linked")
            _count(counters, "semantic_links")


def _connect_lowcost_context(
    features: dict[str, RequestFeatures],
    session_uf: UnionFind,
    counters: dict[str, int] | None = None,
) -> None:
    shingle_buckets = inverted_index({rid: feat.shingles for rid, feat in features.items()})
    pair_counts: dict[str, int] = defaultdict(int)
    for left, right in _iter_bounded_candidate_pairs(
        shingle_buckets,
        max_bucket_size=LOWCOST_SHINGLE_BUCKET_SIZE,
        pair_counts=pair_counts,
        max_pairs_per_item=LOWCOST_MAX_PAIRS_PER_REQUEST,
    ):
        _count(counters, "candidate_pairs_considered")
        _count(counters, "context_candidate_pairs")
        left_feat = features[left]
        right_feat = features[right]
        if _context_carryover_link(left_feat, right_feat):
            session_uf.union(left, right)
            _count(counters, "candidate_pairs_linked")
            _count(counters, "context_links")


def _connect_lowcost_refine(
    features: dict[str, RequestFeatures],
    session_uf: UnionFind,
    user_uf: UnionFind,
    project_uf: UnionFind,
    org_uf: UnionFind,
    counters: dict[str, int] | None = None,
) -> None:
    buckets = inverted_index(
        {
            rid: _informative_identifiers(feat.identifiers)
            | _business_ids(feat.identifiers)
            | feat.traces
            | feat.domains
            for rid, feat in features.items()
        }
    )
    pair_counts: dict[str, int] = defaultdict(int)
    for left, right in _iter_bounded_candidate_pairs(
        buckets,
        max_bucket_size=20,
        pair_counts=pair_counts,
        max_pairs_per_item=LOWCOST_MAX_PAIRS_PER_REQUEST,
    ):
        _count(counters, "candidate_pairs_considered")
        _count(counters, "refine_candidate_pairs")
        left_feat = features[left]
        right_feat = features[right]
        scores = _provider_lowcost_pair_scores(left_feat, right_feat)
        if _lowcost_session_link(scores):
            session_uf.union(left, right)
            _count(counters, "candidate_pairs_linked")
            _count(counters, "refine_session_links")
        if scores["user_score"] >= 1.8 or scores["business_user_overlap"] >= 1:
            user_uf.union(left, right)
            _count(counters, "candidate_pairs_linked")
            _count(counters, "refine_user_links")
        if scores["project_score"] >= 1.0 or scores["business_project_overlap"] >= 1:
            project_uf.union(left, right)
            _count(counters, "candidate_pairs_linked")
            _count(counters, "refine_project_links")
        if scores["org_score"] >= 1.0 or scores["business_org_overlap"] >= 1:
            org_uf.union(left, right)
            _count(counters, "candidate_pairs_linked")
            _count(counters, "refine_org_links")


def _connect_global_business_entities(
    identifiers_by_request: dict[str, frozenset[str]],
    user_uf: UnionFind,
    project_uf: UnionFind,
    org_uf: UnionFind,
    counters: dict[str, int] | None = None,
) -> None:
    """Percolate exact stable content handles across cache buckets.

    Cache partitioning is useful for bounded local comparison, but stable provider-visible
    user/customer, order/reservation, queue/project, and tenant/domain handles can legitimately
    recur in different cache buckets. This pass builds a small entity graph instead of comparing
    request pairs. Ambiguous account-cache aliases are excluded when they co-occur with multiple
    customer references.
    """

    level_specs = (
        ("user", user_uf),
        ("project", project_uf),
        ("org", org_uf),
    )
    for level, request_uf in level_specs:
        anchors_by_request = {
            request_id: _business_entity_anchors(identifiers, level)
            for request_id, identifiers in identifiers_by_request.items()
        }
        anchors_by_request = {
            request_id: anchors for request_id, anchors in anchors_by_request.items() if anchors
        }
        if level == "user":
            ambiguous = _ambiguous_account_cache_anchors(anchors_by_request)
            _count(counters, "global_business_ambiguous_anchors", len(ambiguous))
            if ambiguous:
                anchors_by_request = {
                    request_id: anchors - ambiguous
                    for request_id, anchors in anchors_by_request.items()
                    if anchors - ambiguous
                }
        ambiguous_stable = _ambiguous_stable_anchors(anchors_by_request, level)
        _count(counters, "global_business_ambiguous_anchors", len(ambiguous_stable))
        if ambiguous_stable:
            anchors_by_request = {
                request_id: anchors - ambiguous_stable
                for request_id, anchors in anchors_by_request.items()
                if anchors - ambiguous_stable
            }
        all_anchors = sorted({anchor for anchors in anchors_by_request.values() for anchor in anchors})
        if not all_anchors:
            continue
        anchor_uf = UnionFind(all_anchors)
        for anchors in anchors_by_request.values():
            ordered = sorted(anchors)
            for anchor in ordered[1:]:
                anchor_uf.union(ordered[0], anchor)
        requests_by_component: dict[str, list[str]] = defaultdict(list)
        for request_id, anchors in anchors_by_request.items():
            component = anchor_uf.find(sorted(anchors)[0])
            requests_by_component[component].append(request_id)
        for members in requests_by_component.values():
            if len(members) < 2:
                continue
            _count(counters, "global_business_candidate_pairs", len(members) - 1)
            before = request_uf.find(members[0])
            for request_id in members[1:]:
                if request_uf.find(request_id) != before:
                    request_uf.union(members[0], request_id)
                    _count(counters, "global_business_links")


def _business_entity_anchors(identifiers: frozenset[str], level: str) -> set[str]:
    prefixes = (f"business_{level}:", f"stable_{level}:")
    return {value for value in identifiers if value.startswith(prefixes)}


def _ambiguous_account_cache_anchors(
    anchors_by_request: dict[str, set[str]],
) -> set[str]:
    customers_by_cache: dict[str, set[str]] = defaultdict(set)
    for anchors in anchors_by_request.values():
        customers = {anchor for anchor in anchors if anchor.startswith("business_user:customer_ref:")}
        caches = {anchor for anchor in anchors if anchor.startswith("business_user:account_cache:")}
        for cache in caches:
            customers_by_cache[cache].update(customers)
    return {
        cache
        for cache, customers in customers_by_cache.items()
        if len(customers) != 1
    }


def _ambiguous_stable_anchors(
    anchors_by_request: dict[str, set[str]],
    level: str,
) -> set[str]:
    """Reject generic handles that bridge distinct stronger typed-anchor components."""

    business_prefix = f"business_{level}:"
    stable_prefix = f"stable_{level}:"
    business_anchors = sorted(
        {
            anchor
            for anchors in anchors_by_request.values()
            for anchor in anchors
            if anchor.startswith(business_prefix)
        }
    )
    if not business_anchors:
        return set()
    business_uf = UnionFind(business_anchors)
    for anchors in anchors_by_request.values():
        references = sorted(anchor for anchor in anchors if anchor.startswith(business_prefix))
        for reference in references[1:]:
            business_uf.union(references[0], reference)
    components_by_stable: dict[str, set[str]] = defaultdict(set)
    for anchors in anchors_by_request.values():
        references = [anchor for anchor in anchors if anchor.startswith(business_prefix)]
        stable = [anchor for anchor in anchors if anchor.startswith(stable_prefix)]
        for stable_anchor in stable:
            components_by_stable[stable_anchor].update(
                business_uf.find(reference) for reference in references
            )
    return {
        anchor
        for anchor, components in components_by_stable.items()
        if len(components) > 1
    }


def _provider_lowcost_pair_scores(
    left_feat: RequestFeatures, right_feat: RequestFeatures
) -> dict[str, float]:
    time_gap = abs(left_feat.timestamp_minute - right_feat.timestamp_minute)
    id_overlap = overlap_count(
        _non_stable_identifiers(left_feat.identifiers),
        _non_stable_identifiers(right_feat.identifiers),
    )
    trace_overlap = overlap_count(left_feat.traces, right_feat.traces)
    domain_overlap = overlap_count(left_feat.domains, right_feat.domains)
    user_overlap = overlap_count(left_feat.usernames, right_feat.usernames)
    semantic_overlap = overlap_count(left_feat.semantic_signatures, right_feat.semantic_signatures)
    shingle_score = jaccard(left_feat.shingles, right_feat.shingles)
    same_tool = left_feat.tool_fingerprint == right_feat.tool_fingerprint
    same_system = left_feat.system_fingerprint == right_feat.system_fingerprint
    same_cache = bool(left_feat.cache_bucket) and left_feat.cache_bucket == right_feat.cache_bucket
    repo_overlap = overlap_count(_repo_full_ids(left_feat.identifiers), _repo_full_ids(right_feat.identifiers))
    business_user_overlap = overlap_count(
        _business_user_ids(left_feat.identifiers), _business_user_ids(right_feat.identifiers)
    )
    business_project_overlap = overlap_count(
        _business_project_ids(left_feat.identifiers),
        _business_project_ids(right_feat.identifiers),
    )
    business_org_overlap = overlap_count(
        _business_org_ids(left_feat.identifiers), _business_org_ids(right_feat.identifiers)
    )
    owner_overlap = overlap_count(
        {value for value in left_feat.identifiers if value.startswith("repo_owner:")},
        {value for value in right_feat.identifiers if value.startswith("repo_owner:")},
    )
    session_score = (
        2.0 * min(trace_overlap, 1)
        + 1.0 * min(user_overlap, 1)
        + 0.7 * min(id_overlap, 5) / 5
        + 0.9 * min(semantic_overlap, 3) / 3
        + 1.1 * shingle_score
        + 0.5 * (1 if time_gap <= 180 else 0)
        + 0.3 * (1 if same_cache else 0)
    )
    user_score = (
        2.0 * min(user_overlap, 1)
        + 0.8 * min(id_overlap, 6) / 6
        + 0.5 * min(semantic_overlap, 2) / 2
        + 2.0 * min(business_user_overlap, 1)
        + 0.3 * (1 if time_gap <= 24 * 60 else 0)
    )
    return {
        "session_score": session_score,
        "user_score": user_score,
        "project_score": float(repo_overlap + business_project_overlap),
        "org_score": float(domain_overlap + owner_overlap + business_org_overlap),
        "semantic_overlap": float(semantic_overlap),
        "shingle_score": shingle_score,
        "id_overlap": float(id_overlap),
        "business_user_overlap": float(business_user_overlap),
        "business_project_overlap": float(business_project_overlap),
        "business_org_overlap": float(business_org_overlap),
        "time_gap_minutes": float(time_gap),
        "same_tool": float(1 if same_tool else 0),
        "same_system": float(1 if same_system else 0),
        "same_cache": float(1 if same_cache else 0),
    }


def _lowcost_session_link(scores: dict[str, float]) -> bool:
    return (
        scores["shingle_score"] >= 0.22
        and scores["id_overlap"] >= 2
        and scores["time_gap_minutes"] <= 180
    ) or (
        scores["shingle_score"] >= 0.24
        and scores["semantic_overlap"] >= 2
        and scores["id_overlap"] >= 3
        and scores["time_gap_minutes"] <= 90
    )


def _context_carryover_link(left_feat: RequestFeatures, right_feat: RequestFeatures) -> bool:
    if not left_feat.shingles or not right_feat.shingles:
        return False
    time_gap = abs(left_feat.timestamp_minute - right_feat.timestamp_minute)
    if time_gap > 180:
        return False
    small, large = (
        (left_feat.shingles, right_feat.shingles)
        if len(left_feat.shingles) <= len(right_feat.shingles)
        else (right_feat.shingles, left_feat.shingles)
    )
    overlap = len(small & large)
    if overlap == 0:
        return False
    containment = overlap / len(small)
    jaccard_score = overlap / len(left_feat.shingles | right_feat.shingles)
    id_overlap = overlap_count(
        _non_stable_identifiers(left_feat.identifiers),
        _non_stable_identifiers(right_feat.identifiers),
    )
    repo_overlap = overlap_count(_repo_full_ids(left_feat.identifiers), _repo_full_ids(right_feat.identifiers))
    return (
        containment >= 0.78
        and jaccard_score >= 0.20
        and id_overlap >= 2
        and repo_overlap >= 1
    )


def _hybrid_candidate_edges(
    features: dict[str, RequestFeatures], limit: int | None = None
) -> EdgeDiagnostics:
    diagnostics: EdgeDiagnostics = []
    buckets = inverted_index(
        {
            rid: _informative_identifiers(feat.identifiers)
            | feat.traces
            | feat.domains
            | feat.usernames
            for rid, feat in features.items()
        }
    )
    for left, right in sorted(candidate_pairs(buckets, max_bucket_size=15)):
        left_feat = features[left]
        right_feat = features[right]
        scores = _hybrid_pair_scores(left_feat, right_feat)
        links = _hybrid_pair_links(left_feat, right_feat, scores)
        if not links:
            continue
        diagnostics.append(
            {
                "left": left,
                "right": right,
                "links": links,
                **scores,
                "shared_identifiers": _sample_shared(left_feat.identifiers, right_feat.identifiers),
                "shared_domains": _sample_shared(left_feat.domains, right_feat.domains),
                "shared_traces": _sample_shared(left_feat.traces, right_feat.traces),
                "shared_usernames": _sample_shared(left_feat.usernames, right_feat.usernames),
                "shared_repo_full": _sample_shared(
                    _repo_full_ids(left_feat.identifiers), _repo_full_ids(right_feat.identifiers)
                ),
            }
        )
        if limit is not None and len(diagnostics) >= limit:
            break
    return diagnostics


def _hybrid_pair_scores(
    left_feat: RequestFeatures, right_feat: RequestFeatures
) -> dict[str, float | int | bool]:
    time_gap = abs(left_feat.timestamp_minute - right_feat.timestamp_minute)
    id_overlap = overlap_count(
        _non_stable_identifiers(left_feat.identifiers),
        _non_stable_identifiers(right_feat.identifiers),
    )
    trace_overlap = overlap_count(left_feat.traces, right_feat.traces)
    domain_overlap = overlap_count(left_feat.domains, right_feat.domains)
    user_overlap = overlap_count(left_feat.usernames, right_feat.usernames)
    shingle_score = jaccard(left_feat.shingles, right_feat.shingles)
    length_ratio = _length_ratio(left_feat.token_count, right_feat.token_count)
    same_tool = left_feat.tool_fingerprint == right_feat.tool_fingerprint
    same_system = left_feat.system_fingerprint == right_feat.system_fingerprint
    session_score = (
        3.0 * min(trace_overlap, 1)
        + 1.0 * min(user_overlap, 1)
        + 1.0 * min(id_overlap, 5) / 5
        + 1.2 * shingle_score
        + 0.8 * (1 if time_gap <= 180 else 0)
        + 0.2 * length_ratio
    )
    user_score = (
        2.5 * min(user_overlap, 1)
        + 1.0 * min(id_overlap, 6) / 6
        + 0.5 * shingle_score
        + 0.3 * (1 if time_gap <= 24 * 60 else 0)
    )
    org_score = (
        2.8 * min(domain_overlap, 1)
        + 0.9 * min(id_overlap, 8) / 8
        + 0.2 * (1 if same_tool else 0)
        + 0.2 * (1 if same_system else 0)
        + 0.3 * shingle_score
    )
    return {
        "time_gap_minutes": time_gap,
        "id_overlap": id_overlap,
        "trace_overlap": trace_overlap,
        "domain_overlap": domain_overlap,
        "user_overlap": user_overlap,
        "shingle_score": shingle_score,
        "length_ratio": length_ratio,
        "same_tool": same_tool,
        "same_system": same_system,
        "session_score": session_score,
        "user_score": user_score,
        "org_score": org_score,
    }


def _hybrid_pair_links(
    left_feat: RequestFeatures,
    right_feat: RequestFeatures,
    scores: dict[str, float | int | bool],
) -> list[str]:
    links: list[str] = []
    trace_overlap = int(scores["trace_overlap"])
    user_overlap = int(scores["user_overlap"])
    id_overlap = int(scores["id_overlap"])
    domain_overlap = int(scores["domain_overlap"])
    shingle_score = float(scores["shingle_score"])
    time_gap = int(scores["time_gap_minutes"])
    session_score = float(scores["session_score"])
    user_score = float(scores["user_score"])
    org_score = float(scores["org_score"])
    if trace_overlap or (
        session_score >= 2.55
        and user_overlap
        and id_overlap >= 4
        and shingle_score >= 0.18
        and time_gap <= 90
    ) or (
        shingle_score >= 0.22 and id_overlap >= 2 and time_gap <= 180
    ):
        links.append("session")
    if user_score >= 1.8:
        links.append("user")
    if overlap_count(_repo_full_ids(left_feat.identifiers), _repo_full_ids(right_feat.identifiers)):
        links.append("project")
    if domain_overlap and org_score >= 2.0:
        links.append("org")
    return links


def _public_orgish_ids(identifiers: frozenset[str]) -> set[str]:
    return {value for value in identifiers if "-" in value and not value.startswith("trace-")}


def _repo_full_ids(identifiers: frozenset[str]) -> set[str]:
    return {value for value in identifiers if value.startswith("repo_full:")}


def _informative_identifiers(identifiers: frozenset[str]) -> set[str]:
    stop_prefixes = ("generic-", "synthetic-", "maxfail", "dry-run")
    stop_values = {
        "github_actions",
        "gitlab_ci",
        "self_hosted",
        "read_file",
        "generic-agent-model",
    }
    return {
        value
        for value in identifiers
        if value not in stop_values
        and not value.startswith(stop_prefixes)
        and (
            value.startswith("/home/")
            or value.startswith("/workspace/")
            or value.startswith("trace-")
            or value.startswith("repo_owner:")
            or value.startswith("repo_name:")
            or value.startswith("repo_full:")
            or value.startswith("business_")
            or "." in value
            or any(marker in value for marker in ("service", "api", "core", "engine", "portal", "worker"))
        )
    }


def _business_ids(identifiers: frozenset[str]) -> set[str]:
    return {value for value in identifiers if value.startswith("business_")}


def _non_stable_identifiers(identifiers: frozenset[str]) -> set[str]:
    return {value for value in identifiers if not value.startswith("stable_")}


def _business_user_ids(identifiers: frozenset[str]) -> set[str]:
    return {value for value in identifiers if value.startswith("business_user:")}


def _business_project_ids(identifiers: frozenset[str]) -> set[str]:
    return {value for value in identifiers if value.startswith("business_project:")}


def _business_org_ids(identifiers: frozenset[str]) -> set[str]:
    return {value for value in identifiers if value.startswith("business_org:")}


def _ownerish_path_ids(paths: frozenset[str]) -> set[str]:
    out: set[str] = set()
    for path in paths:
        if "/workspace/" not in path:
            continue
        parts = [part for part in path.split("/") if part]
        if len(parts) < 2:
            continue
        slug = parts[1]
        if "__" in slug:
            out.add("workspace_owner:" + slug.split("__", 1)[0])
    return out


def _bounded_candidate_pairs(
    buckets: dict[str, set[str]],
    *,
    max_bucket_size: int,
    pair_counts: dict[str, int],
    max_pairs_per_item: int,
) -> list[tuple[str, str]]:
    # Keep the returned list bounded by per-item caps; callers process one blocking family at a time.
    return list(
        _iter_bounded_candidate_pairs(
            buckets,
            max_bucket_size=max_bucket_size,
            pair_counts=pair_counts,
            max_pairs_per_item=max_pairs_per_item,
        )
    )


def _iter_bounded_candidate_pairs(
    buckets: dict[str, set[str]],
    *,
    max_bucket_size: int,
    pair_counts: dict[str, int],
    max_pairs_per_item: int,
) -> Iterator[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    ordered_buckets = sorted(
        buckets.values(),
        key=lambda members: (len(members), sorted(members)[0] if members else ""),
    )
    for members in ordered_buckets:
        if not (1 < len(members) <= max_bucket_size):
            continue
        for left, right in combinations(sorted(members), 2):
            if (
                pair_counts[left] >= max_pairs_per_item
                or pair_counts[right] >= max_pairs_per_item
            ):
                continue
            pair = (left, right)
            if pair in seen:
                continue
            seen.add(pair)
            pair_counts[left] += 1
            pair_counts[right] += 1
            yield pair


def _connect_members(
    uf: UnionFind,
    members: set[str],
    max_bucket_size: int,
    counters: dict[str, int] | None = None,
) -> None:
    if not (1 < len(members) <= max_bucket_size):
        return
    iterator = iter(members)
    first = next(iterator)
    for member in iterator:
        uf.union(first, member)
        _count(counters, "rare_bucket_links")


def _length_ratio(left: int, right: int) -> float:
    if left <= 0 or right <= 0:
        return 0.0
    small = min(left, right)
    large = max(left, right)
    return small / large


def group_by_label(labels: dict[str, str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for request_id, label in labels.items():
        grouped[label].append(request_id)
    return dict(grouped)


def _sample_shared(left: set[str] | frozenset[str], right: set[str] | frozenset[str]) -> list[str]:
    return sorted(left & right)[:10]


def _count(counters: dict[str, int] | None, key: str, amount: int = 1) -> None:
    if counters is not None:
        counters[key] += amount
