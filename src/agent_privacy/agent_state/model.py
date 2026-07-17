from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


LinkLevel = Literal["session", "user", "project", "org"]
Disposition = Literal["accept", "reject", "abstain"]


@dataclass(frozen=True)
class AgentRequestState:
    """Fixed-cap provider-visible state; raw message text is deliberately absent."""

    request_id: str
    timestamp_second: int
    token_count: int
    message_count: int
    content_chars: int
    role_counts: tuple[tuple[str, int], ...]
    replay_sketch: tuple[str, ...]
    initial_task_sketch: tuple[str, ...]
    recent_context_sketch: tuple[str, ...]
    tool_observation_sketch: tuple[str, ...]
    tool_names: tuple[str, ...]
    tool_argument_keys: tuple[str, ...]
    action_types: tuple[str, ...]
    error_fingerprints: tuple[str, ...]
    resource_fingerprints: tuple[str, ...]
    resource_roots: tuple[str, ...]
    user_handles: tuple[str, ...]
    project_handles: tuple[str, ...]
    org_handles: tuple[str, ...]
    context_handles: tuple[str, ...]
    system_fingerprint: str
    tool_schema_fingerprint: str
    cache_bucket: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PairEvidence:
    earlier_id: str
    later_id: str
    replay_containment: float
    initial_task_containment: float
    handle_overlap: int
    tool_observation_overlap: int
    resource_overlap: int
    time_delta_seconds: int
    length_growth: int
    evidence_families: tuple[str, ...]
    conflicts: tuple[str, ...]
    score: float


@dataclass(frozen=True)
class LinkDecision:
    request_id: str
    predecessor_id: str | None
    disposition: Disposition
    score: float
    runner_up_score: float
    margin: float
    evidence_families: tuple[str, ...]
    conflicts: tuple[str, ...]
    reason: str


@dataclass
class LinkerStats:
    requests_processed: int = 0
    candidates_considered: int = 0
    max_candidates_for_request: int = 0
    accepted_merges: int = 0
    rejected_candidates: int = 0
    abstained_requests: int = 0
    conflict_rejections: int = 0
    index_entries_added: int = 0
    active_postings: int = 0
    peak_active_postings: int = 0
    heavy_hitter_suppressions: int = 0
    expired_postings: int = 0
    retained_state_hashes: int = 0
    peak_component_size: int = 1
    estimated_state_bytes: int = 0
    peak_active_states: int = 0

    def to_dict(self) -> dict[str, int | float]:
        values: dict[str, int | float] = asdict(self)
        values["candidates_per_request"] = (
            self.candidates_considered / self.requests_processed
            if self.requests_processed
            else 0.0
        )
        values["estimated_bytes_per_request"] = (
            self.estimated_state_bytes / self.requests_processed
            if self.requests_processed
            else 0.0
        )
        return values
