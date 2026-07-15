from __future__ import annotations

import unittest

from agent_privacy.evaluation.clustering import cross_workflow_clustering_metrics


class CrossWorkflowClusteringMetricsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.truth = {rid: "project_a" for rid in ("a1", "a2", "b1", "b2")}
        self.workflows = {"a1": "workflow_a", "a2": "workflow_a", "b1": "workflow_b", "b2": "workflow_b"}

    def test_perfect_cross_workflow_linkage(self) -> None:
        pred = {rid: "cluster_a" for rid in self.truth}

        metrics = cross_workflow_clustering_metrics(pred, self.truth, self.workflows)

        self.assertEqual(metrics["cross_workflow_f1"], 1.0)
        self.assertEqual(metrics["cross_workflow_true_positive_pairs"], 4.0)
        self.assertEqual(metrics["cross_workflow_truth_positive_pairs"], 4.0)

    def test_within_workflow_only_clusters_do_not_receive_credit(self) -> None:
        pred = {"a1": "cluster_a", "a2": "cluster_a", "b1": "cluster_b", "b2": "cluster_b"}

        metrics = cross_workflow_clustering_metrics(pred, self.truth, self.workflows)

        self.assertEqual(metrics["cross_workflow_precision"], 0.0)
        self.assertEqual(metrics["cross_workflow_recall"], 0.0)
        self.assertEqual(metrics["cross_workflow_f1"], 0.0)
        self.assertEqual(metrics["cross_workflow_predicted_positive_pairs"], 0.0)
        self.assertEqual(metrics["cross_workflow_false_negative_pairs"], 4.0)

    def test_cross_entity_merge_counts_false_positive_pairs(self) -> None:
        truth = {"a": "project_a", "b": "project_b"}
        workflows = {"a": "workflow_a", "b": "workflow_b"}
        pred = {"a": "merged", "b": "merged"}

        metrics = cross_workflow_clustering_metrics(pred, truth, workflows)

        self.assertEqual(metrics["cross_workflow_true_positive_pairs"], 0.0)
        self.assertEqual(metrics["cross_workflow_false_positive_pairs"], 1.0)
        self.assertEqual(metrics["cross_workflow_f1"], 0.0)


if __name__ == "__main__":
    unittest.main()
