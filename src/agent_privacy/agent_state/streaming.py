from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Iterable

from agent_privacy.agent_state.evidence import compare_states
from agent_privacy.agent_state.extract import (
    AgentStateOptions,
    estimate_state_bytes,
    extract_agent_state,
    state_hash_count,
)
from agent_privacy.agent_state.model import (
    AgentRequestState,
    LinkDecision,
    LinkerStats,
    PairEvidence,
)


@dataclass(frozen=True)
class LinkerConfig:
    state_options: AgentStateOptions = field(default_factory=AgentStateOptions)
    max_posting_size: int = 64
    max_candidates_per_request: int = 96
    active_window_seconds: int = 90 * 60
    accept_score: float = 4.2
    min_evidence_families: int = 3
    min_margin: float = 0.35
    max_session_gap_seconds: int = 90 * 60
    retain_debug_states: bool = True
    enabled_evidence: tuple[str, ...] = (
        "state_replay",
        "initial_task",
        "typed_handle",
        "tool_resource",
        "resource_root",
        "ordered_progression",
    )
    enforce_conflicts: bool = True


@dataclass(frozen=True)
class LinkerResult:
    predictions: dict[str, dict[str, str]]
    states: dict[str, AgentRequestState]
    decisions: tuple[LinkDecision, ...]
    stats: dict[str, int | float]


class _DynamicUnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}
        self.size: dict[str, int] = {}

    def add(self, item: str) -> None:
        if item not in self.parent:
            self.parent[item] = item
            self.size[item] = 1

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> int:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return self.size[root_left]
        if self.size[root_left] < self.size[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        self.size[root_left] += self.size.pop(root_right)
        return self.size[root_left]

    def labels(self, prefix: str) -> dict[str, str]:
        roots: dict[str, str] = {}
        labels: dict[str, str] = {}
        for item in self.parent:
            root = self.find(item)
            roots.setdefault(root, f"{prefix}_{len(roots):06d}")
            labels[item] = roots[root]
        return labels


class AgentNativeLinker:
    """One-pass candidate retrieval and conservative hierarchical linkage."""

    def __init__(self, config: LinkerConfig | None = None) -> None:
        self.config = config or LinkerConfig()

    def run(self, rows: Iterable[dict[str, Any]]) -> LinkerResult:
        stats = LinkerStats()
        states: dict[str, AgentRequestState] = {}
        active_states: dict[str, AgentRequestState] = {}
        active_order: deque[str] = deque()
        decisions: list[LinkDecision] = []
        indexes: dict[str, dict[str, deque[str]]] = {
            name: defaultdict(deque)
            for name in (
                "replay",
                "initial",
                "user",
                "project",
                "org",
                "tool",
                "resource",
                "resource_root",
            )
        }
        suppressed: dict[str, set[str]] = defaultdict(set)
        workflow_uf = _DynamicUnionFind()
        user_uf = _DynamicUnionFind()
        project_uf = _DynamicUnionFind()
        org_uf = _DynamicUnionFind()

        for row in rows:
            state = extract_agent_state(row, self.config.state_options)
            request_id = state.request_id
            self._expire(
                state.timestamp_second,
                active_states,
                active_order,
                indexes,
                suppressed,
                stats,
            )
            for uf in (workflow_uf, user_uf, project_uf, org_uf):
                uf.add(request_id)
            candidate_ids = self._candidates(state, indexes, suppressed)
            candidate_ids = {
                candidate_id
                for candidate_id in candidate_ids
                if 0
                <= state.timestamp_second - active_states[candidate_id].timestamp_second
                <= self.config.active_window_seconds
            }
            ranked = sorted(
                (
                    self._filter_evidence(compare_states(active_states[candidate_id], state))
                    for candidate_id in candidate_ids
                ),
                key=lambda evidence: (-evidence.score, evidence.earlier_id),
            )[: self.config.max_candidates_per_request]
            stats.requests_processed += 1
            stats.candidates_considered += len(ranked)
            stats.max_candidates_for_request = max(stats.max_candidates_for_request, len(ranked))
            decision = self._decide(state, ranked)
            decisions.append(decision)
            if decision.disposition == "accept" and decision.predecessor_id:
                predecessor = active_states[decision.predecessor_id]
                size = workflow_uf.union(predecessor.request_id, request_id)
                user_uf.union(predecessor.request_id, request_id)
                project_uf.union(predecessor.request_id, request_id)
                org_uf.union(predecessor.request_id, request_id)
                stats.peak_component_size = max(stats.peak_component_size, size)
                stats.accepted_merges += 1
            elif decision.disposition == "abstain":
                stats.abstained_requests += 1
            else:
                stats.rejected_candidates += 1
                if decision.conflicts:
                    stats.conflict_rejections += 1

            if self.config.retain_debug_states:
                states[request_id] = state
            active_states[request_id] = state
            active_order.append(request_id)
            stats.peak_active_states = max(stats.peak_active_states, len(active_states))
            stats.retained_state_hashes += state_hash_count(state)
            stats.estimated_state_bytes += estimate_state_bytes(state)
            self._add_to_indexes(state, indexes, suppressed, stats)

        if self.config.retain_debug_states:
            self._link_higher_levels(states, workflow_uf, user_uf, project_uf, org_uf)
        predictions = {
            "session": workflow_uf.labels("an_s"),
            "user": user_uf.labels("an_u"),
            "project": project_uf.labels("an_p"),
            "org": org_uf.labels("an_o"),
        }
        return LinkerResult(
            predictions=predictions,
            states=states,
            decisions=tuple(decisions),
            stats=stats.to_dict(),
        )

    def _filter_evidence(self, evidence: PairEvidence) -> PairEvidence:
        enabled = set(self.config.enabled_evidence)
        families = tuple(
            family for family in evidence.evidence_families if family in enabled
        )
        score = 0.0
        if "state_replay" in enabled:
            score += 3.0 * evidence.replay_containment
        if "initial_task" in enabled:
            score += 1.5 * evidence.initial_task_containment
        if "typed_handle" in enabled and "typed_handle" in evidence.evidence_families:
            score += min(evidence.handle_overlap, 2) * 0.8
        if "tool_resource" in enabled:
            score += min(evidence.tool_observation_overlap + evidence.resource_overlap, 2) * 0.5
        if "resource_root" in enabled and "resource_root" in evidence.evidence_families:
            score += 3.0
        if "ordered_progression" in enabled and "ordered_progression" in evidence.evidence_families:
            score += 0.8
        return PairEvidence(
            earlier_id=evidence.earlier_id,
            later_id=evidence.later_id,
            replay_containment=evidence.replay_containment,
            initial_task_containment=evidence.initial_task_containment,
            handle_overlap=evidence.handle_overlap,
            tool_observation_overlap=evidence.tool_observation_overlap,
            resource_overlap=evidence.resource_overlap,
            time_delta_seconds=evidence.time_delta_seconds,
            length_growth=evidence.length_growth,
            evidence_families=families,
            conflicts=evidence.conflicts if self.config.enforce_conflicts else (),
            score=score,
        )

    def _expire(
        self,
        timestamp_second: int,
        active_states: dict[str, AgentRequestState],
        active_order: deque[str],
        indexes: dict[str, dict[str, deque[str]]],
        suppressed: dict[str, set[str]],
        stats: LinkerStats,
    ) -> None:
        while active_order:
            request_id = active_order[0]
            state = active_states[request_id]
            if timestamp_second - state.timestamp_second <= self.config.active_window_seconds:
                return
            active_order.popleft()
            del active_states[request_id]
            for index_name, values in self._index_values(state).items():
                for value in values:
                    if value in suppressed[index_name]:
                        continue
                    posting = indexes[index_name].get(value)
                    if posting is None:
                        continue
                    try:
                        posting.remove(request_id)
                    except ValueError:
                        continue
                    stats.active_postings -= 1
                    stats.expired_postings += 1
                    if not posting:
                        del indexes[index_name][value]

    def _candidates(
        self,
        state: AgentRequestState,
        indexes: dict[str, dict[str, deque[str]]],
        suppressed: dict[str, set[str]],
    ) -> set[str]:
        candidates: set[str] = set()
        keyed_values = self._index_values(state)
        for index_name, values in keyed_values.items():
            for value in values:
                if value in suppressed[index_name]:
                    continue
                candidates.update(indexes[index_name].get(value, ()))
                if len(candidates) >= self.config.max_candidates_per_request:
                    return set(sorted(candidates)[: self.config.max_candidates_per_request])
        return candidates

    def _add_to_indexes(
        self,
        state: AgentRequestState,
        indexes: dict[str, dict[str, deque[str]]],
        suppressed: dict[str, set[str]],
        stats: LinkerStats,
    ) -> None:
        for index_name, values in self._index_values(state).items():
            for value in values:
                if value in suppressed[index_name]:
                    continue
                posting = indexes[index_name][value]
                posting.append(state.request_id)
                stats.index_entries_added += 1
                stats.active_postings += 1
                if len(posting) > self.config.max_posting_size:
                    stats.active_postings -= len(posting)
                    stats.expired_postings += len(posting)
                    posting.clear()
                    del indexes[index_name][value]
                    suppressed[index_name].add(value)
                    stats.heavy_hitter_suppressions += 1
                stats.peak_active_postings = max(
                    stats.peak_active_postings, stats.active_postings
                )

    @staticmethod
    def _index_values(state: AgentRequestState) -> dict[str, tuple[str, ...]]:
        return {
            "replay": state.replay_sketch,
            "initial": state.initial_task_sketch,
            "user": state.user_handles,
            "project": state.project_handles,
            "org": state.org_handles,
            "tool": state.tool_observation_sketch,
            "resource": state.resource_fingerprints,
            "resource_root": state.resource_roots,
        }

    def _decide(self, state: AgentRequestState, ranked: list[PairEvidence]) -> LinkDecision:
        if not ranked:
            return LinkDecision(
                request_id=state.request_id,
                predecessor_id=None,
                disposition="abstain",
                score=0.0,
                runner_up_score=0.0,
                margin=0.0,
                evidence_families=(),
                conflicts=(),
                reason="no_candidate",
            )
        best = ranked[0]
        runner_up = ranked[1].score if len(ranked) > 1 else 0.0
        margin = best.score - runner_up
        if best.conflicts:
            disposition = "reject"
            reason = "hard_conflict"
        elif best.time_delta_seconds > self.config.max_session_gap_seconds:
            disposition = "abstain"
            reason = "session_gap_exceeded"
        elif (
            "resource_root" in best.evidence_families
            and "state_replay" not in best.evidence_families
            and (
                "ordered_progression" not in best.evidence_families
                or "tool_resource" not in best.evidence_families
            )
        ):
            disposition = "abstain"
            reason = "resource_root_without_progression"
        elif (
            "resource_root" in best.evidence_families
            and "state_replay" not in best.evidence_families
            and best.resource_overlap < 2
        ):
            disposition = "abstain"
            reason = "weak_resource_continuity"
        elif best.score < self.config.accept_score:
            disposition = "abstain"
            reason = "insufficient_score"
        elif len(best.evidence_families) < self.config.min_evidence_families:
            disposition = "abstain"
            reason = "insufficient_independent_evidence"
        elif margin < self.config.min_margin:
            disposition = "abstain"
            reason = "ambiguous_runner_up"
        else:
            disposition = "accept"
            reason = "risk_gate_passed"
        return LinkDecision(
            request_id=state.request_id,
            predecessor_id=best.earlier_id,
            disposition=disposition,
            score=best.score,
            runner_up_score=runner_up,
            margin=margin,
            evidence_families=best.evidence_families,
            conflicts=best.conflicts,
            reason=reason,
        )

    @staticmethod
    def _link_higher_levels(
        states: dict[str, AgentRequestState],
        workflow_uf: _DynamicUnionFind,
        user_uf: _DynamicUnionFind,
        project_uf: _DynamicUnionFind,
        org_uf: _DynamicUnionFind,
    ) -> None:
        representatives: dict[str, list[str]] = defaultdict(list)
        for request_id in states:
            representatives[workflow_uf.find(request_id)].append(request_id)
        summaries: list[tuple[str, set[str], set[str], set[str]]] = []
        for members in representatives.values():
            summaries.append(
                (
                    members[0],
                    {value for rid in members for value in states[rid].user_handles},
                    {value for rid in members for value in states[rid].project_handles},
                    {value for rid in members for value in states[rid].org_handles},
                )
            )
        AgentNativeLinker._merge_by_unambiguous_handle(summaries, 1, user_uf)
        AgentNativeLinker._merge_by_unambiguous_handle(
            summaries, 2, project_uf, allowed_kinds={"repository", "workspace", "order", "reservation", "booking", "ticket"}
        )
        AgentNativeLinker._merge_by_unambiguous_handle(summaries, 3, org_uf)

    @staticmethod
    def _merge_by_unambiguous_handle(
        summaries: list[tuple[str, set[str], set[str], set[str]]],
        handle_index: int,
        uf: _DynamicUnionFind,
        allowed_kinds: set[str] | None = None,
    ) -> None:
        owners: dict[str, list[str]] = defaultdict(list)
        for summary in summaries:
            representative = summary[0]
            handles = summary[handle_index]
            for handle in handles:
                if allowed_kinds is not None:
                    parts = handle.split(":", 2)
                    if len(parts) < 3 or parts[1] not in allowed_kinds:
                        continue
                owners[handle].append(representative)
        for members in owners.values():
            if len(members) < 2:
                continue
            first = members[0]
            for member in members[1:]:
                uf.union(first, member)
