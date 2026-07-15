from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_privacy.reporting import write_csv


@dataclass(frozen=True)
class OverlayRun:
    overlay_level: str
    snapshot: str
    dataset_dir: str
    result_dir: str
    run_type: str = "hybrid_ablation"


SNAPSHOTS = [1000, 4000, 8000, 12000]
FEATURE_ABLATIONS = [
    "none",
    "no_paths",
    "no_usernames",
    "no_tool_schema",
    "no_time_length",
    "no_cache",
    "no_shingles",
]


def _default_runs() -> list[OverlayRun]:
    runs = []
    for level, dataset_base, result_prefix in [
        (
            "U3",
            "artifacts/datasets/open_swe_user_overlay_u3_mixed_1000_snapshots",
            "results/open_swe_user_overlay_u3",
        ),
        (
            "U4",
            "artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000_snapshots",
            "results/open_swe_user_overlay_u4",
        ),
    ]:
        for count in SNAPSHOTS:
            runs.append(
                OverlayRun(
                    overlay_level=level,
                    snapshot=f"first_{count}_requests",
                    dataset_dir=f"{dataset_base}/first_{count}_requests",
                    result_dir=f"{result_prefix}_first_{count}_m0_ablation",
                )
            )
        for count in SNAPSHOTS:
            runs.append(
                OverlayRun(
                    overlay_level=level,
                    snapshot=f"first_{count}_requests",
                    dataset_dir=f"{dataset_base}/first_{count}_requests",
                    result_dir=f"{result_prefix}_first_{count}_provider_lowcost_streamed",
                    run_type="provider_lowcost_streamed",
                )
            )
    return runs


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_metrics(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _metric(rows: list[dict[str, str]], method: str, level: str) -> float | str:
    for row in rows:
        if row.get("method") == method and row.get("level") == level:
            return round(float(row["pairwise_f1"]), 3)
    return ""


def _metrics_for_ablation(metrics: list[dict[str, str]], feature_ablation: str) -> dict[str, Any]:
    rows = [row for row in metrics if row.get("feature_ablation", "none") == feature_ablation]
    return {
        "hybrid_session_f1": _metric(rows, "hybrid", "session"),
        "hybrid_user_f1": _metric(rows, "hybrid", "user"),
        "hybrid_project_f1": _metric(rows, "hybrid", "project"),
        "hybrid_org_f1": _metric(rows, "hybrid", "org"),
        "rare_user_f1": _metric(rows, "rare", "user"),
        "temporal_user_f1": _metric(rows, "temporal", "user"),
        "tool_user_f1": _metric(rows, "tool", "user"),
        "provider_lowcost_session_f1": _metric(rows, "provider_lowcost", "session"),
        "provider_lowcost_user_f1": _metric(rows, "provider_lowcost", "user"),
        "provider_lowcost_project_f1": _metric(rows, "provider_lowcost", "project"),
        "provider_lowcost_org_f1": _metric(rows, "provider_lowcost", "org"),
    }


def _summarize_run(run: OverlayRun) -> list[dict[str, Any]]:
    manifest = _read_json(Path(run.dataset_dir) / "source_manifest.json")
    metrics = _read_metrics(Path(run.result_dir) / "clustering_metrics_all.csv")
    rows = []
    for feature_ablation in FEATURE_ABLATIONS:
        metric_values = _metrics_for_ablation(metrics, feature_ablation)
        if (
            metric_values["hybrid_user_f1"] == ""
            and metric_values["provider_lowcost_session_f1"] == ""
        ):
            continue
        rows.append(
            {
                "overlay_level": run.overlay_level,
                "snapshot": run.snapshot,
                "run_type": run.run_type,
                "dataset_dir": run.dataset_dir,
                "result_dir": run.result_dir,
                "requests": manifest.get("requests", ""),
                "users": manifest.get("user_count", ""),
                "workflows": manifest.get("workflow_count", ""),
                "projects": manifest.get("project_count", ""),
                "orgs": manifest.get("org_count", ""),
                "feature_ablation": feature_ablation,
                **metric_values,
            }
        )
    return rows


def summarize_user_overlay(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        row
        for run in _default_runs()
        if (Path(run.result_dir) / "clustering_metrics_all.csv").exists()
        for row in _summarize_run(run)
    ]
    main_rows = [row for row in rows if row["feature_ablation"] == "none"]
    ablation_rows = [
        row
        for row in rows
        if row["run_type"] == "hybrid_ablation"
        and row["snapshot"] == "first_1000_requests"
        and row["feature_ablation"] in FEATURE_ABLATIONS
    ]
    scale_rows = [
        row
        for row in rows
        if row["feature_ablation"] == "none"
        and (
            row["snapshot"] == "first_1000_requests"
            or row["run_type"] == "provider_lowcost_streamed"
        )
    ]
    outputs = {
        "linkage": _write_table(
            output_dir / "open_swe_user_overlay_linkage_summary",
            main_rows,
            [
                "overlay_level",
                "snapshot",
                "run_type",
                "requests",
                "users",
                "workflows",
                "projects",
                "orgs",
                "hybrid_session_f1",
                "hybrid_user_f1",
                "hybrid_project_f1",
                "hybrid_org_f1",
                "rare_user_f1",
                "temporal_user_f1",
                "provider_lowcost_session_f1",
                "provider_lowcost_user_f1",
                "provider_lowcost_project_f1",
                "provider_lowcost_org_f1",
            ],
        ),
        "ablation": _write_table(
            output_dir / "open_swe_user_overlay_user_ablation",
            ablation_rows,
            [
                "overlay_level",
                "snapshot",
                "feature_ablation",
                "hybrid_user_f1",
                "hybrid_session_f1",
                "hybrid_project_f1",
                "hybrid_org_f1",
            ],
        ),
        "longitudinal": _write_table(
            output_dir / "open_swe_user_overlay_longitudinal",
            scale_rows,
            [
                "overlay_level",
                "snapshot",
                "run_type",
                "requests",
                "users",
                "hybrid_session_f1",
                "hybrid_user_f1",
                "hybrid_project_f1",
                "hybrid_org_f1",
                "provider_lowcost_session_f1",
                "provider_lowcost_user_f1",
                "provider_lowcost_project_f1",
                "provider_lowcost_org_f1",
            ],
        ),
    }
    return {key: str(path) for key, path in outputs.items()} | {"rows": str(len(rows))}


def _write_table(base_path: Path, rows: list[dict[str, Any]], headers: list[str]) -> Path:
    csv_path = base_path.with_suffix(".csv")
    md_path = base_path.with_suffix(".md")
    write_csv(csv_path, rows)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format(row.get(header, "")) for header in headers) + " |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path


def _format(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Open-SWE user overlay linkage runs.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(json.dumps(summarize_user_overlay(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
