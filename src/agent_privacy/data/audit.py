from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.io import read_jsonl, write_json


def audit_dataset(dataset_dir: Path, output_path: Path | None = None) -> dict[str, Any]:
    attack_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    provenance_rows = (
        read_jsonl(dataset_dir / "request_provenance.jsonl")
        if (dataset_dir / "request_provenance.jsonl").exists()
        else []
    )
    truth_by_request = {row["request_id"]: row for row in truth_rows}

    repair_source = provenance_rows or attack_rows
    repair_modes = Counter(str(row.get("repair_mode", "unknown")) for row in repair_source)
    repair_fields = Counter(
        field for row in repair_source for field in row.get("repair_fields", []) if field
    )
    role_counts = Counter(
        message.get("role", "unknown")
        for row in attack_rows
        for message in row.get("messages", [])
    )
    message_counts = [len(row.get("messages", [])) for row in attack_rows]
    token_counts = [int(row.get("token_count", 0)) for row in attack_rows]
    workflow_turns: dict[str, set[int]] = defaultdict(set)
    orgs = Counter()
    projects = Counter()
    users = Counter()

    for row in truth_rows:
        orgs[str(row.get("org_id"))] += 1
        projects[str(row.get("project_id"))] += 1
        users[str(row.get("user_id"))] += 1
        workflow_turns[str(row.get("workflow_id"))].add(int(row.get("turn_id", 0)))

    leakage_markers = Counter()
    non_provider_fields = Counter()
    non_provider_metadata_fields = Counter()
    allowed_provider_fields = {
        "request_id",
        "timestamp",
        "model",
        "messages",
        "tool_schemas",
        "token_count",
        "cache_bucket",
        "provider_metadata",
    }
    allowed_provider_metadata_fields = {
        "api_surface",
        "brokered",
        "stream",
    }
    for row in attack_rows:
        for field in row:
            if field not in allowed_provider_fields:
                non_provider_fields[field] += 1
        provider_metadata = row.get("provider_metadata", {})
        if isinstance(provider_metadata, dict):
            for field in provider_metadata:
                if field not in allowed_provider_metadata_fields:
                    non_provider_metadata_fields[field] += 1
        text = "\n".join(message.get("content", "") for message in row.get("messages", []))
        if "repository=" in text:
            leakage_markers["repository_field"] += 1
        if "/workspace/" in text:
            leakage_markers["workspace_path"] += 1
        if "[repair_context]" in text:
            leakage_markers["repair_context_marker"] += 1

    missing_truth = [row["request_id"] for row in attack_rows if row["request_id"] not in truth_by_request]
    summary: dict[str, Any] = {
        "dataset_dir": str(dataset_dir),
        "requests": len(attack_rows),
        "truth_rows": len(truth_rows),
        "provenance_rows": len(provenance_rows),
        "missing_truth_rows": len(missing_truth),
        "non_provider_attack_view_fields": non_provider_fields.most_common(),
        "non_provider_provider_metadata_fields": non_provider_metadata_fields.most_common(),
        "org_count": len(orgs),
        "project_count": len(projects),
        "workflow_count": len(workflow_turns),
        "user_count_excluding_missing": len(
            {key for key in users if key.lower() not in {"none", "null", "", "unknown"}}
        ),
        "top_orgs": orgs.most_common(20),
        "top_projects": projects.most_common(20),
        "repair_modes": repair_modes.most_common(),
        "repair_fields": repair_fields.most_common(),
        "role_counts": role_counts.most_common(),
        "leakage_markers": leakage_markers.most_common(),
        "messages_per_request": _stats(message_counts),
        "tokens_per_request": _stats(token_counts),
        "turns_per_workflow": _stats([len(turns) for turns in workflow_turns.values()]),
        "source_manifest": _read_json_if_exists(dataset_dir / "source_manifest.json"),
    }
    if output_path:
        if output_path.suffix == ".md":
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(_to_markdown(summary), encoding="utf-8")
        else:
            write_json(output_path, summary)
    return summary


def _stats(values: list[int]) -> dict[str, float]:
    if not values:
        return {"min": 0, "p50": 0, "p90": 0, "max": 0, "mean": 0}
    sorted_values = sorted(values)
    return {
        "min": float(sorted_values[0]),
        "p50": float(_percentile(sorted_values, 0.5)),
        "p90": float(_percentile(sorted_values, 0.9)),
        "max": float(sorted_values[-1]),
        "mean": sum(sorted_values) / len(sorted_values),
    }


def _percentile(sorted_values: list[int], q: float) -> int:
    idx = min(len(sorted_values) - 1, max(0, int(round((len(sorted_values) - 1) * q))))
    return sorted_values[idx]


def _read_json_if_exists(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _to_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Dataset Audit",
        "",
        f"- Dataset: `{summary['dataset_dir']}`",
        f"- Requests: {summary['requests']}",
        f"- Truth rows: {summary['truth_rows']}",
        f"- Provenance rows: {summary['provenance_rows']}",
        f"- Workflows: {summary['workflow_count']}",
        f"- Projects: {summary['project_count']}",
        f"- Orgs: {summary['org_count']}",
        f"- Users with ground truth: {summary['user_count_excluding_missing']}",
        "",
        "## Repair",
        "",
        f"- Repair modes: `{summary['repair_modes']}`",
        f"- Repair fields: `{summary['repair_fields']}`",
        f"- Leakage markers: `{summary['leakage_markers']}`",
        f"- Non-provider attack-view fields: `{summary['non_provider_attack_view_fields']}`",
        f"- Non-provider provider_metadata fields: `{summary['non_provider_provider_metadata_fields']}`",
        "",
        "## Shape",
        "",
        f"- Roles: `{summary['role_counts']}`",
        f"- Messages/request: `{summary['messages_per_request']}`",
        f"- Tokens/request: `{summary['tokens_per_request']}`",
        f"- Turns/workflow: `{summary['turns_per_workflow']}`",
        "",
        "## Top Orgs",
        "",
    ]
    lines.extend(f"- `{org}`: {count}" for org, count in summary["top_orgs"][:20])
    lines.extend(["", "## Top Projects", ""])
    lines.extend(f"- `{project}`: {count}" for project, count in summary["top_projects"][:20])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit converted attack/truth dataset files.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = audit_dataset(args.dataset_dir, args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
