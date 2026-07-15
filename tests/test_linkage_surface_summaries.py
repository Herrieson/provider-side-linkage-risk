from __future__ import annotations

import unittest

import numpy as np

from agent_privacy.attacks.pipeline import run_provider_lowcost_from_features_with_stats
from agent_privacy.evaluation.clustering import clustering_metrics
from agent_privacy.experiments.summarize_open_swe_candidate_diagnostics import (
    _bottom_k_shingle_sketch_baseline,
)
from agent_privacy.experiments.summarize_carp_scale import (
    _context_candidate_recall,
    _synthetic_features,
)
from agent_privacy.experiments.summarize_open_swe_direct_exposure import _level_exposure
from agent_privacy.experiments.summarize_open_swe_main_session import (
    _exact_message_nesting_labels,
)
from agent_privacy.experiments.summarize_open_swe_cross_scaffold_transfer import (
    _mutual_margin_pairs,
)
from agent_privacy.experiments.summarize_open_swe_strict_removal import _strict_sanitize
from agent_privacy.experiments.summarize_tau_bench_anchor_robustness import (
    _retain_occurrences,
    _rotate_later_anchors,
)
from agent_privacy.experiments.semantic_linkage import (
    exact_anchor_pairs,
    hnsw_cosine_pairs,
    labels_from_scores,
    top_k_cosine_pairs,
)
from agent_privacy.experiments.summarize_tau_bench_natural_watchlist import (
    _assignment_scores,
    _base_task_disjoint_split,
    _calibrate_semantic_threshold,
    _identity_masked_semantic_document,
    _workflow_anchors,
)
from agent_privacy.experiments.summarize_tau_bench_temporal_stress import (
    _intent_hash_labels,
    _rephrase_intent,
)
from agent_privacy.experiments.summarize_stable_handle_audit import _family_row
from agent_privacy.features.extract import RequestFeatures


class LinkageSurfaceSummaryTest(unittest.TestCase):
    def test_direct_exposure_reports_exact_request_and_workflow_recovery(self) -> None:
        truth_rows = [
            {
                "request_id": "a1",
                "workflow_id": "a",
                "project_id": "owner/repo",
            },
            {
                "request_id": "a2",
                "workflow_id": "a",
                "project_id": "owner/repo",
            },
        ]
        anchors = {
            "a1": {"repo_full:owner/repo"},
            "a2": {"repo_full:owner/repo"},
        }

        row = _level_exposure(
            truth_rows=truth_rows,
            anchors=anchors,
            level="project",
            truth_field="project_id",
            prefix="repo_full:",
        )

        self.assertEqual(row["request_exact_recoverability"], 1.0)
        self.assertEqual(row["workflow_all_turn_recoverability"], 1.0)

    def test_exact_message_nesting_links_prefix_requests_only(self) -> None:
        rows = [
            {"request_id": "a", "messages": [_message("first")]},
            {"request_id": "b", "messages": [_message("first"), _message("second")]},
            {"request_id": "c", "messages": [_message("different")]},
        ]

        labels = _exact_message_nesting_labels(rows)

        self.assertEqual(labels["a"], labels["b"])
        self.assertNotEqual(labels["a"], labels["c"])

    def test_strict_sanitizer_removes_repository_path_and_domain(self) -> None:
        row = {
            "messages": [
                _message(
                    "repository=owner/repo /workspace/owner__repo__1.0 api.team.internal"
                )
            ]
        }

        sanitized = _strict_sanitize(row)["messages"][0]["content"]

        self.assertNotIn("owner/repo", sanitized)
        self.assertNotIn("owner__repo", sanitized)
        self.assertNotIn("api.team.internal", sanitized)

    def test_anchor_retention_and_rotation_are_deterministic(self) -> None:
        anchors = {"r1": {"business_user:customer_ref:c1", "business_user:account_cache:a1"}}

        self.assertEqual(_retain_occurrences(anchors, 0.0, 7), {"r1": set()})
        self.assertEqual(_retain_occurrences(anchors, 1.0, 7), anchors)
        rotated = _rotate_later_anchors(anchors, 1.0, 7)
        self.assertTrue(all("rotated" in anchor for anchor in rotated["r1"]))

    def test_bottom_k_shingle_sketch_links_high_containment_pair(self) -> None:
        shared = frozenset(f"{index:016x}" for index in range(40))
        features = {
            "a": _feature("a", shared, 100),
            "b": _feature("b", shared | {"ffffffffffffffff"}, 110),
            "c": _feature("c", frozenset({"z" * 16}), 120),
        }

        _, labels = _bottom_k_shingle_sketch_baseline(features)

        self.assertEqual(labels["a"], labels["b"])
        self.assertNotEqual(labels["a"], labels["c"])

    def test_semantic_top_k_and_exact_anchor_pairs_are_bounded(self) -> None:
        request_ids = ["a", "b", "c"]
        vectors = np.asarray([[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]], dtype=np.float32)
        pairs = top_k_cosine_pairs(request_ids, vectors, top_k=1)
        labels = labels_from_scores(request_ids, pairs, threshold=0.9, prefix="semantic")
        anchors = exact_anchor_pairs(
            {"a": {"order:1"}, "b": {"order:1"}, "c": {"order:1"}},
            max_bucket_size=2,
        )

        self.assertEqual(labels["a"], labels["b"])
        self.assertNotEqual(labels["a"], labels["c"])
        self.assertEqual(anchors, {})

    def test_rephrased_intent_breaks_exact_hash_per_request(self) -> None:
        rows = [
            {
                "request_id": "a",
                "messages": [_message("Please cancel reservation 12345")],
                "tool_schemas": [],
            },
            {
                "request_id": "b",
                "messages": [_message("Please cancel reservation 12345")],
                "tool_schemas": [],
            },
        ]

        exact = _intent_hash_labels(rows, rephrase=False)
        rephrased = _intent_hash_labels(rows, rephrase=True)

        self.assertEqual(exact["a"], exact["b"])
        self.assertNotEqual(rephrased["a"], rephrased["b"])
        self.assertIn("booking", _rephrase_intent("cancel reservation", "a"))

    def test_hnsw_returns_high_similarity_neighbor(self) -> None:
        request_ids = ["a", "b", "c"]
        vectors = np.asarray([[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]], dtype=np.float32)

        pairs, stats = hnsw_cosine_pairs(
            request_ids,
            vectors,
            top_k=1,
            ef_search=10,
            ef_construction=20,
            max_connections=4,
        )

        self.assertIn(("a", "b"), pairs)
        self.assertGreater(stats["index_bytes"], 0)

    def test_natural_watchlist_extracts_cross_aliases(self) -> None:
        rows = [
            {
                "messages": [
                    _message(
                        "My name is Mia Garcia and my zip code is 19122. "
                        "mia.garcia@example.com mia_garcia_4516"
                    )
                ]
            }
        ]

        anchors = _workflow_anchors(rows)

        self.assertIn("uid:mia_garcia_4516", anchors)
        self.assertIn("email:mia.garcia@example.com", anchors)
        self.assertIn("namezip:mia:garcia:19122", anchors)

    def test_natural_watchlist_masks_identity_values_from_semantic_document(self) -> None:
        row = {
            "request_id": "a",
            "messages": [
                _message(
                    "My name is Mia Garcia and my zip code is 19122. "
                    "Contact mia.garcia@example.com or use mia_garcia_4516. "
                    "Please cancel my reservation."
                )
            ],
            "tool_schemas": [{"name": "cancel_reservation"}],
        }

        document = _identity_masked_semantic_document(row)

        self.assertNotIn("mia", document)
        self.assertNotIn("garcia", document)
        self.assertNotIn("19122", document)
        self.assertNotIn("mia.garcia@example.com", document)
        self.assertNotIn("mia_garcia_4516", document)
        self.assertIn("cancel", document)
        self.assertIn("reservation", document)

    def test_watchlist_precision_counts_unseen_user_assignments_as_false_positive(self) -> None:
        scores = _assignment_scores(
            later_workflows=["seen", "unseen"],
            eligible={"seen"},
            assignments={"seen": "component", "unseen": "component"},
            users_by_component={"component": {"user-a"}},
            truth_by_workflow={
                "seen": {"user_id": "user-a"},
                "unseen": {"user_id": "user-b"},
            },
            seed=7,
            bootstrap_iterations=20,
        )

        self.assertEqual(scores["precision"], 0.5)
        self.assertEqual(scores["recall"], 1.0)
        self.assertAlmostEqual(scores["f1"], 2 / 3)

    def test_watchlist_semantic_calibration_uses_observed_components(self) -> None:
        workflows = ["a1", "a2", "singleton"]
        components = {"a1": "a", "a2": "a", "singleton": "singleton"}
        vectors = {
            "a1": np.asarray([1.0, 0.0], dtype=np.float32),
            "a2": np.asarray([0.8, 0.6], dtype=np.float32),
            "singleton": np.asarray([0.0, 1.0], dtype=np.float32),
        }

        threshold = _calibrate_semantic_threshold(workflows, components, vectors)

        self.assertEqual(threshold, 0.8)

    def test_watchlist_base_task_split_keeps_trials_together(self) -> None:
        workflows = ["a0", "a1", "b0", "c0", "c1"]
        base_tasks = {
            "a0": "task-a",
            "a1": "task-a",
            "b0": "task-b",
            "c0": "task-c",
            "c1": "task-c",
        }

        early, later = _base_task_disjoint_split(workflows, base_tasks, seed=7)

        self.assertEqual(set(early) | set(later), set(workflows))
        self.assertFalse(set(early) & set(later))
        for task in set(base_tasks.values()):
            members = {workflow for workflow, value in base_tasks.items() if value == task}
            self.assertTrue(members <= set(early) or members <= set(later))

    def test_stable_handle_audit_counts_cross_entity_ambiguity(self) -> None:
        truth = [
            {"request_id": "a", "workflow_id": "wa", "user_id": "u1"},
            {"request_id": "b", "workflow_id": "wb", "user_id": "u2"},
        ]
        row = _family_row(
            dataset="fixture",
            family="identity",
            level="user",
            truth_rows=truth,
            anchors_by_request={"a": {"shared"}, "b": {"shared"}},
            entity_field="user_id",
        )

        self.assertEqual(row["request_coverage"], 1.0)
        self.assertEqual(row["cross_workflow_handle_rate"], 1.0)
        self.assertEqual(row["cross_entity_ambiguity_rate"], 1.0)

    def test_scale_fixture_preserves_all_true_session_candidates(self) -> None:
        features, truth = _synthetic_features(40)

        diagnostics = _context_candidate_recall(features, truth["session"])

        self.assertEqual(diagnostics["truth_pairs"], 60)
        self.assertEqual(diagnostics["candidate_recall"], 1.0)
        self.assertEqual(diagnostics["candidate_precision"], 1.0)

        predictions, stats = run_provider_lowcost_from_features_with_stats(features)
        metrics = clustering_metrics(predictions["session"], truth["session"])
        self.assertEqual(metrics["pairwise_f1"], 1.0)
        self.assertEqual(stats["candidate_pairs_considered"] / len(features), 11.0)

    def test_mutual_margin_rejects_one_sided_neighbor(self) -> None:
        session_ids = ["a", "b", "c"]
        matrix = np.asarray(
            [[0.0, 0.90, 0.80], [0.90, 0.0, 0.20], [0.80, 0.20, 0.0]],
            dtype=np.float32,
        )
        gate = np.ones_like(matrix)

        pairs = _mutual_margin_pairs(
            session_ids,
            matrix,
            gate_matrix=gate,
            gate_threshold=0.0,
            margin=0.05,
        )

        self.assertEqual(pairs, {("a", "b"): 1.0})


def _message(content: str) -> dict[str, str]:
    return {"role": "user", "content": content}


def _feature(request_id: str, shingles: frozenset[str], minute: int) -> RequestFeatures:
    return RequestFeatures(
        request_id=request_id,
        timestamp_minute=minute,
        token_count=100,
        words=frozenset(),
        shingles=shingles,
        identifiers=frozenset(),
        paths=frozenset(),
        usernames=frozenset(),
        domains=frozenset(),
        traces=frozenset(),
        cache_bucket="cache",
        semantic_signatures=frozenset(),
        tool_fingerprint="tool",
        system_fingerprint="system",
    )


if __name__ == "__main__":
    unittest.main()
