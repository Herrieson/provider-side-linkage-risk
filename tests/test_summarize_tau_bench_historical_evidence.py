from __future__ import annotations

import unittest

from agent_privacy.experiments.summarize_tau_bench_historical_evidence import (
    SemanticThresholds,
    _semantic_labels,
    _split_rows,
)
from agent_privacy.features.extract import RequestFeatures


class TauBenchHistoricalEvidenceTest(unittest.TestCase):
    def test_split_rows_is_deterministic_and_domain_stratified(self) -> None:
        rows = []
        for domain in ("airline", "retail"):
            for workflow_index in range(10):
                workflow = f"{domain}-{workflow_index}"
                rows.append(
                    {
                        "request_id": f"{workflow}-1",
                        "workflow_id": workflow,
                        "org_id": domain,
                    }
                )

        calibration, test = _split_rows(rows, seed=7)
        repeated_calibration, repeated_test = _split_rows(rows, seed=7)

        calibration_workflows = {row["workflow_id"] for row in calibration}
        test_workflows = {row["workflow_id"] for row in test}
        self.assertEqual(calibration, repeated_calibration)
        self.assertEqual(test, repeated_test)
        self.assertFalse(calibration_workflows & test_workflows)
        self.assertEqual(len(calibration_workflows), 4)
        self.assertEqual(
            {row["org_id"] for row in calibration},
            {"airline", "retail"},
        )

    def test_semantic_operating_point_respects_all_thresholds(self) -> None:
        shared_semantic = frozenset({"sem:0:a", "sem:1:b", "sem:2:c"})
        features = {
            "a": _feature(
                "a",
                minute=100,
                semantic=shared_semantic,
                shingles=frozenset({"s1", "s2", "s3"}),
                identifiers=frozenset({"i1", "i2", "i3"}),
            ),
            "b": _feature(
                "b",
                minute=110,
                semantic=shared_semantic,
                shingles=frozenset({"s1", "s2", "s3"}),
                identifiers=frozenset({"i1", "i2", "i3"}),
            ),
            "c": _feature(
                "c",
                minute=200,
                semantic=shared_semantic,
                shingles=frozenset({"s1", "s2", "s3"}),
                identifiers=frozenset({"i1", "i2", "i3"}),
            ),
        }

        predictions = _semantic_labels(
            features,
            SemanticThresholds(
                semantic_overlap=3,
                shingle_jaccard=0.7,
                identifier_overlap=3,
                max_time_gap=30,
            ),
        )["session"]

        self.assertEqual(predictions["a"], predictions["b"])
        self.assertNotEqual(predictions["a"], predictions["c"])


def _feature(
    request_id: str,
    *,
    minute: int,
    semantic: frozenset[str],
    shingles: frozenset[str],
    identifiers: frozenset[str],
) -> RequestFeatures:
    return RequestFeatures(
        request_id=request_id,
        timestamp_minute=minute,
        token_count=100,
        words=frozenset(),
        shingles=shingles,
        identifiers=identifiers,
        paths=frozenset(),
        usernames=frozenset(),
        domains=frozenset(),
        traces=frozenset(),
        cache_bucket="shared",
        semantic_signatures=semantic,
        tool_fingerprint="tool",
        system_fingerprint="system",
    )


if __name__ == "__main__":
    unittest.main()
