from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agent_privacy.data.trace_transform import (
    transform_trace_rows,
    validate_trace_preservation,
)
from agent_privacy.evaluation.fidelity import fidelity_audit
from agent_privacy.io import read_jsonl, write_json, write_jsonl


def audit_transformation(dataset_dir: Path, output_dir: Path) -> dict[str, Any]:
    rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    transformed, lineage = transform_trace_rows(rows)
    preservation = validate_trace_preservation(rows, transformed, lineage)
    distribution = fidelity_audit(rows, transformed)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "attack_view.jsonl", transformed)
    write_jsonl(output_dir / "request_lineage.jsonl", (item.to_dict() for item in lineage))
    report = {
        "source_dataset": str(dataset_dir),
        "output_dataset": str(output_dir),
        "fidelity_level": "F0",
        "transformation": "trace_preserving_span_pseudonymization",
        "preservation": preservation,
        "distribution": distribution,
        "claim_boundary": (
            "This controlled intervention preserves observed Agent event structure; it is not "
            "claimed to be captured enterprise provider traffic."
        ),
    }
    write_json(output_dir / "fidelity_audit.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a trace-preserving reconstruction.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            audit_transformation(args.dataset_dir, args.output_dir),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
