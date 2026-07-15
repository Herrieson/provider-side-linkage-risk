from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from agent_privacy.reporting import write_csv


SNAPSHOTS = [
    ("first_1000", "artifacts/datasets/open_swe_traces_raw_1000_snapshots_sample100/first_1000_requests", "results/open_swe_provider_lowcost_longitudinal_first_1000"),
    ("first_4000", "artifacts/datasets/open_swe_traces_raw_1000_snapshots_sample100/first_4000_requests", "results/open_swe_provider_lowcost_longitudinal_first_4000"),
    ("first_8000", "artifacts/datasets/open_swe_traces_raw_1000_snapshots_sample100/first_8000_requests", "results/open_swe_provider_lowcost_longitudinal_first_8000"),
    ("first_12000", "artifacts/datasets/open_swe_traces_raw_1000_snapshots_sample100/first_12000_requests", "results/open_swe_provider_lowcost_longitudinal_first_12000"),
]
FULL_TURN_SNAPSHOTS = [
    (
        "full_turns_first_1000",
        1000,
        "artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_1000_requests",
        "results/open_swe_provider_lowcost_longitudinal_full_first_1000_turns",
    ),
    (
        "full_turns_first_4000",
        4000,
        "artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_4000_requests",
        "results/open_swe_provider_lowcost_longitudinal_full_first_4000_turns",
    ),
    (
        "full_turns_first_8000",
        8000,
        "artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_8000_requests",
        "results/open_swe_provider_lowcost_longitudinal_full_first_8000_turns",
    ),
    (
        "full_turns_first_12000",
        12000,
        "artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_12000_requests",
        "results/open_swe_provider_lowcost_longitudinal_full_first_12000_turns",
    ),
]


def summarize_longitudinal() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for label, dataset_dir, result_dir in SNAPSHOTS:
        dataset_path = Path(dataset_dir)
        result_path = Path(result_dir)
        manifest = _read_json(dataset_path / "source_manifest.json")
        cluster_rows = _read_csv(result_path / "clustering_metrics_all.csv")
        workflow_rows = _read_csv(result_path / "workflow_reconstruction_metrics_all.csv")
        ordering_rows = _read_csv(result_path / "ordering_metrics_all.csv")
        for feature_ablation in _ordered_unique(row["feature_ablation"] for row in cluster_rows):
            item: dict[str, Any] = {
                "snapshot": label,
                "source_requests": _snapshot_source_requests(label),
                "sample_workflows": int(manifest.get("workflows", 0)),
                "sample_requests": int(manifest.get("requests", 0)),
                "feature_ablation": feature_ablation,
            }
            for level in ["session", "project", "org"]:
                metric = _find(cluster_rows, level=level, feature_ablation=feature_ablation)
                item[f"{level}_f1"] = _float(metric.get("pairwise_f1"))
                item[f"{level}_purity"] = _float(metric.get("purity"))
            workflow = _find(workflow_rows, feature_ablation=feature_ablation)
            item["reconstructed_workflows"] = _int(workflow.get("workflows"))
            item["workflow_purity"] = _float(workflow.get("mean_purity"))
            item["workflow_pairwise_order_accuracy"] = _float(
                workflow.get("mean_pairwise_order_accuracy")
            )
            ordering = _find(ordering_rows, feature_ablation=feature_ablation)
            item["pure_ordered_clusters"] = _int(ordering.get("pure_session_clusters"))
            item["ordered_pairs"] = _int(ordering.get("ordered_pairs"))
            out.append(item)
    return out


def write_longitudinal_tables(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = summarize_longitudinal()
    csv_path = output_dir / "open_swe_provider_lowcost_longitudinal.csv"
    md_path = output_dir / "open_swe_provider_lowcost_longitudinal.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    full_rows = summarize_full_turn_longitudinal()
    full_csv_path = output_dir / "open_swe_provider_lowcost_longitudinal_full_turns.csv"
    full_md_path = output_dir / "open_swe_provider_lowcost_longitudinal_full_turns.md"
    write_csv(full_csv_path, full_rows)
    _write_markdown(full_md_path, full_rows)
    return {
        "provider_lowcost_longitudinal": str(csv_path),
        "provider_lowcost_longitudinal_full_turns": str(full_csv_path),
    }


def summarize_full_turn_longitudinal() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for label, source_requests, dataset_dir, result_dir in FULL_TURN_SNAPSHOTS:
        dataset_manifest = _read_json(Path(dataset_dir) / "source_manifest.json")
        cluster_rows = _read_csv(Path(result_dir) / "clustering_metrics_all.csv")
        workflow_rows = _read_csv(Path(result_dir) / "workflow_reconstruction_metrics_all.csv")
        ordering_rows = _read_csv(Path(result_dir) / "ordering_metrics_all.csv")
        for feature_ablation in _ordered_unique(row["feature_ablation"] for row in cluster_rows):
            item: dict[str, Any] = {
                "snapshot": label,
                "source_requests": source_requests,
                "source_workflows": int(dataset_manifest.get("workflow_count", 0)),
                "feature_ablation": feature_ablation,
            }
            session = _find(cluster_rows, level="session", feature_ablation=feature_ablation)
            project = _find(cluster_rows, level="project", feature_ablation=feature_ablation)
            org = _find(cluster_rows, level="org", feature_ablation=feature_ablation)
            workflow = _find(workflow_rows, feature_ablation=feature_ablation)
            ordering = _find(ordering_rows, feature_ablation=feature_ablation)
            item.update(
                {
                    "evaluated_requests": _int(session.get("items")),
                    "session_f1": _float(session.get("pairwise_f1")),
                    "session_purity": _float(session.get("purity")),
                    "project_f1": _float(project.get("pairwise_f1")),
                    "org_f1": _float(org.get("pairwise_f1")),
                    "reconstructed_workflows": _int(workflow.get("workflows")),
                    "workflow_purity": _float(workflow.get("mean_purity")),
                    "workflow_pairwise_order_accuracy": _float(
                        workflow.get("mean_pairwise_order_accuracy")
                    ),
                    "pure_ordered_clusters": _int(ordering.get("pure_session_clusters")),
                    "ordered_pairs": _int(ordering.get("ordered_pairs")),
                }
            )
            out.append(item)
    return out


def _snapshot_source_requests(label: str) -> int:
    return int(label.removeprefix("first_"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    return {}


def _ordered_unique(values: Any) -> list[str]:
    out = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def _float(value: str | None) -> float:
    return float(value) if value not in {None, ""} else 0.0


def _int(value: str | None) -> int:
    return int(float(value)) if value not in {None, ""} else 0


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
        lines.append("| " + " | ".join(_format_cell(row.get(header)) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_cell(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize provider-lowcost longitudinal runs.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(write_longitudinal_tables(args.output_dir))


if __name__ == "__main__":
    main()
