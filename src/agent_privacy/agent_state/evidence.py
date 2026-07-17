from __future__ import annotations

from agent_privacy.agent_state.model import AgentRequestState, PairEvidence


def directed_containment(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    if not left:
        return 0.0
    return len(set(left) & set(right)) / len(left)


def compare_states(earlier: AgentRequestState, later: AgentRequestState) -> PairEvidence:
    replay = directed_containment(earlier.replay_sketch, later.replay_sketch)
    initial = directed_containment(earlier.initial_task_sketch, later.initial_task_sketch)
    user_overlap = _overlap(earlier.user_handles, later.user_handles)
    project_overlap = _overlap(earlier.project_handles, later.project_handles)
    org_overlap = _overlap(earlier.org_handles, later.org_handles)
    context_overlap = _overlap(earlier.context_handles, later.context_handles)
    tool_overlap = _overlap(
        earlier.tool_observation_sketch, later.tool_observation_sketch
    )
    resource_overlap = _overlap(earlier.resource_fingerprints, later.resource_fingerprints)
    resource_root_overlap = _overlap(earlier.resource_roots, later.resource_roots)
    delta = later.timestamp_second - earlier.timestamp_second
    growth = later.message_count - earlier.message_count

    families: list[str] = []
    if replay >= 0.75:
        families.append("state_replay")
    if initial >= 0.6:
        families.append("initial_task")
    if user_overlap + project_overlap + org_overlap > 0:
        families.append("typed_handle")
    if tool_overlap > 0 or resource_overlap > 0:
        families.append("tool_resource")
    if resource_root_overlap > 0:
        families.append("resource_root")
    if 0 <= delta <= 6 * 3600 and (growth > 0 or resource_overlap > 0):
        families.append("ordered_progression")

    conflicts: list[str] = []
    if delta < 0:
        conflicts.append("time_reversal")
    if growth < 0 and replay >= 0.5:
        conflicts.append("context_shrink")
    if _incompatible(earlier.user_handles, later.user_handles):
        conflicts.append("incompatible_user_handles")
    if _incompatible(earlier.org_handles, later.org_handles):
        conflicts.append("incompatible_org_handles")
    if initial < 0.2 and earlier.initial_task_sketch and later.initial_task_sketch:
        conflicts.append("competing_initial_roots")

    score = (
        3.0 * replay
        + 1.5 * initial
        + min(user_overlap + project_overlap + org_overlap, 2) * 0.8
        + min(tool_overlap + resource_overlap, 2) * 0.5
        + min(resource_root_overlap, 1) * 3.0
        + (0.8 if "ordered_progression" in families else 0.0)
    )
    return PairEvidence(
        earlier_id=earlier.request_id,
        later_id=later.request_id,
        replay_containment=replay,
        initial_task_containment=initial,
        handle_overlap=user_overlap + project_overlap + org_overlap + context_overlap,
        tool_observation_overlap=tool_overlap,
        resource_overlap=resource_overlap,
        time_delta_seconds=delta,
        length_growth=growth,
        evidence_families=tuple(families),
        conflicts=tuple(conflicts),
        score=score,
    )


def _overlap(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    return len(set(left) & set(right))


def _incompatible(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    return bool(left and right and not set(left).intersection(right))
