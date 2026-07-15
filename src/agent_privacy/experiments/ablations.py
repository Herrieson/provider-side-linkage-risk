from __future__ import annotations

import copy
import re
from typing import Any

from agent_privacy.features.extract import DOMAIN_RE, PATH_RE, TRACE_RE


REPOSITORY_FIELD_RE = re.compile(r"\brepository=[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b")
REPO_SLUG_RE = re.compile(r"\brepo_slug=[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+\b")
WORKSPACE_PATH_RE = re.compile(r"/workspace/[A-Za-z0-9_.-]+(?:__[A-Za-z0-9_.-]+)?[A-Za-z0-9_./-]*")


def apply_ablation(rows: list[dict[str, Any]], ablation: str) -> list[dict[str, Any]]:
    if ablation == "none":
        return copy.deepcopy(rows)
    transforms = {
        "no_paths": _remove_paths,
        "no_workspace_paths": _remove_workspace_paths,
        "no_repository_fields": _remove_repository_fields,
        "no_domains": _remove_domains,
        "no_repo_ids": _remove_repo_ids,
        "no_traces": _remove_traces,
    }
    if ablation not in transforms:
        known = ", ".join(sorted(["none", *transforms]))
        raise ValueError(f"unknown ablation: {ablation}. Known ablations: {known}")
    return [_map_text(row, transforms[ablation], ablation) for row in rows]


def apply_ablation_to_row(row: dict[str, Any], ablation: str) -> dict[str, Any]:
    if ablation == "none":
        return copy.deepcopy(row)
    transforms = {
        "no_paths": _remove_paths,
        "no_workspace_paths": _remove_workspace_paths,
        "no_repository_fields": _remove_repository_fields,
        "no_domains": _remove_domains,
        "no_repo_ids": _remove_repo_ids,
        "no_traces": _remove_traces,
    }
    if ablation not in transforms:
        known = ", ".join(sorted(["none", *transforms]))
        raise ValueError(f"unknown ablation: {ablation}. Known ablations: {known}")
    return _map_text(row, transforms[ablation], ablation)


def _map_text(row: dict[str, Any], func, ablation: str) -> dict[str, Any]:
    out = copy.deepcopy(row)
    for message in out.get("messages", []):
        message["content"] = func(message.get("content", ""))
    out["ablation"] = ablation
    out["token_count"] = _token_count(out)
    return out


def _remove_paths(text: str) -> str:
    return PATH_RE.sub("[PATH_REMOVED]", text)


def _remove_workspace_paths(text: str) -> str:
    return WORKSPACE_PATH_RE.sub("[WORKSPACE_PATH_REMOVED]", text)


def _remove_domains(text: str) -> str:
    return DOMAIN_RE.sub("[DOMAIN_REMOVED]", text)


def _remove_repo_ids(text: str) -> str:
    text = REPOSITORY_FIELD_RE.sub("repository=[REPO_REMOVED]", text)
    return REPO_SLUG_RE.sub("repo_slug=[REPO_SLUG_REMOVED]", text)


def _remove_repository_fields(text: str) -> str:
    return REPOSITORY_FIELD_RE.sub("repository=[REPO_REMOVED]", text)


def _remove_traces(text: str) -> str:
    return TRACE_RE.sub("[TRACE_REMOVED]", text)


def _token_count(row: dict[str, Any]) -> int:
    return sum(len(message.get("content", "").split()) for message in row.get("messages", []))
