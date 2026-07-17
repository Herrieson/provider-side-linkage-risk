from __future__ import annotations

from agent_privacy.evaluation.clustering import pairwise_confusion_counts


def test_pairwise_confusion_counts() -> None:
    truth = {"a": "x", "b": "x", "c": "y", "d": "y"}
    pred = {"a": "p", "b": "p", "c": "p", "d": "q"}

    counts = pairwise_confusion_counts(pred, truth)

    assert counts == {
        "items": 4,
        "total_pairs": 6,
        "actual_positive_pairs": 2,
        "actual_negative_pairs": 4,
        "predicted_positive_pairs": 3,
        "true_positive_pairs": 1,
        "false_positive_pairs": 2,
        "false_negative_pairs": 1,
        "true_negative_pairs": 2,
    }
