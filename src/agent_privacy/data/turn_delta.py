from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.io import read_jsonl, write_json, write_jsonl


def build_turn_delta_dataset(
    dataset_dir: Path,
    output_dir: Path,
    turn_ids: list[int],
) -> dict[str, Any]:
    attack_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    provenance_path = dataset_dir / "request_provenance.jsonl"
    provenance_rows = read_jsonl(provenance_path) if provenance_path.exists() else []

    truth_by_request = {row["request_id"]: row for row in truth_rows}
    provenance_by_request = {row["request_id"]: row for row in provenance_rows}
    rows_by_workflow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for attack_row in attack_rows:
        truth = truth_by_request.get(attack_row["request_id"])
        if truth is None:
            continue
        turn_id = int(truth.get("turn_id", -1))
        if turn_id in turn_ids:
            rows_by_workflow[str(truth["workflow_id"])].append(attack_row)

    selected_attack: list[dict[str, Any]] = []
    selected_truth: list[dict[str, Any]] = []
    selected_provenance: list[dict[str, Any]] = []
    for workflow_id in sorted(rows_by_workflow):
        previous_message_count = 0
        for attack_row in sorted(
            rows_by_workflow[workflow_id],
            key=lambda row: int(truth_by_request[row["request_id"]].get("turn_id", 0)),
        ):
            out = dict(attack_row)
            messages = list(out.get("messages", []))
            delta_messages = messages[previous_message_count:]
            if not delta_messages and messages:
                delta_messages = [messages[-1]]
            out["messages"] = delta_messages
            out["token_count"] = _token_count(delta_messages)
            delta_from = previous_message_count
            delta_to = len(messages)
            previous_message_count = len(messages)
            selected_attack.append(out)
            selected_truth.append(truth_by_request[out["request_id"]])
            provenance = dict(provenance_by_request.get(out["request_id"], {}))
            provenance["request_id"] = out["request_id"]
            provenance["view"] = "turn_delta"
            provenance["delta_from_message_index"] = delta_from
            provenance["delta_to_message_index"] = delta_to
            selected_provenance.append(provenance)

    selected = list(zip(selected_attack, selected_truth, strict=True))
    selected.sort(key=lambda pair: (pair[0]["timestamp"], pair[0]["request_id"]))
    selected_attack = [pair[0] for pair in selected]
    selected_truth = [pair[1] for pair in selected]
    if selected_provenance:
        provenance_by_request = {row["request_id"]: row for row in selected_provenance}
        selected_provenance = [
            provenance_by_request[row["request_id"]]
            for row in selected_attack
            if row["request_id"] in provenance_by_request
        ]

    write_jsonl(output_dir / "attack_view.jsonl", selected_attack)
    write_jsonl(output_dir / "ground_truth.jsonl", selected_truth)
    write_jsonl(output_dir / "request_provenance.jsonl", selected_provenance)
    manifest = {
        "source_dataset_dir": str(dataset_dir),
        "view": "turn_delta",
        "turn_ids": turn_ids,
        "requests": len(selected_attack),
        "truth": len(selected_truth),
        "workflows": len(rows_by_workflow),
        "notes": [
            "Messages are replaced with deltas between selected turns.",
            "This view is for ablation only and is not a raw provider log.",
            "Ground truth labels are preserved only for evaluation.",
        ],
    }
    write_json(output_dir / "source_manifest.json", manifest)
    return manifest


def _token_count(messages: list[dict[str, Any]]) -> int:
    return sum(len(str(message.get("content", "")).split()) for message in messages)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a turn-delta dataset view.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--turn-ids", type=int, nargs="+", required=True)
    args = parser.parse_args()
    summary = build_turn_delta_dataset(args.dataset_dir, args.output_dir, args.turn_ids)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
