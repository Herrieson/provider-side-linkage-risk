from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.experiments.summarize_open_swe_entity_validity import _read_direct_anchors
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_12000_requests")
DEFAULT_DEVELOPMENT_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000_sample100")
OUTPUT_BASE = "open_swe_direct_exposure_audit"


def summarize_direct_exposure(
    *,
    dataset_dir: Path = DEFAULT_DATASET,
    development_dataset_dir: Path = DEFAULT_DEVELOPMENT_DATASET,
) -> list[dict[str, Any]]:
    development_workflows = {
        str(row["workflow_id"])
        for row in read_jsonl(development_dataset_dir / "ground_truth.jsonl")
    }
    truth_rows = [
        row
        for row in read_jsonl(dataset_dir / "ground_truth.jsonl")
        if str(row["workflow_id"]) not in development_workflows
    ]
    request_ids = {str(row["request_id"]) for row in truth_rows}
    anchors = _read_direct_anchors(dataset_dir / "attack_view.jsonl", request_ids)
    rows: list[dict[str, Any]] = []
    for level, truth_field, prefix in (
        ("project", "project_id", "repo_full:"),
        ("owner", "org_id", "repo_owner:"),
    ):
        rows.append(
            _level_exposure(
                truth_rows=truth_rows,
                anchors=anchors,
                level=level,
                truth_field=truth_field,
                prefix=prefix,
            )
        )
    return rows


def _level_exposure(
    *,
    truth_rows: list[dict[str, Any]],
    anchors: dict[str, set[str]],
    level: str,
    truth_field: str,
    prefix: str,
) -> dict[str, Any]:
    workflows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    entities: dict[str, list[dict[str, Any]]] = defaultdict(list)
    exposed_requests = 0
    exactly_recoverable_requests = 0
    ambiguous_requests = 0
    incorrect_requests = 0
    for row in truth_rows:
        request_id = str(row["request_id"])
        workflow_id = str(row["workflow_id"])
        truth_value = str(row[truth_field]).lower()
        values = {value.removeprefix(prefix) for value in anchors[request_id] if value.startswith(prefix)}
        workflows[workflow_id].append(row)
        entities[truth_value].append(row)
        if values:
            exposed_requests += 1
        if truth_value in values:
            exactly_recoverable_requests += 1
        elif values:
            incorrect_requests += 1
        if len(values) > 1:
            ambiguous_requests += 1

    exposed_workflows = 0
    fully_exposed_workflows = 0
    for members in workflows.values():
        flags = []
        for row in members:
            truth_value = str(row[truth_field]).lower()
            values = {
                value.removeprefix(prefix)
                for value in anchors[str(row["request_id"])]
                if value.startswith(prefix)
            }
            flags.append(truth_value in values)
        exposed_workflows += any(flags)
        fully_exposed_workflows += all(flags)

    exposed_entities = 0
    for truth_value, members in entities.items():
        exposed_entities += any(
            truth_value
            in {
                value.removeprefix(prefix)
                for value in anchors[str(row["request_id"])]
                if value.startswith(prefix)
            }
            for row in members
        )

    requests = len(truth_rows)
    workflow_count = len(workflows)
    entity_count = len(entities)
    return {
        "level": level,
        "requests": requests,
        "workflows": workflow_count,
        "entities": entity_count,
        "request_anchor_coverage": exposed_requests / requests,
        "request_exact_recoverability": exactly_recoverable_requests / requests,
        "request_ambiguity_rate": ambiguous_requests / requests,
        "request_incorrect_anchor_rate": incorrect_requests / requests,
        "workflow_any_turn_recoverability": exposed_workflows / workflow_count,
        "workflow_all_turn_recoverability": fully_exposed_workflows / workflow_count,
        "entity_any_request_recoverability": exposed_entities / entity_count,
    }


def write_direct_exposure_tables(
    output_dir: Path,
    *,
    dataset_dir: Path = DEFAULT_DATASET,
    development_dataset_dir: Path = DEFAULT_DEVELOPMENT_DATASET,
) -> dict[str, str]:
    rows = summarize_direct_exposure(
        dataset_dir=dataset_dir,
        development_dataset_dir=development_dataset_dir,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
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
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"csv": str(csv_path), "markdown": str(md_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit direct Open-SWE repository/owner exposure.")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--development-dataset-dir", type=Path, default=DEFAULT_DEVELOPMENT_DATASET
    )
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(
        write_direct_exposure_tables(
            args.output_dir,
            dataset_dir=args.dataset_dir,
            development_dataset_dir=args.development_dataset_dir,
        )
    )


if __name__ == "__main__":
    main()
