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


USER_ID_RE = re.compile(r"\b[A-Za-z]+_[A-Za-z]+_[0-9]{3,}\b")
ORDER_RE = re.compile(r"#[A-Z][0-9]{6,}|\border[_-][A-Za-z0-9-]{4,}\b", re.IGNORECASE)
RESERVATION_RE = re.compile(r"\breservation[_-][A-Za-z0-9-]{3,}\b", re.IGNORECASE)


SERVICE_LINES = {
    "airline": ["booking", "flight-change", "cancellation", "compensation", "baggage"],
    "retail": ["refund", "exchange", "order-modification", "delivery", "loyalty"],
}
REGIONS = ["iad", "pdx", "dfw", "fra", "sin", "syd"]
ORG_WORDS = [
    "aurora",
    "beacon",
    "cedar",
    "delta",
    "ember",
    "fjord",
    "grove",
    "helix",
]


def build_tau_bench_overlay(config_path: Path) -> dict[str, Any]:
    config = _read_config(config_path)
    rng = random.Random(int(config.get("seed", 17)))
    source_dir = Path(config["source_dataset_dir"])
    output_dir = Path(config["output_dir"])
    snapshot_dir = Path(config["snapshot_output_dir"])

    attack_rows = read_jsonl(source_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(source_dir / "ground_truth.jsonl")
    provenance_rows = (
        read_jsonl(source_dir / "request_provenance.jsonl")
        if (source_dir / "request_provenance.jsonl").exists()
        else []
    )
    truth_by_request = {row["request_id"]: row for row in truth_rows}
    provenance_by_request = {row["request_id"]: row for row in provenance_rows}
    workflows = _group_workflows(attack_rows, truth_by_request)
    max_workflows = int(config.get("max_source_workflows") or len(workflows))
    workflows = workflows[:max_workflows]

    orgs, users, projects = _build_entities(config, rng)
    assignments = _assign_workflows(workflows, orgs, users, projects, rng)
    profiles = _build_profiles(orgs, users, projects)

    overlay_attack: list[dict[str, Any]] = []
    overlay_truth: list[dict[str, Any]] = []
    overlay_provenance: list[dict[str, Any]] = []
    request_index = 1
    for workflow_index, workflow in enumerate(workflows, start=1):
        assignment = assignments[workflow.workflow_id]
        workflow_id = f"tau_overlay_wf_{assignment.user.user_id.removeprefix('tau_overlay_user_')}_{workflow_index:04d}"
        workflow_start = _workflow_start_time(assignment.user, workflow_index, config, rng)
        sorted_rows = sorted(workflow.rows, key=lambda row: workflow.turns[row["request_id"]])
        timestamps = _turn_timestamps(workflow_start, len(sorted_rows), config, rng)
        for row, timestamp in zip(sorted_rows, timestamps, strict=True):
            source_truth = truth_by_request[row["request_id"]]
            source_provenance = provenance_by_request.get(row["request_id"], {})
            turn_id = int(source_truth.get("turn_id", workflow.turns[row["request_id"]]))
            request_id = f"tau_overlay_req_{request_index:07d}"
            request_index += 1
            attack_row = _overlay_attack_row(
                row,
                source_truth=source_truth,
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
                "task_type": f"tau_bench_overlay_{assignment.project.domain}",
                "profile_truth": _request_profile_truth(assignment),
            }
            provenance_row = {
                "request_id": request_id,
                "source_request_id": row["request_id"],
                "source_workflow_id": workflow.workflow_id,
                "source_user_id": source_truth.get("user_id"),
                "source_project_id": source_truth.get("project_id"),
                "source_org_id": source_truth.get("org_id"),
                "source_domain": source_provenance.get("source_domain") or source_truth.get("org_id"),
                "source_turn_id": turn_id,
                "overlay_level": config.get("overlay_level", "T3"),
                "overlay_org_id": assignment.org.org_id,
                "overlay_user_id": assignment.user.user_id,
                "overlay_project_id": assignment.project.project_id,
                "overlay_workflow_id": workflow_id,
                "injected_signal_types": _signal_types(attack_row),
            }
            overlay_attack.append(attack_row)
            overlay_truth.append(truth_row)
            overlay_provenance.append(provenance_row)

    joined = sorted(
        zip(overlay_attack, overlay_truth, overlay_provenance, strict=True),
        key=lambda item: (item[0]["timestamp"], item[0]["request_id"]),
    )
    overlay_attack = [item[0] for item in joined]
    overlay_truth = [item[1] for item in joined]
    overlay_provenance = [item[2] for item in joined]

    write_jsonl(output_dir / "attack_view.jsonl", overlay_attack)
    write_jsonl(output_dir / "ground_truth.jsonl", overlay_truth)
    write_jsonl(output_dir / "request_provenance.jsonl", overlay_provenance)
    write_json(output_dir / "profiles.json", profiles)
    manifest = _manifest(config_path, config, source_dir, overlay_attack, overlay_truth, profiles)
    write_json(output_dir / "source_manifest.json", manifest)
    snapshots = _write_snapshots(snapshot_dir, overlay_attack, overlay_truth, overlay_provenance, config, output_dir)
    return {
        "dataset_dir": str(output_dir),
        "snapshot_dir": str(snapshot_dir),
        "requests": len(overlay_attack),
        "truth": len(overlay_truth),
        "provenance": len(overlay_provenance),
        "orgs": len(profiles["orgs"]),
        "users": len(profiles["users"]),
        "projects": len(profiles["projects"]),
        "snapshots": snapshots["snapshots"],
    }


class SourceWorkflow:
    def __init__(self, workflow_id: str, rows: list[dict[str, Any]], turns: dict[str, int]):
        self.workflow_id = workflow_id
        self.rows = rows
        self.turns = turns


class TauOrg:
    def __init__(self, org_id: str, alias: str, domain: str, region: str, cache_bucket: str):
        self.org_id = org_id
        self.alias = alias
        self.domain = domain
        self.region = region
        self.cache_bucket = cache_bucket


class TauProject:
    def __init__(self, project_id: str, org_id: str, alias: str, domain: str, service_line: str):
        self.project_id = project_id
        self.org_id = org_id
        self.alias = alias
        self.domain = domain
        self.service_line = service_line
        self.queue = f"{alias}-queue"
        self.internal_domain = f"{alias}.{domain}.ops.internal"


class TauUser:
    def __init__(
        self,
        user_id: str,
        org_id: str,
        alias: str,
        customer_ref: str,
        tier: str,
        active_center: int,
        cache_bucket: str,
    ):
        self.user_id = user_id
        self.org_id = org_id
        self.alias = alias
        self.customer_ref = customer_ref
        self.tier = tier
        self.active_center = active_center
        self.cache_bucket = cache_bucket
        self.projects: list[str] = []


class Assignment:
    def __init__(self, org: TauOrg, user: TauUser, project: TauProject):
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
    turns_by_workflow: dict[str, dict[str, int]] = defaultdict(dict)
    for row in attack_rows:
        truth = truth_by_request.get(row["request_id"])
        if not truth:
            continue
        workflow_id = str(truth["workflow_id"])
        rows_by_workflow[workflow_id].append(row)
        turns_by_workflow[workflow_id][row["request_id"]] = int(truth.get("turn_id", 0))
    workflows = [
        SourceWorkflow(workflow_id, rows, turns_by_workflow[workflow_id])
        for workflow_id, rows in rows_by_workflow.items()
    ]
    workflows.sort(key=lambda workflow: workflow.workflow_id)
    return workflows


def _build_entities(
    config: dict[str, Any],
    rng: random.Random,
) -> tuple[list[TauOrg], list[TauUser], list[TauProject]]:
    label = config["label_overlay"]
    orgs: list[TauOrg] = []
    users: list[TauUser] = []
    projects: list[TauProject] = []
    domains = list(label.get("domains", ["airline", "retail"]))
    for org_idx in range(1, int(label["num_orgs"]) + 1):
        domain = domains[(org_idx - 1) % len(domains)]
        alias = f"{ORG_WORDS[(org_idx - 1) % len(ORG_WORDS)]}{org_idx:02d}-{domain}"
        org = TauOrg(
            org_id=f"tau_overlay_org_{org_idx:03d}",
            alias=alias,
            domain=domain,
            region=rng.choice(REGIONS),
            cache_bucket=f"tenant:{domain}:{alias}",
        )
        orgs.append(org)
        org_projects: list[TauProject] = []
        project_count = rng.randint(
            int(label["min_projects_per_org"]),
            int(label["max_projects_per_org"]),
        )
        for project_idx in range(1, project_count + 1):
            service_line = rng.choice(SERVICE_LINES.get(domain, ["support"]))
            project = TauProject(
                project_id=f"tau_overlay_proj_{org_idx:03d}_{project_idx:03d}",
                org_id=org.org_id,
                alias=f"{alias}-{service_line}-{project_idx}",
                domain=domain,
                service_line=service_line,
            )
            projects.append(project)
            org_projects.append(project)
        user_count = rng.randint(
            int(label["min_users_per_org"]),
            int(label["max_users_per_org"]),
        )
        shared_prefix = _alias_token(rng)
        for user_idx in range(1, user_count + 1):
            alias = shared_prefix if rng.random() < float(label.get("user_alias_collision_rate", 0.0)) else _alias_token(rng)
            user = TauUser(
                user_id=f"tau_overlay_user_{org_idx:03d}_{user_idx:03d}",
                org_id=org.org_id,
                alias=alias,
                customer_ref=f"cust-{alias}-{org_idx:03d}{user_idx:03d}",
                tier=rng.choice(["standard", "silver", "gold", "platinum"]),
                active_center=rng.randint(8, 18),
                cache_bucket=f"{org.cache_bucket}:acct:{alias}",
            )
            user.projects = [
                project.project_id
                for project in rng.sample(org_projects, k=min(2, len(org_projects)))
            ]
            users.append(user)
    return orgs, users, projects


def _assign_workflows(
    workflows: list[SourceWorkflow],
    orgs: list[TauOrg],
    users: list[TauUser],
    projects: list[TauProject],
    rng: random.Random,
) -> dict[str, Assignment]:
    users_by_org: dict[str, list[TauUser]] = defaultdict(list)
    projects_by_org: dict[str, list[TauProject]] = defaultdict(list)
    orgs_by_id = {org.org_id: org for org in orgs}
    for user in users:
        users_by_org[user.org_id].append(user)
    for project in projects:
        projects_by_org[project.org_id].append(project)
    assignments: dict[str, Assignment] = {}
    shuffled = list(workflows)
    rng.shuffle(shuffled)
    for idx, workflow in enumerate(shuffled):
        org = orgs[idx % len(orgs)]
        org_projects = projects_by_org[org.org_id]
        project = rng.choice(org_projects)
        eligible = [user for user in users_by_org[org.org_id] if project.project_id in user.projects]
        user = rng.choice(eligible or users_by_org[org.org_id])
        assignments[workflow.workflow_id] = Assignment(orgs_by_id[org.org_id], user, project)
    return assignments


def _build_profiles(orgs: list[TauOrg], users: list[TauUser], projects: list[TauProject]) -> dict[str, Any]:
    projects_by_org: dict[str, list[TauProject]] = defaultdict(list)
    users_by_org: dict[str, list[TauUser]] = defaultdict(list)
    for project in projects:
        projects_by_org[project.org_id].append(project)
    for user in users:
        users_by_org[user.org_id].append(user)
    return {
        "orgs": {
            org.org_id: {
                "alias": org.alias,
                "domain": org.domain,
                "region": org.region,
                "cache_bucket": org.cache_bucket,
                "projects": [project.project_id for project in projects_by_org[org.org_id]],
                "users": [user.user_id for user in users_by_org[org.org_id]],
                "service_lines": sorted({project.service_line for project in projects_by_org[org.org_id]}),
                "internal_domains": sorted({project.internal_domain for project in projects_by_org[org.org_id]}),
            }
            for org in orgs
        },
        "users": {
            user.user_id: {
                "org_id": user.org_id,
                "alias": user.alias,
                "customer_ref": user.customer_ref,
                "tier": user.tier,
                "cache_bucket": user.cache_bucket,
                "projects": user.projects,
            }
            for user in users
        },
        "projects": {
            project.project_id: {
                "org_id": project.org_id,
                "alias": project.alias,
                "domain": project.domain,
                "service_line": project.service_line,
                "queue": project.queue,
                "internal_domain": project.internal_domain,
            }
            for project in projects
        },
    }


def _overlay_attack_row(
    source_row: dict[str, Any],
    *,
    source_truth: dict[str, Any],
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
        _overlay_message(message, source_truth, assignment)
        for message in row.get("messages", [])
    ]
    signal = config["signal_overlay"]
    if _should_inject(signal, "inject_account_context_rate", rng):
        row["messages"].append({"role": "tool", "name": "account_context", "content": _account_context(assignment)})
    if _should_inject(signal, "inject_case_context_rate", rng):
        row["messages"].append({"role": "tool", "name": "case_context", "content": _case_context(assignment, rng)})
    row["tool_schemas"] = _tool_schemas(row.get("tool_schemas", []), assignment, signal, rng)
    row["cache_bucket"] = _cache_bucket(assignment, signal, rng)
    row["provider_metadata"] = _provider_metadata(row.get("provider_metadata", {}))
    row["token_count"] = _token_count(row.get("messages", []))
    return _provider_view_only(row)


def _overlay_message(message: dict[str, Any], source_truth: dict[str, Any], assignment: Assignment) -> dict[str, Any]:
    out = dict(message)
    content = str(out.get("content", ""))
    source_user = str(source_truth.get("user_id") or "")
    if source_user:
        content = content.replace(source_user, assignment.user.customer_ref)
    content = USER_ID_RE.sub(assignment.user.customer_ref, content)
    content = ORDER_RE.sub(f"order-{assignment.project.alias}", content)
    content = RESERVATION_RE.sub(f"reservation-{assignment.project.alias}", content)
    out["content"] = content
    return out


def _account_context(assignment: Assignment) -> str:
    return (
        f"Account context: tenant={assignment.org.alias}; region={assignment.org.region}; "
        f"customer_ref={assignment.user.customer_ref}; loyalty_tier={assignment.user.tier}; "
        f"account_cache={assignment.user.cache_bucket}"
    )


def _case_context(assignment: Assignment, rng: random.Random) -> str:
    ticket = f"case-{assignment.project.service_line}-{rng.randint(10000, 99999)}"
    return (
        f"Case context: case_id={ticket}; queue={assignment.project.queue}; "
        f"service_line={assignment.project.service_line}; internal_domain={assignment.project.internal_domain}"
    )


def _tool_schemas(
    source_schemas: list[dict[str, Any]],
    assignment: Assignment,
    signal: dict[str, Any],
    rng: random.Random,
) -> list[dict[str, Any]]:
    schemas = copy.deepcopy(source_schemas)
    if rng.random() < float(signal.get("inject_overlay_tool_schema_rate", 0.5)):
        schemas.append(
            {
                "name": f"{assignment.project.domain}_{assignment.project.service_line}_crm",
                "parameters": ["customer_ref", "case_id", "tenant"],
            }
        )
    return schemas


def _cache_bucket(assignment: Assignment, signal: dict[str, Any], rng: random.Random) -> str:
    if rng.random() < float(signal.get("cache_noise_rate", 0.0)):
        return f"tenant:{assignment.project.domain}:shared"
    if rng.random() < float(signal.get("user_cache_bucket_rate", 0.35)):
        return assignment.user.cache_bucket
    return assignment.org.cache_bucket


def _provider_metadata(metadata: Any) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "api_surface": metadata.get("api_surface", "chat_completions"),
        "brokered": bool(metadata.get("brokered", True)),
        "stream": bool(metadata.get("stream", False)),
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
    return {key: value for key, value in row.items() if key in allowed}


def _request_profile_truth(assignment: Assignment) -> dict[str, list[str]]:
    return {
        "domains": [assignment.project.domain],
        "tenant_aliases": [assignment.org.alias],
        "regions": [assignment.org.region],
        "customer_refs": [assignment.user.customer_ref],
        "loyalty_tiers": [assignment.user.tier],
        "service_lines": [assignment.project.service_line],
        "case_queues": [assignment.project.queue],
        "internal_domains": [assignment.project.internal_domain],
    }


def _signal_types(row: dict[str, Any]) -> list[str]:
    text = "\n".join(str(message.get("content", "")) for message in row.get("messages", []))
    signals = ["timestamp"]
    if "Account context:" in text:
        signals.append("account_context")
    if "Case context:" in text:
        signals.append("case_context")
    if row.get("cache_bucket"):
        signals.append("cache_proxy")
    if row.get("tool_schemas"):
        signals.append("tool_schema")
    return sorted(set(signals))


def _workflow_start_time( user: TauUser, workflow_index: int, config: dict[str, Any], rng: random.Random) -> datetime:
    time_config = config["time_overlay"]
    start = datetime.fromisoformat(str(time_config["start_time"]).replace("Z", "+00:00"))
    day_offset = workflow_index % int(time_config["time_span_days"])
    hour = max(0, min(23, int(rng.gauss(user.active_center, float(time_config["active_hour_spread_hours"]) / 2))))
    jitter = rng.randint(0, int(time_config["workflow_start_jitter_minutes"]))
    return (start + timedelta(days=day_offset, hours=hour - start.hour, minutes=jitter)).astimezone(timezone.utc)


def _turn_timestamps(start: datetime, turns: int, config: dict[str, Any], rng: random.Random) -> list[str]:
    time_config = config["time_overlay"]
    current = start
    timestamps = []
    for idx in range(turns):
        if idx:
            current += timedelta(seconds=rng.randint(int(time_config["inter_turn_delay_seconds_min"]), int(time_config["inter_turn_delay_seconds_max"])))
        timestamps.append(current.isoformat().replace("+00:00", "Z"))
    return timestamps


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
    for count in config.get("snapshots", {}).get("request_counts", []):
        selected = attack_rows[: min(int(count), len(attack_rows))]
        label = f"first_{count}_requests"
        path = output_dir / label
        snapshot_truth = [truth_by_request[row["request_id"]] for row in selected]
        snapshot_provenance = [provenance_by_request[row["request_id"]] for row in selected]
        write_jsonl(path / "attack_view.jsonl", selected)
        write_jsonl(path / "ground_truth.jsonl", snapshot_truth)
        write_jsonl(path / "request_provenance.jsonl", snapshot_provenance)
        manifest = {
            "label": label,
            "source_dataset_dir": str(source_dataset_dir),
            "overlay_level": config.get("overlay_level", "T3"),
            "snapshot_type": "cumulative_provider_view",
            "requested_count": count,
            "requests": len(selected),
            "truth": len(snapshot_truth),
            "provenance": len(snapshot_provenance),
            "org_count": len({row["org_id"] for row in snapshot_truth}),
            "user_count": len({row["user_id"] for row in snapshot_truth}),
            "project_count": len({row["project_id"] for row in snapshot_truth}),
            "workflow_count": len({row["workflow_id"] for row in snapshot_truth}),
            "start_timestamp": selected[0]["timestamp"] if selected else None,
            "end_timestamp": selected[-1]["timestamp"] if selected else None,
        }
        write_json(path / "source_manifest.json", manifest)
        snapshots.append({"path": str(path), **manifest})
    summary = {
        "source_dataset_dir": str(source_dataset_dir),
        "overlay_level": config.get("overlay_level", "T3"),
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
        "dataset": "tau-bench three-layer overlay",
        "dataset_type": "trace_grounded_semi_synthetic_business_overlay",
        "config_path": str(config_path),
        "source_dataset_dir": str(source_dir),
        "overlay_level": config.get("overlay_level", "T3"),
        "requests": len(attack_rows),
        "truth": len(truth_rows),
        "orgs": len(profiles["orgs"]),
        "users": len(profiles["users"]),
        "projects": len(profiles["projects"]),
        "notes": [
            "tau-bench historical traces are used as the real non-code agent-trace substrate.",
            "Org/user/project labels are synthetic business overlay truth.",
            "attack_view contains only provider-visible fields.",
            "Source tau-bench labels and ids are provenance-only.",
            "This dataset is not real tau-bench user identity evidence.",
        ],
    }


def _should_inject(signal: dict[str, Any], key: str, rng: random.Random) -> bool:
    return rng.random() >= float(signal.get("signal_dropout_rate", 0.0)) and rng.random() < float(signal.get(key, 0.0))


def _token_count(messages: list[dict[str, Any]]) -> int:
    return sum(len(str(message.get("content", "")).split()) for message in messages)


def _alias_token(rng: random.Random) -> str:
    return f"{rng.choice('abcdefghjkmnpqrstuvwxyz')}{rng.randint(100, 999)}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a tau-bench trace-grounded three-layer overlay dataset.")
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_tau_bench_overlay(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
