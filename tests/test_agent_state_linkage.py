from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from agent_privacy.agent_state.evidence import compare_states, directed_containment
from agent_privacy.agent_state.extract import AgentStateOptions, extract_agent_state
from agent_privacy.agent_state.model import AgentRequestState
from agent_privacy.agent_state.streaming import AgentNativeLinker, LinkerConfig
from agent_privacy.evaluation.clustering import clustering_metrics, truth_labels
from agent_privacy.io import read_jsonl


SMOKE = Path("examples/tool_agent_smoke/dataset")


def test_agent_state_is_bounded_and_contains_no_raw_text() -> None:
    row = _smoke_rows()[1]
    options = AgentStateOptions(
        replay_hashes=2,
        initial_task_hashes=2,
        recent_context_hashes=2,
        tool_observation_hashes=2,
        max_handles_per_level=2,
    )
    state = extract_agent_state(row, options)
    assert len(state.replay_sketch) <= 2
    assert len(state.initial_task_sketch) <= 2
    assert len(state.recent_context_sketch) <= 2
    assert len(state.tool_observation_sketch) <= 2
    serialized = str(state.to_dict()).lower()
    assert "please refund" not in serialized
    assert "ground_truth" not in serialized
    assert "provenance" not in serialized
    assert {field.name for field in fields(AgentRequestState)} == set(state.to_dict())


def test_directed_replay_separates_true_smoke_extensions() -> None:
    states = [extract_agent_state(row) for row in _smoke_rows()]
    true_pairs = [(0, 1), (2, 3), (4, 5)]
    for earlier, later in true_pairs:
        assert directed_containment(
            states[earlier].replay_sketch, states[later].replay_sketch
        ) == 1.0
        evidence = compare_states(states[earlier], states[later])
        assert "state_replay" in evidence.evidence_families
        assert "ordered_progression" in evidence.evidence_families
        assert not evidence.conflicts
    for earlier, later in [(0, 3), (2, 5), (0, 5)]:
        assert directed_containment(
            states[earlier].replay_sketch, states[later].replay_sketch
        ) < 0.75


def test_shared_schema_is_not_sufficient_and_strong_handles_conflict() -> None:
    rows = _smoke_rows()
    refund = extract_agent_state(rows[0])
    exchange = extract_agent_state(rows[2])
    evidence = compare_states(refund, exchange)
    assert refund.cache_bucket == exchange.cache_bucket
    assert evidence.score < LinkerConfig().accept_score or evidence.conflicts
    assert "incompatible_user_handles" in evidence.conflicts
    assert "competing_initial_roots" in evidence.conflicts


def test_agent_native_linker_passes_smoke_workflow_gate() -> None:
    result = AgentNativeLinker().run(iter(_smoke_rows()))
    truth = read_jsonl(SMOKE / "ground_truth.jsonl")
    session_metrics = clustering_metrics(
        result.predictions["session"], truth_labels(truth, "session")
    )
    assert session_metrics["pairwise_f1"] == 1.0
    assert session_metrics["merge_rate"] == 0.0
    assert result.stats["max_candidates_for_request"] <= LinkerConfig().max_candidates_per_request
    assert sum(d.disposition == "accept" for d in result.decisions) == 3
    assert sum(d.disposition == "abstain" for d in result.decisions) == 3


def test_posting_and_candidate_caps_hold_under_heavy_hitters() -> None:
    base = _smoke_rows()[0]
    rows = []
    for index in range(30):
        row = dict(base)
        row["request_id"] = f"repeated_{index:03d}"
        row["timestamp"] = f"2026-02-01T09:{index:02d}:10Z"
        rows.append(row)
    config = LinkerConfig(max_posting_size=4, max_candidates_per_request=5)
    result = AgentNativeLinker(config).run(iter(rows))
    assert result.stats["max_candidates_for_request"] <= 5
    assert result.stats["heavy_hitter_suppressions"] > 0
    assert result.stats["requests_processed"] == 30


def test_active_states_and_postings_expire_with_time_window() -> None:
    base = _smoke_rows()[0]
    rows = []
    for index, minute in enumerate((0, 1, 120, 121)):
        row = dict(base)
        row["request_id"] = f"window_{index}"
        row["timestamp"] = f"2026-02-01T{9 + minute // 60:02d}:{minute % 60:02d}:10Z"
        rows.append(row)
    config = LinkerConfig(active_window_seconds=60 * 60, retain_debug_states=False)
    result = AgentNativeLinker(config).run(iter(rows))
    assert not result.states
    assert result.stats["peak_active_states"] == 2
    assert result.stats["expired_postings"] > 0


def _smoke_rows() -> list[dict[str, object]]:
    return read_jsonl(SMOKE / "attack_view.jsonl")
