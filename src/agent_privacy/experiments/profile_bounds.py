from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from agent_privacy.evaluation.profile import evaluate_profiles
from agent_privacy.io import read_jsonl
from agent_privacy.profiling.rule_profiler import profile_clusters
from agent_privacy.reporting import write_csv


RISK_LEVELS: dict[str, dict[str, Any]] = {
    "L1_technical": {
        "description": "General technical stack",
        "fields": {"languages", "frameworks", "package_managers", "build_tools"},
    },
    "L2_project": {
        "description": "Project/repository identifiers",
        "fields": {"repo_names"},
    },
    "L3_org_clues": {
        "description": "Organization-like or business clues",
        "fields": {"industries", "service_names"},
    },
    "L4_security_environment": {
        "description": "Security/deployment environment clues",
        "fields": {"internal_domains", "cloud_providers", "databases", "ci_cd_systems", "auth_systems", "security_clues"},
    },
    "L5_high_risk_secrets": {
        "description": "Secrets and credentials; excluded from Open-SWE profile claims",
        "fields": {"api_keys", "tokens", "connection_strings", "customer_data"},
    },
}


def profile_bounds(
    *,
    dataset_dir: Path,
    output_dir: Path,
    predictions_path: Path | None = None,
    method: str = "hybrid",
    level: str = "org",
    turn_ids: list[int] | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    attack_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    if turn_ids:
        allowed_turns = set(turn_ids)
        truth_rows = [row for row in truth_rows if int(row.get("turn_id", -1)) in allowed_turns]
        request_ids = {row["request_id"] for row in truth_rows}
        attack_rows = [row for row in attack_rows if row.get("request_id") in request_ids]
    truth_labels = _truth_labels(truth_rows, level)
    outputs: dict[str, str] = {}
    bound_rows = _evaluate_source(
        source="truth_cluster_upper_bound",
        rows=attack_rows,
        truth_rows=truth_rows,
        labels=truth_labels,
    )
    if predictions_path:
        predictions = _read_predictions(predictions_path)
        predicted_labels = predictions.get(method, {}).get(level, {})
        if predicted_labels:
            bound_rows.extend(
                _evaluate_source(
                    source=f"predicted_{method}_{level}",
                    rows=attack_rows,
                    truth_rows=truth_rows,
                    labels=predicted_labels,
                )
            )
    field_csv = output_dir / "open_swe_profile_bounds.csv"
    field_md = output_dir / "open_swe_profile_bounds.md"
    write_csv(field_csv, bound_rows)
    _write_markdown(field_md, bound_rows)
    risk_rows = _risk_rows(bound_rows)
    risk_csv = output_dir / "open_swe_profile_risk_levels.csv"
    risk_md = output_dir / "open_swe_profile_risk_levels.md"
    write_csv(risk_csv, risk_rows)
    _write_markdown(risk_md, risk_rows)
    outputs["profile_bounds"] = str(field_csv)
    outputs["profile_risk_levels"] = str(risk_csv)
    return outputs


def _evaluate_source(
    *,
    source: str,
    rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    labels: dict[str, str],
) -> list[dict[str, Any]]:
    profiles = profile_clusters(rows, labels)
    metrics = evaluate_profiles(profiles, truth_rows, labels)
    out = []
    for row in metrics:
        out.append({"source": source, **row})
    return out


def _truth_labels(truth_rows: list[dict[str, Any]], level: str) -> dict[str, str]:
    field = {"session": "workflow_id", "project": "project_id", "org": "org_id"}[level]
    labels = {}
    for row in truth_rows:
        value = row.get(field)
        if value is None or str(value).lower() in {"", "none", "null", "unknown", "n/a"}:
            continue
        labels[row["request_id"]] = str(value)
    return labels


def _read_predictions(path: Path) -> dict[str, dict[str, dict[str, str]]]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _risk_rows(field_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    sources = sorted({row["source"] for row in field_rows})
    for source in sources:
        source_rows = [row for row in field_rows if row["source"] == source and row["field"] != "__micro__"]
        for risk_level, spec in RISK_LEVELS.items():
            fields = set(spec["fields"])
            counts = Counter()
            predicted_values = 0
            evidenced_values = 0
            covered_fields = []
            for row in source_rows:
                if row["field"] not in fields:
                    continue
                covered_fields.append(row["field"])
                counts["tp"] += int(row.get("tp", 0))
                counts["fp"] += int(row.get("fp", 0))
                counts["fn"] += int(row.get("fn", 0))
                predicted_values += int(row.get("predicted_values", 0))
                evidenced_values += int(row.get("evidenced_values", 0))
            precision = _ratio(counts["tp"], counts["tp"] + counts["fp"])
            recall = _ratio(counts["tp"], counts["tp"] + counts["fn"])
            rows.append(
                {
                    "source": source,
                    "risk_level": risk_level,
                    "description": spec["description"],
                    "fields": ",".join(sorted(fields)),
                    "covered_fields": ",".join(sorted(covered_fields)),
                    "precision": precision,
                    "recall": recall,
                    "f1": _f1(precision, recall),
                    "tp": counts["tp"],
                    "fp": counts["fp"],
                    "fn": counts["fn"],
                    "predicted_values": predicted_values,
                    "evidence_coverage": _ratio(evidenced_values, predicted_values),
                }
            )
    return rows


def _ratio(num: int, den: int) -> float:
    return num / den if den else 0.0


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0])
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format(row.get(header)) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile truth-cluster bounds and risk levels.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--method", default="hybrid")
    parser.add_argument("--level", choices=["session", "project", "org"], default="org")
    parser.add_argument("--turn-ids", type=int, nargs="*")
    args = parser.parse_args()
    print(
        profile_bounds(
            dataset_dir=args.dataset_dir,
            output_dir=args.output_dir,
            predictions_path=args.predictions,
            method=args.method,
            level=args.level,
            turn_ids=args.turn_ids,
        )
    )


if __name__ == "__main__":
    main()
