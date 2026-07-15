from __future__ import annotations

import argparse
import copy
import json
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from agent_privacy.io import read_jsonl, write_json, write_jsonl


WORKSPACE_RE = re.compile(r"/workspace/[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+(?:__[0-9.]+)?")
REPOSITORY_RE = re.compile(r"\brepository=[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b")
UPLOADED_RE = re.compile(r"/workspace/[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+(?:__[0-9.]+)?")
SOURCE_REPO_TEXT_RE = re.compile(r"\b[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+(?:__[0-9.]+)?\b")


LANGUAGE_TO_PACKAGE = {
    "python": ("pip", "pytest -q", ".cache/pip"),
    "javascript": ("npm", "npm test", ".npm"),
    "typescript": ("npm", "pnpm test", ".pnpm-store"),
    "go": ("go", "go test ./...", "go-build"),
    "java": ("maven", "mvn test", ".m2"),
    "rust": ("cargo", "cargo test", ".cargo"),
}


SERVICE_WORDS = [
    "billing",
    "search",
    "identity",
    "deploy",
    "metrics",
    "pipeline",
    "notebook",
    "visual",
    "schema",
    "worker",
    "gateway",
    "scheduler",
]


def build_open_swe_user_overlay(config_path: Path) -> dict[str, Any]:
    config = _read_config(config_path)
    rng = random.Random(int(config.get("seed", 7)))
    source_dir = Path(config["source_dataset_dir"])
    output_dir = Path(config["output_dir"])
    snapshot_dir = Path(config["snapshot_output_dir"])

    attack_rows = read_jsonl(source_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(source_dir / "ground_truth.jsonl")
    truth_by_request = {row["request_id"]: row for row in truth_rows}
    workflows = _group_workflows(attack_rows, truth_by_request)
    max_workflows = int(config.get("max_source_workflows") or len(workflows))
    workflows = workflows[:max_workflows]

    orgs, users, projects = _build_overlay_entities(config, rng)
    assignments = _assign_workflows(workflows, orgs, users, projects, config, rng)
    overlay_attack: list[dict[str, Any]] = []
    overlay_truth: list[dict[str, Any]] = []
    overlay_provenance: list[dict[str, Any]] = []
    profile_truth = _build_profiles(orgs, users, projects)

    request_index = 1
    for workflow_index, workflow in enumerate(workflows, start=1):
        assignment = assignments[workflow.source_workflow_id]
        workflow_id = (
            f"overlay_wf_{assignment.user.user_id.removeprefix('overlay_user_')}_"
            f"{workflow_index:04d}"
        )
        workflow_start = _workflow_start_time(assignment.user, workflow_index, config, rng)
        sorted_rows = sorted(workflow.rows, key=lambda row: workflow.turn_by_request[row["request_id"]])
        turn_timestamps = _turn_timestamps(workflow_start, len(sorted_rows), config, rng)
        for row, timestamp in zip(sorted_rows, turn_timestamps, strict=True):
            source_truth = truth_by_request[row["request_id"]]
            turn_id = int(source_truth.get("turn_id", workflow.turn_by_request[row["request_id"]]))
            request_id = f"overlay_req_{request_index:07d}"
            request_index += 1
            attack_row = _overlay_attack_row(
                row,
                request_id=request_id,
                timestamp=timestamp,
                assignment=assignment,
                config=config,
                rng=rng,
            )
            truth_row = {
                "request_id": request_id,
                "org_id": assignment.org.org_id,
                "user_id": assignment.user.user_id,
                "project_id": assignment.project.project_id,
                "workflow_id": workflow_id,
                "turn_id": turn_id,
                "task_type": source_truth.get("task_type", "software_issue_resolution"),
                "profile_truth": _request_profile_truth(assignment),
            }
            provenance_row = {
                "request_id": request_id,
                "source_request_id": row["request_id"],
                "source_workflow_id": workflow.source_workflow_id,
                "source_project_id": source_truth.get("project_id"),
                "source_org_id": source_truth.get("org_id"),
                "source_turn_id": turn_id,
                "overlay_level": config.get("overlay_level", ""),
                "overlay_org_id": assignment.org.org_id,
                "overlay_user_id": assignment.user.user_id,
                "overlay_project_id": assignment.project.project_id,
                "overlay_workflow_id": workflow_id,
                "injected_signal_types": _signal_types(attack_row),
            }
            overlay_attack.append(attack_row)
            overlay_truth.append(truth_row)
            overlay_provenance.append(provenance_row)

    sorted_bundle = sorted(
        zip(overlay_attack, overlay_truth, overlay_provenance, strict=True),
        key=lambda item: (item[0]["timestamp"], item[0]["request_id"]),
    )
    overlay_attack = [item[0] for item in sorted_bundle]
    overlay_truth = [item[1] for item in sorted_bundle]
    overlay_provenance = [item[2] for item in sorted_bundle]

    write_jsonl(output_dir / "attack_view.jsonl", overlay_attack)
    write_jsonl(output_dir / "ground_truth.jsonl", overlay_truth)
    write_jsonl(output_dir / "request_provenance.jsonl", overlay_provenance)
    write_json(output_dir / "profiles.json", profile_truth)
    manifest = _manifest(config_path, config, source_dir, overlay_attack, overlay_truth, profile_truth)
    write_json(output_dir / "source_manifest.json", manifest)
    snapshot_summary = _write_snapshots(
        snapshot_dir,
        overlay_attack,
        overlay_truth,
        overlay_provenance,
        config,
        output_dir,
    )
    return {
        "dataset_dir": str(output_dir),
        "snapshot_dir": str(snapshot_dir),
        "requests": len(overlay_attack),
        "truth": len(overlay_truth),
        "provenance": len(overlay_provenance),
        "orgs": len(profile_truth["orgs"]),
        "users": len(profile_truth["users"]),
        "projects": len(profile_truth["projects"]),
        "snapshots": snapshot_summary["snapshots"],
    }


class SourceWorkflow:
    def __init__(self, source_workflow_id: str, rows: list[dict[str, Any]], turn_by_request: dict[str, int]):
        self.source_workflow_id = source_workflow_id
        self.rows = rows
        self.turn_by_request = turn_by_request


class OverlayOrg:
    def __init__(self, org_id: str, alias: str, timezone_offset: int):
        self.org_id = org_id
        self.alias = alias
        self.timezone_offset = timezone_offset


class OverlayProject:
    def __init__(
        self,
        project_id: str,
        org_id: str,
        alias: str,
        service_name: str,
        language: str,
        package_manager: str,
        build_tool: str,
        internal_domain: str,
    ):
        self.project_id = project_id
        self.org_id = org_id
        self.alias = alias
        self.service_name = service_name
        self.language = language
        self.package_manager = package_manager
        self.build_tool = build_tool
        self.internal_domain = internal_domain


class OverlayUser:
    def __init__(
        self,
        user_id: str,
        org_id: str,
        alias: str,
        home_alias: str,
        timezone_offset: int,
        active_center: int,
        tool_schema: dict[str, Any],
        command_preferences: list[str],
        cache_bucket: str,
    ):
        self.user_id = user_id
        self.org_id = org_id
        self.alias = alias
        self.home_alias = home_alias
        self.timezone_offset = timezone_offset
        self.active_center = active_center
        self.tool_schema = tool_schema
        self.command_preferences = command_preferences
        self.cache_bucket = cache_bucket
        self.projects: list[str] = []


class Assignment:
    def __init__(self, org: OverlayOrg, user: OverlayUser, project: OverlayProject):
        self.org = org
        self.user = user
        self.project = project


def _read_config(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    base = config.get("base_config")
    if base:
        base_config = json.loads(Path(base).read_text(encoding="utf-8"))
        config = _deep_merge(base_config, config)
    return config


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _group_workflows(
    attack_rows: list[dict[str, Any]],
    truth_by_request: dict[str, dict[str, Any]],
) -> list[SourceWorkflow]:
    rows_by_workflow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    turn_by_workflow: dict[str, dict[str, int]] = defaultdict(dict)
    for row in attack_rows:
        truth = truth_by_request.get(row["request_id"])
        if not truth:
            continue
        workflow_id = str(truth["workflow_id"])
        rows_by_workflow[workflow_id].append(row)
        turn_by_workflow[workflow_id][row["request_id"]] = int(truth.get("turn_id", 0))
    workflows = []
    for workflow_id, rows in rows_by_workflow.items():
        rows.sort(key=lambda row: (turn_by_workflow[workflow_id][row["request_id"]], row["request_id"]))
        workflows.append(SourceWorkflow(workflow_id, rows, turn_by_workflow[workflow_id]))
    workflows.sort(key=lambda workflow: workflow.source_workflow_id)
    return workflows


def _build_overlay_entities(
    config: dict[str, Any], rng: random.Random
) -> tuple[list[OverlayOrg], list[OverlayUser], list[OverlayProject]]:
    label = config["label_overlay"]
    signal = config["signal_overlay"]
    time_config = config["time_overlay"]
    orgs: list[OverlayOrg] = []
    users: list[OverlayUser] = []
    projects: list[OverlayProject] = []
    timezone_offsets = list(time_config["timezone_offsets"])
    for org_idx in range(1, int(label["num_orgs"]) + 1):
        org = OverlayOrg(
            org_id=f"overlay_org_{org_idx:03d}",
            alias=f"{_word(org_idx)}-{rng.choice(['core', 'labs', 'data', 'cloud'])}",
            timezone_offset=rng.choice(timezone_offsets),
        )
        orgs.append(org)
        project_count = rng.randint(int(label["min_projects_per_org"]), int(label["max_projects_per_org"]))
        org_projects = []
        for project_idx in range(1, project_count + 1):
            language = rng.choice(list(LANGUAGE_TO_PACKAGE))
            package_manager, build_tool, _cache = LANGUAGE_TO_PACKAGE[language]
            service_name = f"{rng.choice(SERVICE_WORDS)}-{rng.choice(['api', 'svc', 'engine', 'worker'])}"
            project = OverlayProject(
                project_id=f"overlay_proj_{org_idx:03d}_{project_idx:03d}",
                org_id=org.org_id,
                alias=f"{service_name}-{project_idx}",
                service_name=service_name,
                language=language,
                package_manager=package_manager,
                build_tool=build_tool,
                internal_domain=f"{service_name}.{rng.choice(config['profile_overlay']['synthetic_internal_domain_suffixes'])}",
            )
            projects.append(project)
            org_projects.append(project)
        user_count = rng.randint(int(label["min_users_per_org"]), int(label["max_users_per_org"]))
        shared_alias_prefix = _alias_token(rng)
        for user_idx in range(1, user_count + 1):
            alias = (
                shared_alias_prefix
                if rng.random() < float(signal["user_alias_collision_rate"])
                else _alias_token(rng)
            )
            home_template = rng.choice(signal["home_alias_templates"])
            active_center = rng.randint(
                int(time_config["active_hour_center_min"]),
                int(time_config["active_hour_center_max"]),
            )
            command_preferences = rng.sample(
                list(signal["command_preferences"]),
                k=min(3, len(signal["command_preferences"])),
            )
            user = OverlayUser(
                user_id=f"overlay_user_{org_idx:03d}_{user_idx:03d}",
                org_id=org.org_id,
                alias=alias,
                home_alias=home_template.format(alias=alias),
                timezone_offset=org.timezone_offset,
                active_center=active_center,
                tool_schema=copy.deepcopy(rng.choice(signal["tool_schema_variants"])),
                command_preferences=command_preferences,
                cache_bucket=rng.choice(signal["cache_buckets"]),
            )
            user.projects = [project.project_id for project in rng.sample(org_projects, k=min(2, len(org_projects)))]
            users.append(user)
    return orgs, users, projects


def _assign_workflows(
    workflows: list[SourceWorkflow],
    orgs: list[OverlayOrg],
    users: list[OverlayUser],
    projects: list[OverlayProject],
    config: dict[str, Any],
    rng: random.Random,
) -> dict[str, Assignment]:
    users_by_org: dict[str, list[OverlayUser]] = defaultdict(list)
    projects_by_org: dict[str, list[OverlayProject]] = defaultdict(list)
    for user in users:
        users_by_org[user.org_id].append(user)
    for project in projects:
        projects_by_org[project.org_id].append(project)
    orgs_by_id = {org.org_id: org for org in orgs}
    assignments: dict[str, Assignment] = {}
    shuffled = list(workflows)
    rng.shuffle(shuffled)
    for idx, workflow in enumerate(shuffled):
        org_id = sorted(users_by_org)[idx % len(users_by_org)]
        org_users = users_by_org[org_id]
        org_projects = projects_by_org[org_id]
        project = rng.choice(org_projects)
        eligible_users = [user for user in org_users if project.project_id in user.projects]
        if not eligible_users:
            eligible_users = org_users
        user = rng.choice(eligible_users)
        assignments[workflow.source_workflow_id] = Assignment(orgs_by_id[org_id], user, project)
    return assignments


def _build_profiles(
    orgs: list[OverlayOrg],
    users: list[OverlayUser],
    projects: list[OverlayProject],
) -> dict[str, Any]:
    projects_by_org: dict[str, list[OverlayProject]] = defaultdict(list)
    users_by_org: dict[str, list[OverlayUser]] = defaultdict(list)
    for project in projects:
        projects_by_org[project.org_id].append(project)
    for user in users:
        users_by_org[user.org_id].append(user)
    return {
        "orgs": {
            org.org_id: {
                "alias": org.alias,
                "timezone_offset": org.timezone_offset,
                "projects": [project.project_id for project in projects_by_org[org.org_id]],
                "users": [user.user_id for user in users_by_org[org.org_id]],
                "languages": sorted({project.language for project in projects_by_org[org.org_id]}),
                "package_managers": sorted(
                    {project.package_manager for project in projects_by_org[org.org_id]}
                ),
                "build_tools": sorted({project.build_tool for project in projects_by_org[org.org_id]}),
                "service_names": sorted(
                    {project.service_name for project in projects_by_org[org.org_id]}
                ),
                "internal_domains": sorted(
                    {project.internal_domain for project in projects_by_org[org.org_id]}
                ),
            }
            for org in orgs
        },
        "users": {
            user.user_id: {
                "org_id": user.org_id,
                "alias": user.alias,
                "home_alias": user.home_alias,
                "timezone_offset": user.timezone_offset,
                "active_center": user.active_center,
                "tool_schema": user.tool_schema,
                "tool_preferences": user.command_preferences,
                "cache_bucket": user.cache_bucket,
                "projects": user.projects,
            }
            for user in users
        },
        "projects": {
            project.project_id: {
                "org_id": project.org_id,
                "alias": project.alias,
                "service_name": project.service_name,
                "language": project.language,
                "package_manager": project.package_manager,
                "build_tool": project.build_tool,
                "internal_domain": project.internal_domain,
            }
            for project in projects
        },
    }


def _workflow_start_time(
    user: OverlayUser,
    workflow_index: int,
    config: dict[str, Any],
    rng: random.Random,
) -> datetime:
    time_config = config["time_overlay"]
    start = _parse_time(time_config["start_time"])
    span_days = int(time_config["time_span_days"])
    day_offset = workflow_index % span_days
    local_hour = max(
        0,
        min(
            23,
            int(rng.gauss(user.active_center, float(time_config["active_hour_spread_hours"]) / 2)),
        ),
    )
    jitter = rng.randint(0, int(time_config["workflow_start_jitter_minutes"]))
    local = start + timedelta(days=day_offset, hours=local_hour - start.hour, minutes=jitter)
    return local - timedelta(hours=user.timezone_offset)


def _turn_timestamps(
    workflow_start: datetime,
    turns: int,
    config: dict[str, Any],
    rng: random.Random,
) -> list[str]:
    time_config = config["time_overlay"]
    current = workflow_start
    timestamps = []
    for idx in range(turns):
        if idx > 0:
            delay = _sample_delay_seconds(time_config, rng)
            current += timedelta(seconds=delay)
        timestamps.append(current.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"))
    return timestamps


def _sample_delay_seconds(time_config: dict[str, Any], rng: random.Random) -> int:
    low = int(time_config["inter_turn_delay_seconds_min"])
    p50 = int(time_config["inter_turn_delay_seconds_p50"])
    p90 = int(time_config["inter_turn_delay_seconds_p90"])
    if rng.random() < float(time_config["burst_probability"]):
        return rng.randint(low, p50)
    return rng.randint(p50, p90)


def _overlay_attack_row(
    source_row: dict[str, Any],
    *,
    request_id: str,
    timestamp: str,
    assignment: Assignment,
    config: dict[str, Any],
    rng: random.Random,
) -> dict[str, Any]:
    row = copy.deepcopy(source_row)
    row["request_id"] = request_id
    row["timestamp"] = timestamp
    row["messages"] = [
        _overlay_message(message, assignment)
        for message in row.get("messages", [])
    ]
    row["tool_schemas"] = _tool_schemas(row.get("tool_schemas", []), assignment, config, rng)
    row["cache_bucket"] = _cache_bucket(assignment, config, rng)
    row["provider_metadata"] = _provider_metadata(row.get("provider_metadata", {}))
    if _should_inject(config, "inject_environment_observation_rate", rng):
        row["messages"].append({"role": "tool", "name": "environment", "content": _environment_observation(assignment, config, rng)})
    if _should_inject(config, "inject_tool_preference_observation_rate", rng):
        row["messages"].append({"role": "tool", "name": "shell", "content": _tool_preference_observation(assignment, rng)})
    if _should_inject(config, "inject_profile_hint_rate", rng):
        row["messages"].append({"role": "tool", "name": "service", "content": _profile_observation(assignment)})
    row["token_count"] = _token_count(row.get("messages", []))
    return _provider_view_only(row)


def _overlay_message(message: dict[str, Any], assignment: Assignment) -> dict[str, Any]:
    out = dict(message)
    content = str(out.get("content", ""))
    workspace = f"/workspace/{assignment.org.alias}__{assignment.project.alias}"
    content = WORKSPACE_RE.sub(workspace, content)
    content = UPLOADED_RE.sub(workspace, content)
    content = REPOSITORY_RE.sub(
        f"repository={assignment.org.alias}/{assignment.project.alias}",
        content,
    )
    content = SOURCE_REPO_TEXT_RE.sub(
        f"{assignment.org.alias}__{assignment.project.alias}",
        content,
    )
    out["content"] = content
    return out


def _tool_schemas(
    source_schemas: list[dict[str, Any]],
    assignment: Assignment,
    config: dict[str, Any],
    rng: random.Random,
) -> list[dict[str, Any]]:
    signal = config["signal_overlay"]
    if rng.random() < float(signal["user_signal_dropout_rate"]):
        return source_schemas
    if rng.random() < float(signal["shared_tool_schema_rate"]):
        return [copy.deepcopy(assignment.user.tool_schema)]
    schemas = [copy.deepcopy(assignment.user.tool_schema)]
    if source_schemas and rng.random() < 0.35:
        schemas.append(copy.deepcopy(source_schemas[0]))
    return schemas


def _cache_bucket(assignment: Assignment, config: dict[str, Any], rng: random.Random) -> str:
    signal = config["signal_overlay"]
    if rng.random() < float(signal["cache_noise_rate"]):
        return rng.choice(signal["cache_buckets"])
    return assignment.user.cache_bucket


def _provider_metadata(metadata: Any) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "api_surface": metadata.get("api_surface", "chat_completions"),
        "brokered": bool(metadata.get("brokered", True)),
        "stream": bool(metadata.get("stream", False)),
    }


def _environment_observation(
    assignment: Assignment,
    config: dict[str, Any],
    rng: random.Random,
) -> str:
    signal = config["signal_overlay"]
    cache_template = rng.choice(signal["cache_path_templates"])
    home = assignment.user.home_alias
    cache_path = cache_template.format(home=home)
    workspace = signal["workspace_template"].format(
        org_alias=assignment.org.alias,
        project_alias=assignment.project.alias,
    )
    shell_history = f"{home}/.agent/history.log"
    return (
        f"Environment summary: cwd={workspace}; cache_root={cache_path}; "
        f"runner_home={home}; shell_history={shell_history}; "
        f"package_manager={assignment.project.package_manager}"
    )


def _tool_preference_observation(assignment: Assignment, rng: random.Random) -> str:
    command = rng.choice(assignment.user.command_preferences)
    return (
        f"Command trace: preferred_check={command}; "
        f"last_status=nonzero; retry_policy=short"
    )


def _profile_observation(assignment: Assignment) -> str:
    return (
        f"Service context: service={assignment.project.service_name}; "
        f"domain={assignment.project.internal_domain}; build={assignment.project.build_tool}"
    )


def _request_profile_truth(assignment: Assignment) -> dict[str, list[str]]:
    return {
        "languages": [assignment.project.language],
        "package_managers": [assignment.project.package_manager],
        "build_tools": [assignment.project.build_tool],
        "repo_names": [assignment.project.alias],
        "service_names": [assignment.project.service_name],
        "internal_domains": [assignment.project.internal_domain],
    }


def _provider_view_only(row: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "request_id",
        "timestamp",
        "model",
        "messages",
        "tool_schemas",
        "token_count",
        "cache_bucket",
        "provider_metadata",
    }
    clean = {key: value for key, value in row.items() if key in allowed}
    metadata = clean.get("provider_metadata")
    if isinstance(metadata, dict):
        clean["provider_metadata"] = {
            key: value
            for key, value in metadata.items()
            if key in {"api_surface", "brokered", "stream"}
        }
    return clean


def _signal_types(row: dict[str, Any]) -> list[str]:
    text = "\n".join(str(message.get("content", "")) for message in row.get("messages", []))
    signals = []
    if "Environment summary:" in text:
        signals.append("environment")
    if "Command trace:" in text:
        signals.append("tool_preference")
    if "Service context:" in text:
        signals.append("profile_hint")
    if row.get("cache_bucket"):
        signals.append("cache_proxy")
    if row.get("tool_schemas"):
        signals.append("tool_schema")
    signals.append("timestamp")
    return sorted(set(signals))


def _write_snapshots(
    output_dir: Path,
    attack_rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    provenance_rows: list[dict[str, Any]],
    config: dict[str, Any],
    source_dataset_dir: Path,
) -> dict[str, Any]:
    truth_by_request = {row["request_id"]: row for row in truth_rows}
    provenance_by_request = {row["request_id"]: row for row in provenance_rows}
    snapshots = []
    counts = list(config.get("snapshots", {}).get("request_counts", []))
    include_partial = bool(config.get("snapshots", {}).get("include_partial_if_short", True))
    for count in counts:
        if count > len(attack_rows) and not include_partial:
            continue
        selected = attack_rows[: min(int(count), len(attack_rows))]
        label = f"first_{count}_requests"
        snapshot_path = output_dir / label
        snapshot_truth = [truth_by_request[row["request_id"]] for row in selected]
        snapshot_provenance = [provenance_by_request[row["request_id"]] for row in selected]
        write_jsonl(snapshot_path / "attack_view.jsonl", selected)
        write_jsonl(snapshot_path / "ground_truth.jsonl", snapshot_truth)
        write_jsonl(snapshot_path / "request_provenance.jsonl", snapshot_provenance)
        manifest = {
            "label": label,
            "source_dataset_dir": str(source_dataset_dir),
            "overlay_level": config.get("overlay_level"),
            "snapshot_type": "cumulative_provider_view",
            "requested_count": count,
            "requests": len(selected),
            "truth": len(snapshot_truth),
            "provenance": len(snapshot_provenance),
            "user_count": len({row["user_id"] for row in snapshot_truth}),
            "workflow_count": len({row["workflow_id"] for row in snapshot_truth}),
            "project_count": len({row["project_id"] for row in snapshot_truth}),
            "org_count": len({row["org_id"] for row in snapshot_truth}),
            "start_timestamp": selected[0]["timestamp"] if selected else None,
            "end_timestamp": selected[-1]["timestamp"] if selected else None,
        }
        write_json(snapshot_path / "source_manifest.json", manifest)
        snapshots.append({"path": str(snapshot_path), **manifest})
    summary = {
        "source_dataset_dir": str(source_dataset_dir),
        "overlay_level": config.get("overlay_level"),
        "snapshots": snapshots,
    }
    write_json(output_dir / "snapshot_manifest.json", summary)
    return summary


def _manifest(
    config_path: Path,
    config: dict[str, Any],
    source_dir: Path,
    attack_rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    profiles: dict[str, Any],
) -> dict[str, Any]:
    return {
        "dataset": "Open-SWE User Overlay",
        "dataset_type": "trace_grounded_semi_synthetic_user_overlay",
        "config_path": str(config_path),
        "source_dataset_dir": str(source_dir),
        "overlay_level": config.get("overlay_level"),
        "requests": len(attack_rows),
        "truth": len(truth_rows),
        "orgs": len(profiles["orgs"]),
        "users": len(profiles["users"]),
        "projects": len(profiles["projects"]),
        "notes": [
            "Open-SWE traces are used as the real agent-trace substrate.",
            "User/org/project labels are synthetic overlay truth.",
            "attack_view contains only provider-visible fields.",
            "Source Open-SWE labels and ids are provenance-only.",
            "This dataset is not real Open-SWE user identity evidence.",
        ],
        "provider_view_guardrails": config.get("provider_view_guardrails", {}),
    }


def _should_inject(config: dict[str, Any], key: str, rng: random.Random) -> bool:
    signal = config["signal_overlay"]
    dropout = float(signal["user_signal_dropout_rate"])
    return rng.random() >= dropout and rng.random() < float(signal[key])


def _token_count(messages: list[dict[str, Any]]) -> int:
    return sum(len(str(message.get("content", "")).split()) for message in messages)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _word(idx: int) -> str:
    words = [
        "atlas",
        "river",
        "nova",
        "vector",
        "signal",
        "matrix",
        "harbor",
        "summit",
        "orbit",
        "quartz",
    ]
    return words[(idx - 1) % len(words)] + f"{idx:02d}"


def _alias_token(rng: random.Random) -> str:
    return f"{rng.choice('abcdefghjkmnpqrstuvwxyz')}{rng.randint(10, 99)}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an Open-SWE trace-grounded user overlay dataset.")
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_open_swe_user_overlay(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
