from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from agent_privacy.reporting import write_csv


DEFAULT_RUNS = [
    (
        "provider_lowcost_sample100",
        Path("artifacts/datasets/open_swe_traces_raw_1000_sample100"),
        Path("results/open_swe_provider_lowcost_cumulative_sample100_cluster_timed"),
    ),
    (
        "provider_lowcost_full_turns_first_1000",
        Path("artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_1000_requests"),
        Path("results/open_swe_provider_lowcost_longitudinal_full_first_1000_turns"),
    ),
    (
        "provider_lowcost_full_turns_first_4000",
        Path("artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_4000_requests"),
        Path("results/open_swe_provider_lowcost_longitudinal_full_first_4000_turns"),
    ),
    (
        "provider_lowcost_full_turns_first_8000",
        Path("artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_8000_requests"),
        Path("results/open_swe_provider_lowcost_longitudinal_full_first_8000_turns"),
    ),
    (
        "provider_lowcost_full_turns_first_12000",
        Path("artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_12000_requests"),
        Path("results/open_swe_provider_lowcost_longitudinal_full_first_12000_turns"),
    ),
    (
        "overlay_u3_provider_lowcost_12k_materialized_budgeted",
        Path("artifacts/datasets/open_swe_user_overlay_u3_mixed_1000_snapshots/first_12000_requests"),
        Path("results/open_swe_user_overlay_u3_first_12000_provider_lowcost_budgeted"),
    ),
]

for level, dataset_base, result_prefix in [
    (
        "u3",
        "artifacts/datasets/open_swe_user_overlay_u3_mixed_1000_snapshots",
        "results/open_swe_user_overlay_u3",
    ),
    (
        "u4",
        "artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000_snapshots",
        "results/open_swe_user_overlay_u4",
    ),
]:
    for count in [1000, 4000, 8000, 12000]:
        DEFAULT_RUNS.append(
            (
                f"overlay_{level}_provider_lowcost_{count // 1000}k_streamed_budgeted",
                Path(f"{dataset_base}/first_{count}_requests"),
                Path(f"{result_prefix}_first_{count}_provider_lowcost_streamed"),
            )
        )


def summarize_runtime_cost(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [_summarize_run(label, dataset_dir, result_dir) for label, dataset_dir, result_dir in DEFAULT_RUNS]
    csv_path = output_dir / "open_swe_runtime_cost.csv"
    md_path = output_dir / "open_swe_runtime_cost.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return {"runtime_cost": str(csv_path)}


def _summarize_run(label: str, dataset_dir: Path, result_dir: Path) -> dict[str, Any]:
    source_manifest = _read_json_if_exists(dataset_dir / "source_manifest.json") or {}
    run_summary = _read_json_if_exists(result_dir / "run_summary.json") or {}
    metrics = _read_metrics(result_dir / "clustering_metrics_all.csv")
    workflow_metrics = _read_metrics(result_dir / "workflow_reconstruction_metrics_all.csv")
    provider_session = _find(metrics, method="provider_lowcost", level="session", feature_ablation="none") or _find(metrics, method="provider_lowcost", level="session", feature_ablation="no_semantic")
    provider_project = _find(metrics, method="provider_lowcost", level="project", feature_ablation="none") or _find(metrics, method="provider_lowcost", level="project", feature_ablation="no_semantic")
    provider_org = _find(metrics, method="provider_lowcost", level="org", feature_ablation="none") or _find(metrics, method="provider_lowcost", level="org", feature_ablation="no_semantic")
    workflow = _find(workflow_metrics, method="provider_lowcost", feature_ablation="none") or _find(workflow_metrics, method="provider_lowcost", feature_ablation="no_semantic")
    feature_summary = _feature_summary(run_summary)
    feature_budget = run_summary.get("feature_budget_overrides", {})
    stream_stats = feature_summary.get("stream_provider_lowcost_stats", {})
    return {
        "label": label,
        "dataset_dir": str(dataset_dir),
        "result_dir": str(result_dir),
        "source_requests": source_manifest.get("source_rows_seen") or source_manifest.get("requests") or "",
        "evaluated_requests": run_summary.get("requests", ""),
        "streaming_features": run_summary.get("defenses", {}).get("M0", {}).get("streaming_features", ""),
        "feature_seconds": _runtime(run_summary, "feature_seconds"),
        "attack_seconds": _runtime(run_summary, "attack_seconds"),
        "evaluation_seconds": _runtime(run_summary, "evaluation_seconds"),
        "cache_scan_seconds": _float_or_text(feature_summary.get("cache_scan_seconds")),
        "max_rss_mb": _float_or_text(feature_summary.get("max_rss_mb")),
        "feature_window_chars": feature_budget.get("feature_window_chars") or "",
        "feature_max_shingles": feature_budget.get("feature_max_shingles") or "",
        "feature_max_words": feature_budget.get("feature_max_words") or "",
        "stream_provider_lowcost": feature_budget.get("stream_provider_lowcost", ""),
        "max_cache_bucket_requests": stream_stats.get("max_cache_bucket_requests", ""),
        "candidate_edges": feature_summary.get("candidate_pairs_considered")
        or run_summary.get("candidate_edges", "not_recorded"),
        "candidate_pair_link_events": feature_summary.get("candidate_pairs_linked", ""),
        "session_f1": _float(provider_session.get("pairwise_f1")),
        "user_f1": _float((_find(metrics, method="provider_lowcost", level="user", feature_ablation="none") or {}).get("pairwise_f1")),
        "project_f1": _float(provider_project.get("pairwise_f1")),
        "org_f1": _float(provider_org.get("pairwise_f1")),
        "reconstructed_workflows": _int(
            workflow.get("reconstructed_workflows") or workflow.get("workflows")
        ),
        "workflow_pairwise_order_accuracy": _float(workflow.get("mean_pairwise_order_accuracy")),
    }


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_metrics(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _find(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    return {}


def _runtime(run_summary: dict[str, Any], key: str) -> float | str:
    direct = run_summary.get(key)
    if direct not in {None, ""}:
        return round(float(direct), 3)
    try:
        feature_summaries = run_summary["defenses"]["M0"]["ablations"]
        ablation_summary = next(iter(feature_summaries.values()))
        feature_ablation_summary = ablation_summary["feature_ablations"].get("none")
        if feature_ablation_summary is None:
            feature_ablation_summary = next(iter(ablation_summary["feature_ablations"].values()))
        value = feature_ablation_summary.get(key)
        return round(float(value), 3) if value not in {None, ""} else "not_recorded"
    except (KeyError, StopIteration, TypeError, ValueError):
        return "not_recorded"


def _feature_summary(run_summary: dict[str, Any]) -> dict[str, Any]:
    try:
        feature_summaries = run_summary["defenses"]["M0"]["ablations"]
        ablation_summary = next(iter(feature_summaries.values()))
        feature_ablation_summary = ablation_summary["feature_ablations"].get("none")
        if feature_ablation_summary is None:
            feature_ablation_summary = next(iter(ablation_summary["feature_ablations"].values()))
        return feature_ablation_summary
    except (KeyError, StopIteration, TypeError):
        return {}


def _float(value: str | None) -> float:
    return float(value) if value not in {None, ""} else 0.0


def _float_or_text(value: Any) -> float | str:
    if value in {None, ""}:
        return "not_recorded"
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return str(value)


def _int(value: str | None) -> int:
    return int(float(value)) if value not in {None, ""} else 0


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = [
        "label",
        "source_requests",
        "evaluated_requests",
        "feature_seconds",
        "attack_seconds",
        "evaluation_seconds",
        "cache_scan_seconds",
        "max_rss_mb",
        "feature_window_chars",
        "feature_max_shingles",
        "stream_provider_lowcost",
        "max_cache_bucket_requests",
        "candidate_edges",
        "candidate_pair_link_events",
        "session_f1",
        "user_f1",
        "project_f1",
        "org_f1",
        "workflow_pairwise_order_accuracy",
    ]
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
    parser = argparse.ArgumentParser(description="Summarize runtime/cost reporting table.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(summarize_runtime_cost(args.output_dir))


if __name__ == "__main__":
    main()
