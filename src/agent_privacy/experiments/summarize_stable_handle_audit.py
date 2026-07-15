from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from agent_privacy.experiments.summarize_open_swe_entity_validity import (
    _read_direct_anchors,
)
from agent_privacy.features.extract import extract_stable_content_handles
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_OPEN_SWE_DIR = Path(
    "artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_12000_requests"
)
DEFAULT_OPEN_SWE_DEVELOPMENT_DIR = Path(
    "artifacts/datasets/open_swe_traces_raw_1000_sample100"
)
DEFAULT_TAU_DIR = Path("artifacts/datasets/tau_bench_historical_sample200")
DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "cross_domain_stable_handle_audit"


def summarize_stable_handles(
    *,
    open_swe_dir: Path = DEFAULT_OPEN_SWE_DIR,
    open_swe_development_dir: Path = DEFAULT_OPEN_SWE_DEVELOPMENT_DIR,
    tau_dir: Path = DEFAULT_TAU_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, str]:
    rows = _open_swe_rows(open_swe_dir, open_swe_development_dir)
    rows.extend(_tau_rows(tau_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path)}


def _open_swe_rows(dataset_dir: Path, development_dir: Path) -> list[dict[str, Any]]:
    development_workflows = {
        str(row["workflow_id"])
        for row in read_jsonl(development_dir / "ground_truth.jsonl")
    }
    truth_rows = [
        row
        for row in read_jsonl(dataset_dir / "ground_truth.jsonl")
        if str(row["workflow_id"]) not in development_workflows
    ]
    request_ids = {str(row["request_id"]) for row in truth_rows}
    anchors = _read_direct_anchors(dataset_dir / "attack_view.jsonl", request_ids)
    return [
        _family_row(
            dataset="Open-SWE",
            family="repository_namespace",
            level="project",
            truth_rows=truth_rows,
            anchors_by_request={
                request_id: {
                    anchor for anchor in values if anchor.startswith("repo_full:")
                }
                for request_id, values in anchors.items()
            },
            entity_field="project_id",
        ),
        _family_row(
            dataset="Open-SWE",
            family="owner_namespace",
            level="owner",
            truth_rows=truth_rows,
            anchors_by_request={
                request_id: {
                    anchor for anchor in values if anchor.startswith("repo_owner:")
                }
                for request_id, values in anchors.items()
            },
            entity_field="org_id",
        ),
    ]


def _tau_rows(dataset_dir: Path) -> list[dict[str, Any]]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    attack_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    handles = {
        str(row["request_id"]): set(extract_stable_content_handles(row))
        for row in attack_rows
    }
    specs = (
        ("identity_handle", "user", "stable_user:"),
        ("process_handle", "user-associated process", "stable_project:"),
        ("shared_resource_handle", "context", "stable_context:"),
    )
    return [
        _family_row(
            dataset="tau-bench",
            family=family,
            level=level,
            truth_rows=truth_rows,
            anchors_by_request={
                request_id: {value for value in values if value.startswith(prefix)}
                for request_id, values in handles.items()
            },
            entity_field="user_id",
        )
        for family, level, prefix in specs
    ]


def _family_row(
    *,
    dataset: str,
    family: str,
    level: str,
    truth_rows: list[dict[str, Any]],
    anchors_by_request: dict[str, set[str]],
    entity_field: str,
) -> dict[str, Any]:
    records: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"requests": set(), "workflows": set(), "entities": set()}
    )
    covered = 0
    for row in truth_rows:
        request_id = str(row["request_id"])
        values = anchors_by_request.get(request_id, set())
        covered += bool(values)
        for value in values:
            records[value]["requests"].add(request_id)
            records[value]["workflows"].add(str(row["workflow_id"]))
            records[value]["entities"].add(str(row.get(entity_field)))
    unique = len(records)
    recurrent = sum(len(record["requests"]) > 1 for record in records.values())
    cross_workflow = sum(len(record["workflows"]) > 1 for record in records.values())
    ambiguous = sum(len(record["entities"]) > 1 for record in records.values())
    return {
        "dataset": dataset,
        "family": family,
        "level": level,
        "requests": len(truth_rows),
        "request_coverage": covered / len(truth_rows) if truth_rows else 0.0,
        "unique_handles": unique,
        "recurrent_handle_rate": recurrent / unique if unique else 0.0,
        "cross_workflow_handle_rate": cross_workflow / unique if unique else 0.0,
        "cross_entity_ambiguity_rate": ambiguous / unique if unique else 0.0,
        "median_requests_per_handle": median(
            len(record["requests"]) for record in records.values()
        )
        if records
        else 0.0,
    }


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = list(rows[0]) if rows else []
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                f"{row[header]:.3f}" if isinstance(row[header], float) else str(row[header])
                for header in headers
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open-swe-dir", type=Path, default=DEFAULT_OPEN_SWE_DIR)
    parser.add_argument(
        "--open-swe-development-dir",
        type=Path,
        default=DEFAULT_OPEN_SWE_DEVELOPMENT_DIR,
    )
    parser.add_argument("--tau-dir", type=Path, default=DEFAULT_TAU_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(
        summarize_stable_handles(
            open_swe_dir=args.open_swe_dir,
            open_swe_development_dir=args.open_swe_development_dir,
            tau_dir=args.tau_dir,
            output_dir=args.output_dir,
        )
    )


if __name__ == "__main__":
    main()
