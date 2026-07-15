from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agent_privacy.io import read_jsonl, write_json, write_jsonl


def build_time_snapshots(
    dataset_dir: Path,
    output_dir: Path,
    *,
    request_counts: list[int] | None = None,
    time_cutoffs: list[str] | None = None,
) -> dict[str, Any]:
    attack_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    provenance_path = dataset_dir / "request_provenance.jsonl"
    provenance_rows = read_jsonl(provenance_path) if provenance_path.exists() else []

    truth_by_request = {row["request_id"]: row for row in truth_rows}
    provenance_by_request = {row["request_id"]: row for row in provenance_rows}
    sorted_attack = sorted(attack_rows, key=lambda row: (row["timestamp"], row["request_id"]))

    snapshots: list[dict[str, Any]] = []
    for count in request_counts or []:
        selected = sorted_attack[:count]
        label = f"first_{count}_requests"
        snapshots.append(_write_snapshot(output_dir / label, label, selected, truth_by_request, provenance_by_request))

    for cutoff in time_cutoffs or []:
        selected = [row for row in sorted_attack if str(row["timestamp"]) <= cutoff]
        safe_cutoff = cutoff.replace(":", "").replace("-", "").replace("Z", "z")
        label = f"through_{safe_cutoff}"
        snapshots.append(_write_snapshot(output_dir / label, label, selected, truth_by_request, provenance_by_request))

    manifest = {
        "source_dataset_dir": str(dataset_dir),
        "snapshot_type": "cumulative_provider_view",
        "source_requests": len(attack_rows),
        "snapshots": snapshots,
    }
    write_json(output_dir / "snapshot_manifest.json", manifest)
    return manifest


def _write_snapshot(
    output_dir: Path,
    label: str,
    attack_rows: list[dict[str, Any]],
    truth_by_request: dict[str, dict[str, Any]],
    provenance_by_request: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    truth_rows = [truth_by_request[row["request_id"]] for row in attack_rows if row["request_id"] in truth_by_request]
    provenance_rows = [
        provenance_by_request[row["request_id"]]
        for row in attack_rows
        if row["request_id"] in provenance_by_request
    ]
    write_jsonl(output_dir / "attack_view.jsonl", attack_rows)
    write_jsonl(output_dir / "ground_truth.jsonl", truth_rows)
    if provenance_rows:
        write_jsonl(output_dir / "request_provenance.jsonl", provenance_rows)
    snapshot_manifest = {
        "label": label,
        "requests": len(attack_rows),
        "truth": len(truth_rows),
        "provenance": len(provenance_rows),
        "start_timestamp": attack_rows[0]["timestamp"] if attack_rows else None,
        "end_timestamp": attack_rows[-1]["timestamp"] if attack_rows else None,
        "workflow_count": len({row.get("workflow_id") for row in truth_rows}),
        "project_count": len({row.get("project_id") for row in truth_rows}),
        "org_count": len({row.get("org_id") for row in truth_rows}),
        "notes": [
            "Snapshot preserves the provider-visible attack_view schema.",
            "Ground truth and provenance are copied only for evaluation and audit.",
        ],
    }
    write_json(output_dir / "source_manifest.json", snapshot_manifest)
    return {"path": str(output_dir), **snapshot_manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cumulative time snapshots from a dataset.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--request-counts", type=int, nargs="*")
    parser.add_argument("--time-cutoffs", nargs="*")
    args = parser.parse_args()
    summary = build_time_snapshots(
        args.dataset_dir,
        args.output_dir,
        request_counts=args.request_counts,
        time_cutoffs=args.time_cutoffs,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
