from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from agent_privacy.attacks.pipeline import run_attacks_from_features
from agent_privacy.data.profile_truth import enrich_profile_truth
from agent_privacy.evaluation.controls import control_predictions, oracle_size_random_labels
from agent_privacy.evaluation.ordering import evaluate_turn_ordering
from agent_privacy.evaluation.profile import evaluate_profiles
from agent_privacy.evaluation.workflows import (
    reconstruct_workflows,
    workflow_reconstruction_summary,
)
from agent_privacy.experiments.feature_ablations import feature_options_for_ablation
from agent_privacy.experiments.summarize_tau_bench_watchlist import (
    build_entity_watchlist,
    score_entity_watchlist,
)
from agent_privacy.experiments.run_semantic_profile import split_request_ids_by_org
from agent_privacy.experiments.profile_bounds import _risk_rows
from agent_privacy.features.extract import extract_request_features
from agent_privacy.io import read_jsonl, write_jsonl
from agent_privacy.profiling.watchlist import (
    build_profile_watchlist,
    score_watchlist,
    summarize_watchlist_scores,
)
from agent_privacy.profiling.rule_profiler import profile_clusters
from agent_privacy.profiling.structured_profiler import profile_clusters_structured
from agent_privacy.profiling.semantic_profiler import (
    SemanticCandidate,
    SemanticOptions,
    encode_request_evidence,
    extract_evidence_spans,
    profile_clusters_semantic,
)


class ExperimentGapsTest(unittest.TestCase):
    def test_feature_ablation_disables_repo_path_and_shingle_signals(self) -> None:
        row = _attack_row(
            "r1",
            "repository=owner/repo workspace=/workspace/owner__repo tests/test_auth.py",
        )

        no_paths = extract_request_features(
            row,
            feature_options_for_ablation(
                methods=["hybrid"],
                fast_features=False,
                feature_ablation="no_paths",
            ),
        )
        no_shingles = extract_request_features(
            row,
            feature_options_for_ablation(
                methods=["hybrid"],
                fast_features=False,
                feature_ablation="no_shingles",
            ),
        )

        self.assertFalse(no_paths.paths)
        self.assertFalse(any(value.startswith("repo_full:") for value in no_paths.identifiers))
        self.assertFalse(no_shingles.shingles)

    def test_ordering_uses_predicted_session_and_timestamp_order(self) -> None:
        rows = [
            _attack_row("r1", "alpha beta gamma delta epsilon", timestamp="2026-01-01T00:00:00Z"),
            _attack_row("r2", "zeta eta theta iota kappa", timestamp="2026-01-01T00:02:00Z"),
            _attack_row("r3", "lambda mu nu xi omicron", timestamp="2026-01-01T00:01:00Z"),
        ]
        truth_rows = [
            _truth_row("r1", workflow_id="wf", turn_id=1),
            _truth_row("r2", workflow_id="wf", turn_id=2),
            _truth_row("r3", workflow_id="wf", turn_id=3),
        ]
        metrics = evaluate_turn_ordering(
            rows,
            {"r1": "pred_s", "r2": "pred_s", "r3": "pred_s"},
            truth_rows,
        )

        self.assertEqual(metrics["adjacent_pairs"], 2)
        self.assertEqual(metrics["ordered_pairs"], 3)
        self.assertLess(metrics["pairwise_order_accuracy"], 1.0)

    def test_context_ordering_uses_containment(self) -> None:
        first = "alpha beta gamma delta epsilon zeta eta theta"
        second = first + " iota kappa lambda mu nu xi"
        third = second + " omicron pi rho sigma"
        rows = [
            _attack_row("r1", first, timestamp="2026-01-01T00:02:00Z"),
            _attack_row("r2", second, timestamp="2026-01-01T00:00:00Z"),
            _attack_row("r3", third, timestamp="2026-01-01T00:01:00Z"),
        ]
        truth_rows = [
            _truth_row("r1", workflow_id="wf", turn_id=1),
            _truth_row("r2", workflow_id="wf", turn_id=2),
            _truth_row("r3", workflow_id="wf", turn_id=3),
        ]
        metrics = evaluate_turn_ordering(
            rows,
            {"r1": "pred_s", "r2": "pred_s", "r3": "pred_s"},
            truth_rows,
        )

        self.assertLess(metrics["pairwise_order_accuracy"], 1.0)
        self.assertEqual(metrics["context_pairwise_order_accuracy"], 1.0)

    def test_profile_metrics_report_evidence_coverage(self) -> None:
        predicted_profiles = {
            "cluster": {
                "request_ids": ["r1"],
                "fields": {"languages": ["python"], "repo_names": ["repo"]},
                "evidence": {"languages": {"python": ["r1"]}, "repo_names": {"repo": []}},
            }
        }
        rows = evaluate_profiles(
            predicted_profiles,
            [
                {
                    "request_id": "r1",
                    "org_id": "owner",
                    "profile_truth": {"languages": ["python"], "repo_names": ["repo"]},
                }
            ],
            {"r1": "cluster"},
        )
        micro = next(row for row in rows if row["field"] == "__micro__")

        self.assertEqual(micro["unsupported_predictions"], 1)
        self.assertEqual(micro["evidenced_values"], 1)
        self.assertEqual(micro["evidence_coverage"], 0.5)

    def test_enrich_profile_truth_from_attack_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(
                root / "attack_view.jsonl",
                [
                    _attack_row(
                        "r1",
                        "Run pytest in /workspace/owner__repo with pyproject.toml",
                    )
                ],
            )
            write_jsonl(
                root / "ground_truth.jsonl",
                [_truth_row("r1", workflow_id="wf", turn_id=1, project_id="owner/repo")],
            )

            summary = enrich_profile_truth(root)
            truth = read_jsonl(root / "ground_truth.jsonl")[0]["profile_truth"]

            self.assertEqual(summary["truth_rows"], 1)
            self.assertIn("repo", truth["repo_names"])
            self.assertIn("python", truth["languages"])
            self.assertIn("pytest", truth["frameworks"])

    def test_feature_ablation_can_change_hybrid_predictions(self) -> None:
        rows = [
            _attack_row("r1", "repository=owner/repo /workspace/owner__repo/a.py"),
            _attack_row("r2", "repository=owner/repo /workspace/owner__repo/b.py"),
        ]
        full_features = {
            row["request_id"]: extract_request_features(
                row,
                feature_options_for_ablation(
                    methods=["hybrid"], fast_features=False, feature_ablation="none"
                ),
            )
            for row in rows
        }
        no_repo_features = {
            row["request_id"]: extract_request_features(
                row,
                feature_options_for_ablation(
                    methods=["hybrid"], fast_features=False, feature_ablation="no_paths"
                ),
            )
            for row in rows
        }

        full = run_attacks_from_features(full_features, methods=["hybrid"])["hybrid"]["project"]
        no_repo = run_attacks_from_features(no_repo_features, methods=["hybrid"])["hybrid"][
            "project"
        ]

        self.assertEqual(full["r1"], full["r2"])
        self.assertNotEqual(no_repo["r1"], no_repo["r2"])

    def test_profiler_repo_names_require_explicit_repo_artifacts(self) -> None:
        rows = [
            _attack_row(
                "r1",
                (
                    "test_api test_core external_services "
                    "repository=owner/real_repo /workspace/owner__real_repo__1.0/app.py "
                    "service=billing-api"
                ),
            ),
            _attack_row("r2", "Target service billing-api and more test_schemapi output"),
        ]

        profile = profile_clusters(rows, {"r1": "cluster", "r2": "cluster"})["cluster"]

        self.assertEqual(profile["fields"]["repo_names"], ["real_repo"])
        self.assertEqual(profile["fields"]["service_names"], ["billing-api"])
        self.assertNotIn("test_api", profile["fields"]["repo_names"])
        self.assertNotIn("external_services", profile["fields"]["service_names"])

    def test_provider_lowcost_links_cache_rare_and_semantic_signals(self) -> None:
        rows = [
            _attack_row(
                "r1",
                "repository=owner/repo /workspace/owner__repo tests/test_auth.py alpha beta gamma",
                timestamp="2026-01-01T00:00:00Z",
                cache_bucket="medium",
            ),
            _attack_row(
                "r2",
                "repository=owner/repo /workspace/owner__repo tests/test_auth.py alpha beta delta",
                timestamp="2026-01-01T00:04:00Z",
                cache_bucket="medium",
            ),
            _attack_row(
                "r3",
                "repository=other/repo /workspace/other__repo tests/test_auth.py alpha beta delta",
                timestamp="2026-01-01T00:05:00Z",
                cache_bucket="low",
            ),
        ]
        features = {row["request_id"]: extract_request_features(row) for row in rows}

        labels = run_attacks_from_features(features, methods=["provider_lowcost"])[
            "provider_lowcost"
        ]

        self.assertEqual(labels["session"]["r1"], labels["session"]["r2"])
        self.assertEqual(labels["project"]["r1"], labels["project"]["r2"])
        self.assertNotEqual(labels["session"]["r1"], labels["session"]["r3"])

    def test_provider_lowcost_links_tau_business_overlay_anchors(self) -> None:
        rows = [
            _attack_row(
                "r1",
                (
                    "Account context: tenant=aurora01-airline; region=iad; "
                    "customer_ref=cust-a123-001001; loyalty_tier=gold; "
                    "account_cache=tenant:airline:aurora01-airline:acct:a123\n"
                    "Case context: case_id=case-booking-10001; "
                    "queue=aurora01-airline-booking-1-queue; service_line=booking; "
                    "internal_domain=aurora01-airline-booking-1.airline.ops.internal"
                ),
                timestamp="2026-01-01T00:00:00Z",
                cache_bucket="tenant:airline:aurora01-airline",
            ),
            _attack_row(
                "r2",
                (
                    "Account context: tenant=aurora01-airline; region=iad; "
                    "customer_ref=cust-a123-001001; loyalty_tier=gold; "
                    "account_cache=tenant:airline:aurora01-airline:acct:a123\n"
                    "Case context: case_id=case-booking-10002; "
                    "queue=aurora01-airline-booking-1-queue; service_line=booking; "
                    "internal_domain=aurora01-airline-booking-1.airline.ops.internal"
                ),
                timestamp="2026-01-01T00:04:00Z",
                cache_bucket="tenant:airline:aurora01-airline",
            ),
            _attack_row(
                "r3",
                (
                    "Account context: tenant=beacon02-retail; region=syd; "
                    "customer_ref=cust-b456-002001; loyalty_tier=silver; "
                    "account_cache=tenant:retail:beacon02-retail:acct:b456\n"
                    "Case context: case_id=case-refund-20001; "
                    "queue=beacon02-retail-refund-1-queue; service_line=refund; "
                    "internal_domain=beacon02-retail-refund-1.retail.ops.internal"
                ),
                timestamp="2026-01-01T00:05:00Z",
                cache_bucket="tenant:retail:beacon02-retail",
            ),
        ]
        features = {row["request_id"]: extract_request_features(row) for row in rows}

        self.assertIn("business_user:customer_ref:cust-a123-001001", features["r1"].identifiers)
        self.assertIn(
            "business_project:queue:aurora01-airline-booking-1-queue",
            features["r1"].identifiers,
        )
        self.assertIn(
            "business_project:internal_domain:aurora01-airline-booking-1.airline.ops.internal",
            features["r1"].identifiers,
        )
        self.assertIn("business_org:tenant:aurora01-airline", features["r1"].identifiers)
        self.assertNotIn("business_user:loyalty_tier:gold", features["r1"].identifiers)
        self.assertNotIn("business_project:service_line:booking", features["r1"].identifiers)
        self.assertNotIn("business_org:region:iad", features["r1"].identifiers)

        labels = run_attacks_from_features(features, methods=["provider_lowcost"])[
            "provider_lowcost"
        ]

        self.assertEqual(labels["user"]["r1"], labels["user"]["r2"])
        self.assertEqual(labels["project"]["r1"], labels["project"]["r2"])
        self.assertEqual(labels["org"]["r1"], labels["org"]["r2"])
        self.assertNotEqual(labels["user"]["r1"], labels["user"]["r3"])
        self.assertNotEqual(labels["project"]["r1"], labels["project"]["r3"])
        self.assertNotEqual(labels["org"]["r1"], labels["org"]["r3"])

    def test_stable_content_handles_parse_tool_json_and_explicit_ids(self) -> None:
        tool_row = _attack_row(
            "r1",
            (
                '{"reservation_id":"M05KNL","user_id":"aarav_ahmed_6699",'
                '"flight_number":"HAT023","status":"available"}'
            ),
            cache_bucket="a",
        )
        tool_row["messages"][0]["role"] = "tool"
        natural_row = _attack_row(
            "r2",
            "My user ID is aarav_ahmed_6699 and reservation ID: M05KNL.",
            cache_bucket="b",
        )
        features = {
            row["request_id"]: extract_request_features(row)
            for row in (tool_row, natural_row)
        }

        for request_id in ("r1", "r2"):
            self.assertIn(
                "stable_user:user:aarav_ahmed_6699",
                features[request_id].identifiers,
            )
            self.assertIn(
                "stable_project:reservation:m05knl",
                features[request_id].identifiers,
            )
        self.assertIn(
            "stable_context:flight:hat023",
            features["r1"].identifiers,
        )
        self.assertFalse(
            any("available" in value for value in features["r1"].identifiers)
        )

        labels = run_attacks_from_features(features, methods=["provider_lowcost"])[
            "provider_lowcost"
        ]
        self.assertEqual(labels["user"]["r1"], labels["user"]["r2"])
        self.assertEqual(labels["project"]["r1"], labels["project"]["r2"])

    def test_stable_handle_is_rejected_when_it_bridges_typed_projects(self) -> None:
        rows = [
            _attack_row(
                "r1",
                "queue=alpha-project-queue reservation ID: SHARED1",
                cache_bucket="a",
            ),
            _attack_row(
                "r2",
                "queue=beta-project-queue reservation ID: SHARED1",
                cache_bucket="b",
            ),
        ]
        features = {row["request_id"]: extract_request_features(row) for row in rows}

        labels = run_attacks_from_features(features, methods=["provider_lowcost"])[
            "provider_lowcost"
        ]

        self.assertNotEqual(labels["project"]["r1"], labels["project"]["r2"])

    def test_provider_lowcost_percolates_business_entities_across_cache_buckets(self) -> None:
        common = (
            "tenant=aurora01-airline customer_ref=cust-a123-001001 "
            "account_cache=tenant:airline:aurora01-airline:acct:a123 "
            "queue=aurora01-airline-booking-1-queue "
            "internal_domain=aurora01-airline-booking-1.airline.ops.internal "
            "order-aurora01-airline-booking-1"
        )
        rows = [
            _attack_row("r1", common, cache_bucket="tenant:airline:shared"),
            _attack_row("r2", common, cache_bucket="tenant:airline:aurora01-airline"),
        ]
        features = {row["request_id"]: extract_request_features(row) for row in rows}

        self.assertIn(
            "business_project:order:aurora01-airline-booking-1",
            features["r1"].identifiers,
        )
        labels = run_attacks_from_features(features, methods=["provider_lowcost"])[
            "provider_lowcost"
        ]

        self.assertEqual(labels["user"]["r1"], labels["user"]["r2"])
        self.assertEqual(labels["project"]["r1"], labels["project"]["r2"])
        self.assertEqual(labels["org"]["r1"], labels["org"]["r2"])

    def test_provider_lowcost_rejects_ambiguous_account_cache_alias(self) -> None:
        rows = [
            _attack_row(
                "r1",
                "customer_ref=cust-a123-001001 account_cache=tenant:airline:aurora01-airline:acct:a123",
                cache_bucket="one",
            ),
            _attack_row(
                "r2",
                "customer_ref=cust-a123-001002 account_cache=tenant:airline:aurora01-airline:acct:a123",
                cache_bucket="two",
            ),
        ]
        features = {row["request_id"]: extract_request_features(row) for row in rows}
        labels = run_attacks_from_features(features, methods=["provider_lowcost"])[
            "provider_lowcost"
        ]

        self.assertNotEqual(labels["user"]["r1"], labels["user"]["r2"])

    def test_structured_profiler_aggregates_manifest_and_entity_evidence(self) -> None:
        rows = [
            _attack_row(
                "r1",
                "repository=owner/api /workspace/owner__api/app.py pyproject.toml pytest ",
            ),
            _attack_row("r2", "Run pytest for target service api in app.py"),
        ]

        profile = profile_clusters_structured(
            rows,
            {"r1": "cluster", "r2": "cluster"},
        )["cluster"]

        self.assertIn("python", profile["fields"]["languages"])
        self.assertIn("pytest", profile["fields"]["frameworks"])
        self.assertIn("api", profile["fields"]["repo_names"])
        self.assertIn("api", profile["fields"]["service_names"])
        self.assertIn("manifest", profile["confidence"]["languages"]["python"]["sources"])

    def test_tau_entity_watchlist_relinks_future_cross_cache_request(self) -> None:
        train_rows = [
            _attack_row(
                "r1",
                "customer_ref=cust-a123-001001 tenant=aurora01-airline",
                cache_bucket="train",
            )
        ]
        train_truth = [
            {
                "request_id": "r1",
                "user_id": "user-a",
                "project_id": "project-a",
                "org_id": "org-a",
            }
        ]
        watchlist = build_entity_watchlist(
            train_rows,
            train_truth,
            {"r1": "cluster-a"},
            level="user",
            truth_field="user_id",
        )
        test_rows = [
            _attack_row(
                "r2",
                "customer_ref=cust-a123-001001",
                cache_bucket="future-shared",
            )
        ]
        metrics = score_entity_watchlist(
            watchlist,
            test_rows,
            [{"request_id": "r2", "user_id": "user-a"}],
            level="user",
            truth_field="user_id",
        )

        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["recall"], 1.0)

    def test_semantic_profiler_extracts_and_aggregates_evidence(self) -> None:
        rows = [
            _attack_row("r1", "Python traceback in app.py while running the test suite"),
            _attack_row("r2", "The pyproject dependencies configure the Python runtime"),
        ]
        spans = extract_evidence_spans(rows[0], max_spans=4)
        self.assertTrue(any("Python traceback" in span.text for span in spans))
        request_candidates = {
            "r1": [
                SemanticCandidate(
                    field="languages",
                    value="python",
                    score=0.72,
                    span="Python traceback in app.py",
                    role="user",
                    source_type="error",
                )
            ],
            "r2": [
                SemanticCandidate(
                    field="languages",
                    value="python",
                    score=0.69,
                    span="pyproject dependencies configure the Python runtime",
                    role="user",
                    source_type="manifest",
                )
            ],
        }

        profile = profile_clusters_semantic(
            rows,
            {"r1": "cluster", "r2": "cluster"},
            request_candidates,
            threshold=0.60,
            min_request_support=2,
        )["cluster"]

        self.assertIn("python", profile["fields"]["languages"])
        self.assertIn(
            "semantic_embedding",
            profile["confidence"]["languages"]["python"]["sources"],
        )

    def test_semantic_encoder_filters_negated_candidate(self) -> None:
        rows = [_attack_row("r1", "We do not use Python in this Java service test")]

        def encoder(texts: list[str]) -> np.ndarray:
            vectors = []
            for text in texts:
                lower = text.lower()
                if "python" in lower:
                    vector = np.array([1.0, 0.0], dtype=np.float32)
                elif "java" in lower:
                    vector = np.array([0.0, 1.0], dtype=np.float32)
                else:
                    vector = np.array([0.5, 0.5], dtype=np.float32)
                vectors.append(vector / np.linalg.norm(vector))
            return np.vstack(vectors)

        candidates, stats = encode_request_evidence(
            rows,
            options=SemanticOptions(candidate_floor=0.20, top_k_per_field=2),
            encoder=encoder,
        )

        language_values = {
            candidate.value for candidate in candidates.get("r1", []) if candidate.field == "languages"
        }
        self.assertNotIn("python", language_values)
        self.assertGreater(stats["spans"], 0)

    def test_semantic_profile_split_is_org_disjoint(self) -> None:
        truth_rows = [
            {"request_id": f"r{index}", "org_id": f"org-{index // 2}"}
            for index in range(20)
        ]
        calibration, test = split_request_ids_by_org(
            truth_rows,
            calibration_fraction=0.20,
            seed=7,
        )
        org_by_request = {row["request_id"]: row["org_id"] for row in truth_rows}

        self.assertFalse(calibration & test)
        self.assertFalse(
            {org_by_request[request_id] for request_id in calibration}
            & {org_by_request[request_id] for request_id in test}
        )

    def test_reconstructed_workflows_report_purity_and_order(self) -> None:
        first = "alpha beta gamma delta epsilon"
        second = first + " zeta eta theta"
        rows = [
            _attack_row("r2", second, timestamp="2026-01-01T00:02:00Z"),
            _attack_row("r1", first, timestamp="2026-01-01T00:00:00Z"),
        ]
        truth_rows = [
            _truth_row("r1", workflow_id="wf", turn_id=1),
            _truth_row("r2", workflow_id="wf", turn_id=2),
        ]

        workflows = reconstruct_workflows(rows, {"r1": "cluster", "r2": "cluster"}, truth_rows)
        summary = workflow_reconstruction_summary(workflows)

        self.assertEqual(workflows[0]["request_ids"], ["r1", "r2"])
        self.assertEqual(workflows[0]["purity"], 1.0)
        self.assertEqual(summary[0]["mean_pairwise_order_accuracy"], 1.0)

    def test_profile_watchlist_scores_follow_on_request_retrieval(self) -> None:
        profiles = {
            "cluster": {
                "request_ids": ["r1"],
                "fields": {"repo_names": ["repo"], "package_managers": ["poetry"]},
                "evidence": {
                    "repo_names": {"repo": ["r1"]},
                    "package_managers": {"poetry": ["r1"]},
                },
            }
        }
        rows = [
            _attack_row("r1", "repository=owner/repo uses poetry"),
            _attack_row("r2", "later request for repo still uses poetry"),
            _attack_row("r3", "unrelated request"),
        ]
        truth_rows = [
            _truth_row("r1", workflow_id="wf1", turn_id=1, project_id="owner/repo"),
            _truth_row("r2", workflow_id="wf2", turn_id=1, project_id="owner/repo"),
            _truth_row("r3", workflow_id="wf3", turn_id=1, project_id="other/repo"),
        ]
        watchlist = build_profile_watchlist(profiles)

        scores = score_watchlist(
            watchlist,
            rows,
            truth_rows,
            {"r1": "cluster"},
            truth_level="project",
        )
        summary = summarize_watchlist_scores(scores)

        self.assertEqual(scores[0]["true_positive"], 2)
        self.assertEqual(scores[0]["precision"], 1.0)
        self.assertGreater(summary[0]["mean_recall"], 0.0)

    def test_oracle_size_random_preserves_truth_cluster_sizes(self) -> None:
        truth = {
            "r1": "a",
            "r2": "a",
            "r3": "b",
            "r4": "b",
            "r5": "b",
        }

        labels = oracle_size_random_labels(
            sorted(truth),
            truth,
            rng=__import__("random").Random(7),
        )
        sizes = sorted(
            len([rid for rid, label in labels.items() if label == cluster])
            for cluster in set(labels.values())
        )

        self.assertEqual(sizes, [2, 3])

    def test_control_predictions_emit_requested_levels(self) -> None:
        truth_rows = [
            _truth_row("r1", workflow_id="w1", turn_id=1),
            _truth_row("r2", workflow_id="w1", turn_id=2),
            _truth_row("r3", workflow_id="w2", turn_id=1, project_id="owner/other"),
        ]

        predictions = control_predictions(
            request_ids=["r1", "r2", "r3"],
            truth_rows=truth_rows,
            methods=["random", "oracle_size_random"],
            levels=["session", "project"],
        )

        self.assertEqual(set(predictions), {"random", "oracle_size_random"})
        self.assertEqual(set(predictions["random"]), {"session", "project"})
        self.assertEqual(set(predictions["oracle_size_random"]["session"]), {"r1", "r2", "r3"})

    def test_profile_risk_rows_aggregate_field_counts(self) -> None:
        rows = _risk_rows(
            [
                {
                    "source": "truth_cluster_upper_bound",
                    "field": "languages",
                    "tp": 2,
                    "fp": 1,
                    "fn": 1,
                    "predicted_values": 3,
                    "evidenced_values": 3,
                },
                {
                    "source": "truth_cluster_upper_bound",
                    "field": "repo_names",
                    "tp": 1,
                    "fp": 0,
                    "fn": 1,
                    "predicted_values": 1,
                    "evidenced_values": 1,
                },
            ]
        )
        l1 = next(row for row in rows if row["risk_level"] == "L1_technical")
        l2 = next(row for row in rows if row["risk_level"] == "L2_project")

        self.assertAlmostEqual(l1["precision"], 2 / 3)
        self.assertEqual(l2["f1"], 2 / 3)


def _attack_row(
    request_id: str,
    content: str,
    *,
    timestamp: str = "2026-01-01T00:00:00Z",
    cache_bucket: str | None = None,
) -> dict:
    return {
        "request_id": request_id,
        "timestamp": timestamp,
        "model": "test",
        "messages": [{"role": "user", "content": content}],
        "tool_schemas": [{"name": "shell", "parameters": ["cmd"]}],
        "token_count": len(content.split()),
        "cache_bucket": cache_bucket,
    }


def _truth_row(
    request_id: str,
    *,
    workflow_id: str,
    turn_id: int,
    project_id: str = "owner/repo",
) -> dict:
    return {
        "request_id": request_id,
        "org_id": "owner",
        "user_id": None,
        "project_id": project_id,
        "workflow_id": workflow_id,
        "turn_id": turn_id,
        "task_type": "unit",
        "profile_truth": {},
    }


if __name__ == "__main__":
    unittest.main()
