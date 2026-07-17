from __future__ import annotations

import pytest

from agent_privacy.experiments.summarize_indistinguishability import (
    _run_condition,
    observation_equivalence_pairwise_bound,
)


@pytest.mark.parametrize(
    ("multiplicity", "requests_per_entity", "expected"),
    [(1, 4, 1.0), (2, 4, 0.6), (4, 4, 1 / 3), (9, 4, 6 / 38)],
)
def test_observation_equivalence_f1_ceiling(
    multiplicity: int,
    requests_per_entity: int,
    expected: float,
) -> None:
    bound = observation_equivalence_pairwise_bound(multiplicity, requests_per_entity)
    assert bound["f1"] == pytest.approx(expected)


def test_exchangeable_views_force_carp_to_the_observation_ceiling() -> None:
    row = _run_condition(groups=3, multiplicity=4, turns=4)

    assert row["bayes_entity_accuracy_ceiling"] == pytest.approx(0.25)
    assert row["carp_precision"] == pytest.approx(0.2)
    assert row["carp_recall"] == pytest.approx(1.0)
    assert row["carp_f1"] == pytest.approx(row["expected_pairwise_f1_upper_bound"])
    assert row["carp_clusters"] == 3
