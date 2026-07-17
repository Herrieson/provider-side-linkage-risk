from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from agent_privacy.agent_state.model import AgentRequestState
from agent_privacy.features.extract import extract_stable_content_handles


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_./:@-]{2,}")
ERROR_RE = re.compile(r"\b(error|exception|failed|failure|traceback|timeout|denied)\b", re.I)
RESOURCE_RE = re.compile(
    r"(?:/[^\s'\"]+|\b(?:https?://|s3://|gs://)[^\s'\"]+|"
    r"\b(?:order|reservation|booking|case|ticket|product|flight|repo(?:sitory)?)"
    r"[_:=/-][A-Za-z0-9_.:/@-]+)",
    re.I,
)
WORKSPACE_ROOT_RE = re.compile(r"/workspace/([A-Za-z0-9_.-]+)", re.I)
REPOSITORY_FIELD_RE = re.compile(
    r"\brepository=([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b", re.I
)


@dataclass(frozen=True)
class AgentStateOptions:
    replay_hashes: int = 64
    initial_task_hashes: int = 24
    recent_context_hashes: int = 32
    tool_observation_hashes: int = 24
    max_tool_names: int = 24
    max_tool_argument_keys: int = 48
    max_actions: int = 12
    max_errors: int = 12
    max_resources: int = 32
    max_handles_per_level: int = 32
    recent_messages: int = 4


def extract_agent_state(
    row: dict[str, Any], options: AgentStateOptions | None = None
) -> AgentRequestState:
    options = options or AgentStateOptions()
    messages = row.get("messages", [])
    role_counts = Counter(str(message.get("role", "")) for message in messages)
    event_hashes = [_event_hash(message) for message in messages]
    first_user = next(
        (str(message.get("content", "")) for message in messages if message.get("role") == "user"),
        "",
    )
    recent = messages[-options.recent_messages :]
    tool_messages = [message for message in messages if message.get("role") == "tool"]
    tool_names = {
        str(message.get("name")) for message in tool_messages if message.get("name")
    }
    schemas = row.get("tool_schemas", [])
    tool_names.update(
        str(schema.get("name"))
        for schema in schemas
        if isinstance(schema, dict) and schema.get("name")
    )
    argument_keys: set[str] = set()
    for schema in schemas:
        if not isinstance(schema, dict):
            continue
        parameters = schema.get("parameters", [])
        if isinstance(parameters, dict):
            argument_keys.update(str(value) for value in parameters)
        elif isinstance(parameters, list):
            argument_keys.update(str(value) for value in parameters)

    actions = {_action_type(name) for name in tool_names}
    actions.discard("")
    all_content = [str(message.get("content", "")) for message in messages]
    errors = {
        _hash(f"{match.group(1).lower()}:{content[-160:]}")
        for content in all_content
        for match in ERROR_RE.finditer(content)
    }
    resources = {
        _hash(match.group(0).lower())
        for content in all_content
        for match in RESOURCE_RE.finditer(content)
    }
    resource_roots = {
        f"workspace:{match.group(1).lower()}"
        for content in all_content
        for match in WORKSPACE_ROOT_RE.finditer(content)
    }
    resource_roots.update(
        f"repository:{match.group(1).lower()}"
        for content in all_content
        for match in REPOSITORY_FIELD_RE.finditer(content)
    )
    handles = _split_handles(extract_stable_content_handles(row))
    systems = [str(m.get("content", "")) for m in messages if m.get("role") == "system"]
    return AgentRequestState(
        request_id=str(row["request_id"]),
        timestamp_second=_timestamp_second(str(row["timestamp"])),
        token_count=int(row.get("token_count", 0)),
        message_count=len(messages),
        content_chars=sum(len(content) for content in all_content),
        role_counts=tuple(sorted(role_counts.items())),
        replay_sketch=_bottom_k(event_hashes, options.replay_hashes),
        initial_task_sketch=_text_sketch(first_user, options.initial_task_hashes),
        recent_context_sketch=_bottom_k(
            (_event_hash(message) for message in recent), options.recent_context_hashes
        ),
        tool_observation_sketch=_bottom_k(
            (_event_hash(message) for message in tool_messages),
            options.tool_observation_hashes,
        ),
        tool_names=tuple(sorted(tool_names)[: options.max_tool_names]),
        tool_argument_keys=tuple(sorted(argument_keys)[: options.max_tool_argument_keys]),
        action_types=tuple(sorted(actions)[: options.max_actions]),
        error_fingerprints=tuple(sorted(errors)[: options.max_errors]),
        resource_fingerprints=tuple(sorted(resources)[: options.max_resources]),
        resource_roots=tuple(sorted(resource_roots)[: options.max_resources]),
        user_handles=tuple(sorted(handles["user"])[: options.max_handles_per_level]),
        project_handles=tuple(sorted(handles["project"])[: options.max_handles_per_level]),
        org_handles=tuple(sorted(handles["org"])[: options.max_handles_per_level]),
        context_handles=tuple(sorted(handles["context"])[: options.max_handles_per_level]),
        system_fingerprint=_hash("\n".join(systems)) if systems else "",
        tool_schema_fingerprint=_hash(json.dumps(schemas, sort_keys=True)),
        cache_bucket=str(row.get("cache_bucket") or ""),
    )


def state_hash_count(state: AgentRequestState) -> int:
    return sum(
        len(values)
        for values in (
            state.replay_sketch,
            state.initial_task_sketch,
            state.recent_context_sketch,
            state.tool_observation_sketch,
            state.error_fingerprints,
            state.resource_fingerprints,
            state.resource_roots,
            state.user_handles,
            state.project_handles,
            state.org_handles,
            state.context_handles,
        )
    )


def estimate_state_bytes(state: AgentRequestState) -> int:
    strings: Iterable[str] = (
        *state.replay_sketch,
        *state.initial_task_sketch,
        *state.recent_context_sketch,
        *state.tool_observation_sketch,
        *state.tool_names,
        *state.tool_argument_keys,
        *state.action_types,
        *state.error_fingerprints,
        *state.resource_fingerprints,
        *state.resource_roots,
        *state.user_handles,
        *state.project_handles,
        *state.org_handles,
        *state.context_handles,
        state.system_fingerprint,
        state.tool_schema_fingerprint,
        state.cache_bucket,
    )
    return 160 + sum(49 + len(value) for value in strings)


def _event_hash(message: dict[str, Any]) -> str:
    normalized = {
        "role": str(message.get("role", "")),
        "name": str(message.get("name", "")),
        "content": " ".join(str(message.get("content", "")).split()),
    }
    return _hash(json.dumps(normalized, sort_keys=True))


def _text_sketch(text: str, cap: int) -> tuple[str, ...]:
    tokens = [token.lower() for token in TOKEN_RE.findall(text)]
    features = tokens if len(tokens) < 3 else [" ".join(tokens[i : i + 3]) for i in range(len(tokens) - 2)]
    return _bottom_k((_hash(feature) for feature in features), cap)


def _bottom_k(values: Iterable[str], cap: int) -> tuple[str, ...]:
    return tuple(sorted(set(values))[:cap])


def _split_handles(handles: Iterable[str]) -> dict[str, set[str]]:
    result = {"user": set(), "project": set(), "org": set(), "context": set()}
    for handle in handles:
        prefix = handle.split(":", 1)[0]
        level = prefix.removeprefix("stable_")
        if level in result:
            result[level].add(handle)
    return result


def _action_type(tool_name: str) -> str:
    lower = tool_name.lower()
    for action, markers in {
        "read": ("get", "read", "list", "show", "inspect", "check", "search", "find"),
        "write": ("create", "update", "set", "issue", "cancel", "delete", "write", "patch"),
        "execute": ("run", "exec", "test", "build", "deploy"),
    }.items():
        if any(marker in lower for marker in markers):
            return action
    return "other" if lower else ""


def _timestamp_second(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def _hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]
