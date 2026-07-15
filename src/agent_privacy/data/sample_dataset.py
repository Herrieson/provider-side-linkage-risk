from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from agent_privacy.io import read_jsonl, write_json, write_jsonl


def sample_dataset_by_workflow(
    dataset_dir: Path,
    output_dir: Path,
    limit_workflows: int,
    sample_mode: str = "first",
    seed: int = 7,
) -> dict[str, Any]:
    attack_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    provenance_path = dataset_dir / "request_provenance.jsonl"
    provenance_rows = read_jsonl(provenance_path) if provenance_path.exists() else []

    truth_by_request = {row["request_id"]: row for row in truth_rows}
    provenance_by_request = {row["request_id"]: row for row in provenance_rows}
    workflow_ids = _workflow_ids(truth_rows)
    if sample_mode == "first":
        selected_ids = workflow_ids[:limit_workflows]
    elif sample_mode == "reservoir":
        selected_ids = _reservoir_sample(workflow_ids, limit_workflows, seed)
    else:
        raise ValueError(f"unknown sample_mode: {sample_mode}")
    selected_workflows = set(selected_ids)

    selected_attack = [
        row
        for row in attack_rows
        if str(truth_by_request[row["request_id"]]["workflow_id"]) in selected_workflows
    ]
    selected_attack.sort(
        key=lambda row: (
            selected_ids.index(str(truth_by_request[row["request_id"]]["workflow_id"])),
            int(truth_by_request[row["request_id"]].get("turn_id", 0)),
            row["request_id"],
        )
    )
    selected_truth = [truth_by_request[row["request_id"]] for row in selected_attack]
    selected_provenance = [
        provenance_by_request[row["request_id"]]
        for row in selected_attack
        if row["request_id"] in provenance_by_request
    ]

    write_jsonl(output_dir / "attack_view.jsonl", selected_attack)
    write_jsonl(output_dir / "ground_truth.jsonl", selected_truth)
    if selected_provenance:
        write_jsonl(output_dir / "request_provenance.jsonl", selected_provenance)

    manifest = {
        "source_dataset_dir": str(dataset_dir),
        "sample": f"{sample_mode}_workflows",
        "sample_mode": sample_mode,
        "seed": seed,
        "source_workflows": len(workflow_ids),
        "limit_workflows": limit_workflows,
        "workflows": len(selected_workflows),
        "requests": len(selected_attack),
        "truth": len(selected_truth),
        "provenance": len(selected_provenance),
    }
    write_json(output_dir / "source_manifest.json", manifest)
    return manifest


def _workflow_ids(truth_rows: list[dict[str, Any]]) -> list[str]:
    workflow_ids: list[str] = []
    workflow_set: set[str] = set()
    for truth in truth_rows:
        workflow_id = str(truth["workflow_id"])
        if workflow_id not in workflow_set:
            workflow_set.add(workflow_id)
            workflow_ids.append(workflow_id)
    return workflow_ids


def _reservoir_sample(values: list[str], limit: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    reservoir: list[str] = []
    for idx, value in enumerate(values, start=1):
        if len(reservoir) < limit:
            reservoir.append(value)
            continue
        replace_idx = rng.randint(0, idx - 1)
        if replace_idx < limit:
            reservoir[replace_idx] = value
    return sorted(reservoir, key=values.index)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample a dataset by workflow id.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit-workflows", type=int, required=True)
    parser.add_argument("--sample-mode", choices=["first", "reservoir"], default="first")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    summary = sample_dataset_by_workflow(
        args.dataset_dir,
        args.output_dir,
        args.limit_workflows,
        sample_mode=args.sample_mode,
        seed=args.seed,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
