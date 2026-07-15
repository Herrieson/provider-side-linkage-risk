from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_privacy.attacks.pipeline import group_by_label
from agent_privacy.io import iter_jsonl
from agent_privacy.reporting import write_csv


DOMAIN_RE = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:internal|local|prod|corp)\b")
WORKSPACE_RE = re.compile(r"/workspace/([A-Za-z0-9_.-]+)__([A-Za-z0-9_.-]+)")
HOME_RE = re.compile(r"/home/([A-Za-z0-9_.-]+)")
PROFILE_TEXT_WINDOW_CHARS = 24_000


@dataclass(frozen=True)
class ProfileRun:
    overlay_level: str
    snapshot: str
    dataset_dir: Path
    result_dir: Path
    method: str
    levels: tuple[str, ...]


RUNS = [
    ProfileRun(
        "U3",
        "first_1000_requests",
        Path("artifacts/datasets/open_swe_user_overlay_u3_mixed_1000_snapshots/first_1000_requests"),
        Path("results/open_swe_user_overlay_u3_first_1000_m0_ablation"),
        "hybrid",
        ("org", "project", "user"),
    ),
    ProfileRun(
        "U4",
        "first_1000_requests",
        Path("artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000_snapshots/first_1000_requests"),
        Path("results/open_swe_user_overlay_u4_first_1000_m0_ablation"),
        "hybrid",
        ("org", "project", "user"),
    ),
    ProfileRun(
        "U3",
        "first_4000_requests",
        Path("artifacts/datasets/open_swe_user_overlay_u3_mixed_1000_snapshots/first_4000_requests"),
        Path("results/open_swe_user_overlay_u3_first_4000_provider_lowcost_streamed"),
        "provider_lowcost",
        ("org", "project", "user"),
    ),
    ProfileRun(
        "U4",
        "first_4000_requests",
        Path("artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000_snapshots/first_4000_requests"),
        Path("results/open_swe_user_overlay_u4_first_4000_provider_lowcost_streamed"),
        "provider_lowcost",
        ("org", "project", "user"),
    ),
]


def summarize_user_overlay_profiles(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for run in RUNS:
        if not (run.result_dir / "M0" / "predictions.json").exists():
            continue
        rows.extend(_summarize_run(run))
    csv_path = output_dir / "open_swe_user_overlay_profile_reconstruction.csv"
    md_path = output_dir / "open_swe_user_overlay_profile_reconstruction.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return {"profile_reconstruction": str(csv_path), "rows": str(len(rows))}


def _summarize_run(run: ProfileRun) -> list[dict[str, Any]]:
    profiles = _read_profiles(run.dataset_dir)
    truth_rows = list(iter_jsonl(run.dataset_dir / "ground_truth.jsonl"))
    truth_by_id = {row["request_id"]: row for row in truth_rows}
    fields_by_id = _read_fields_by_id(run.dataset_dir / "attack_view.jsonl")
    predictions = json.loads((run.result_dir / "M0" / "predictions.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for level in run.levels:
        labels = predictions.get(run.method, {}).get(level)
        if not labels:
            continue
        rows.extend(_evaluate_level(run, level, labels, fields_by_id, truth_by_id, profiles))
    return rows


def _evaluate_level(
    run: ProfileRun,
    level: str,
    labels: dict[str, str],
    fields_by_id: dict[str, dict[str, set[str]]],
    truth_by_id: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    totals: dict[str, Counter[str]] = defaultdict(Counter)
    evaluated_clusters = 0
    for request_ids in group_by_label(labels).values():
        usable = [rid for rid in request_ids if rid in fields_by_id and rid in truth_by_id]
        if len(usable) < 2:
            continue
        truth_id = _majority_truth_id(level, usable, truth_by_id)
        if truth_id is None:
            continue
        predicted = _merge_fields(fields_by_id[rid] for rid in usable)
        expected = _expected_profile(level, truth_id, profiles)
        if not expected:
            continue
        evaluated_clusters += 1
        for field in sorted(set(predicted) | set(expected)):
            pred_values = predicted.get(field, set())
            truth_values = expected.get(field, set())
            totals[field]["tp"] += len(pred_values & truth_values)
            totals[field]["fp"] += len(pred_values - truth_values)
            totals[field]["fn"] += len(truth_values - pred_values)

    rows = [
        _metric_row(run, level, field, counts, evaluated_clusters)
        for field, counts in sorted(totals.items())
    ]
    micro = Counter()
    for counts in totals.values():
        micro.update(counts)
    rows.append(_metric_row(run, level, "__micro__", micro, evaluated_clusters))
    return rows


def _extract_profile_fields(text: str) -> dict[str, set[str]]:
    lower = _bounded_text(text.lower(), PROFILE_TEXT_WINDOW_CHARS)
    out: dict[str, set[str]] = defaultdict(set)
    for language in ["python", "javascript", "typescript", "go", "rust", "java"]:
        if re.search(rf"\b{language}\b", lower):
            out["languages"].add(language)
    for manager in ["pip", "npm", "pnpm", "go", "cargo", "maven"]:
        if re.search(rf"\b{re.escape(manager)}\b", lower):
            out["package_managers"].add(manager)
    build_patterns = {
        "pytest -q": r"\bpytest(?:\s+-q)?\b",
        "npm test": r"\bnpm\s+test\b",
        "pnpm test": r"\bpnpm\s+test\b",
        "go test ./...": r"\bgo\s+test\b",
        "cargo test": r"\bcargo\s+test\b",
        "mvn test": r"\bmvn\s+test\b",
    }
    for value, pattern in build_patterns.items():
        if re.search(pattern, lower):
            out["build_tools"].add(value)
    for domain in DOMAIN_RE.findall(lower):
        out["internal_domains"].add(domain)
    for org_alias, project_alias in WORKSPACE_RE.findall(lower):
        out["org_aliases"].add(org_alias)
        out["project_aliases"].add(project_alias)
    for home_alias in HOME_RE.findall(lower):
        out["home_aliases"].add("/home/" + home_alias)
    for service in re.findall(r"\bservice=([a-z][a-z0-9_.-]{2,})\b", lower):
        out["service_names"].add(service)
    return dict(out)


def _expected_profile(
    level: str, truth_id: str, profiles: dict[str, dict[str, Any]]
) -> dict[str, set[str]]:
    if level == "org":
        org = profiles["orgs"].get(truth_id, {})
        return {
            "org_aliases": _set(org.get("alias")),
            "languages": _set(org.get("languages")),
            "package_managers": _set(org.get("package_managers")),
            "build_tools": _set(org.get("build_tools")),
            "internal_domains": _set(org.get("internal_domains")),
            "service_names": _set(org.get("service_names")),
        }
    if level == "project":
        project = profiles["projects"].get(truth_id, {})
        return {
            "project_aliases": _set(project.get("alias")),
            "languages": _set(project.get("language")),
            "package_managers": _set(project.get("package_manager")),
            "build_tools": _set(project.get("build_tool")),
            "internal_domains": _set(project.get("internal_domain")),
            "service_names": _set(project.get("service_name")),
        }
    user = profiles["users"].get(truth_id, {})
    return {
        "home_aliases": _set(user.get("home_alias")),
        "build_tools": _set(user.get("tool_preferences")),
    }


def _majority_truth_id(
    level: str, request_ids: list[str], truth_by_id: dict[str, dict[str, Any]]
) -> str | None:
    field = {"org": "org_id", "project": "project_id", "user": "user_id"}[level]
    counts = Counter(str(truth_by_id[rid].get(field, "")) for rid in request_ids if rid in truth_by_id)
    return counts.most_common(1)[0][0] if counts else None


def _metric_row(
    run: ProfileRun,
    level: str,
    field: str,
    counts: Counter[str],
    evaluated_clusters: int,
) -> dict[str, Any]:
    precision = _ratio(counts["tp"], counts["tp"] + counts["fp"])
    recall = _ratio(counts["tp"], counts["tp"] + counts["fn"])
    return {
        "overlay_level": run.overlay_level,
        "snapshot": run.snapshot,
        "method": run.method,
        "profile_level": level,
        "field": field,
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
        "tp": counts["tp"],
        "fp": counts["fp"],
        "fn": counts["fn"],
        "evaluated_clusters": evaluated_clusters,
    }


def _read_profiles(dataset_dir: Path) -> dict[str, dict[str, Any]]:
    manifest = json.loads((dataset_dir / "source_manifest.json").read_text(encoding="utf-8"))
    base_dir = dataset_dir
    if "snapshots" in dataset_dir.name or dataset_dir.name.startswith("first_"):
        # Snapshots do not duplicate profiles.json; it lives in the base dataset directory.
        parent = dataset_dir.parent
        if parent.name.endswith("_snapshots"):
            base_dir = parent.with_name(parent.name.removesuffix("_snapshots"))
    profiles_path = base_dir / "profiles.json"
    if not profiles_path.exists() and "config_path" in manifest:
        profiles_path = dataset_dir / "profiles.json"
    return json.loads(profiles_path.read_text(encoding="utf-8"))


def _read_fields_by_id(path: Path) -> dict[str, dict[str, set[str]]]:
    out = {}
    for row in iter_jsonl(path):
        parts = []
        for message in row.get("messages", []):
            parts.append(str(message.get("content", "")))
        out[row["request_id"]] = _extract_profile_fields("\n".join(parts))
    return out


def _merge_fields(items: Any) -> dict[str, set[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for fields in items:
        for field, values in fields.items():
            merged[field].update(values)
    return dict(merged)


def _bounded_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n" + text[-half:]


def _set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return {str(item).lower() for item in value}
    return {str(value).lower()}


def _ratio(num: int, den: int) -> float:
    return num / den if den else 0.0


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = [
        "overlay_level",
        "snapshot",
        "method",
        "profile_level",
        "field",
        "precision",
        "recall",
        "f1",
        "evaluated_clusters",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format(row.get(header, "")) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Dataset B profile reconstruction.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(json.dumps(summarize_user_overlay_profiles(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
