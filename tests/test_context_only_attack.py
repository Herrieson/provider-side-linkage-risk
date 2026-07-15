from __future__ import annotations

import unittest

from agent_privacy.attacks.pipeline import run_attacks_from_features
from agent_privacy.experiments.feature_ablations import feature_options_for_ablation
from agent_privacy.features.extract import RequestFeatures


class ContextOnlyAttackTest(unittest.TestCase):
    def test_context_only_enables_shingles(self) -> None:
        options = feature_options_for_ablation(
            methods=["context_only"], fast_features=False, feature_ablation="none"
        )

        self.assertTrue(options.include_shingles)
        self.assertFalse(options.include_semantic_signatures)

    def test_context_only_links_sessions_but_not_entities(self) -> None:
        shared_identifiers = frozenset({"repo_full:owner/repo", "stable-build-id"})
        shared_shingles = frozenset({"a", "b", "c", "d", "e"})
        features = {
            "left": _feature(
                "left", timestamp=100, identifiers=shared_identifiers, shingles=shared_shingles
            ),
            "right": _feature(
                "right", timestamp=120, identifiers=shared_identifiers, shingles=shared_shingles
            ),
        }

        predictions = run_attacks_from_features(features, methods=["context_only"])["context_only"]

        self.assertEqual(predictions["session"]["left"], predictions["session"]["right"])
        self.assertNotEqual(predictions["project"]["left"], predictions["project"]["right"])
        self.assertNotEqual(predictions["org"]["left"], predictions["org"]["right"])


def _feature(
    request_id: str,
    *,
    timestamp: int,
    identifiers: frozenset[str],
    shingles: frozenset[str],
) -> RequestFeatures:
    return RequestFeatures(
        request_id=request_id,
        timestamp_minute=timestamp,
        token_count=100,
        words=frozenset(),
        shingles=shingles,
        identifiers=identifiers,
        paths=frozenset(),
        usernames=frozenset(),
        domains=frozenset(),
        traces=frozenset(),
        cache_bucket="cache_unavailable",
        semantic_signatures=frozenset(),
        tool_fingerprint="tool",
        system_fingerprint="system",
    )


if __name__ == "__main__":
    unittest.main()
