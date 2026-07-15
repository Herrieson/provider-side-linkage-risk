from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from agent_privacy.reporting import write_csv


DEFAULT_RESULT_DIR = Path("results/tau_bench_historical_sample200_provider_lowcost")
DEFAULT_DATASET_DIR = Path("artifacts/datasets/tau_bench_historical_sample200")
OUTPUT_BASE = "tau_bench_historical_sample200_provider_lowcost"


def summarize_tau_bench(
    output_dir: Path,
    result_dir: Path = DEFAULT_RESULT_DIR,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    output_base: str = OUTPUT_BASE,
    dataset_name: str = "tau_bench_historical_sample200",
    status: str = "real_historical_trace_sample",
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = _read_metrics(result_dir / "clustering_metrics_all.csv")
    summary = _run_summary(result_dir)
    manifest = _read_json(dataset_dir / "source_manifest.json")
    out = []
    for row in rows:
        if row.get("method") != "provider_lowcost":
            continue
        out.append(
            {
                "dataset": dataset_name,
                "status": status,
                "requests": summary.get("requests", ""),
                "workflows": manifest.get("workflows", manifest.get("workflow_count", "")),
                "level": row["level"],
                "feature_ablation": row.get("feature_ablation", ""),
                "pairwise_precision": _round(row.get("pairwise_precision")),
                "pairwise_recall": _round(row.get("pairwise_recall")),
                "pairwise_f1": _round(row.get("pairwise_f1")),
                "clusters": _round(row.get("clusters"), digits=0),
                "candidate_pairs_considered": _feature_stat(
                    summary, row.get("feature_ablation", ""), "candidate_pairs_considered"
                ),
                "candidate_pairs_linked": _feature_stat(
                    summary, row.get("feature_ablation", ""), "candidate_pairs_linked"
                ),
                "candidate_reduction_vs_all_pairs": _candidate_reduction(summary, row),
                "total_stream_seconds": _round(
                    _feature_stat(summary, row.get("feature_ablation", ""), "total_stream_seconds")
                ),
                "max_rss_mb": _round(
                    _feature_stat(summary, row.get("feature_ablation", ""), "max_rss_mb")
                ),
            }
        )

    csv_path = output_dir / f"{output_base}.csv"
    md_path = output_dir / f"{output_base}.md"
    write_csv(csv_path, out)
    headers = [
        "dataset",
        "status",
        "requests",
        "workflows",
        "level",
        "feature_ablation",
        "pairwise_precision",
        "pairwise_recall",
        "pairwise_f1",
        "clusters",
        "candidate_pairs_considered",
        "candidate_pairs_linked",
        "candidate_reduction_vs_all_pairs",
        "total_stream_seconds",
        "max_rss_mb",
    ]
    _write_markdown(md_path, out, headers)
    return {"tau_bench_table": str(csv_path), "rows": str(len(out))}


def _read_metrics(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _run_summary(result_dir: Path) -> dict[str, Any]:
    return _read_json(result_dir / "run_summary.json")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _feature_stat(summary: dict[str, Any], feature_ablation: str | None, key: str) -> Any:
    feature_ablation = feature_ablation or "none"
    feature = (
        summary.get("defenses", {})
        .get("M0", {})
        .get("ablations", {})
        .get("none", {})
        .get("feature_ablations", {})
        .get(feature_ablation, {})
    )
    stats = feature.get("stream_provider_lowcost_stats", {})
    return stats.get(key, feature.get(key, ""))


def _candidate_reduction(summary: dict[str, Any], row: dict[str, str]) -> str:
    requests = int(float(row.get("items") or summary.get("requests") or 0))
    candidates = _feature_stat(summary, row.get("feature_ablation", ""), "candidate_pairs_considered")
    if not requests or not candidates:
        return ""
    all_pairs = requests * (requests - 1) / 2
    return _round(all_pairs / float(candidates))


def _round(value: Any, digits: int = 3) -> str:
    if value == "":
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if digits == 0:
        return str(int(round(number)))
    return f"{number:.{digits}f}"


def _write_markdown(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize tau-bench historical linkage results.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--output-base", type=str, default=OUTPUT_BASE)
    parser.add_argument("--dataset-name", type=str, default="tau_bench_historical_sample200")
    parser.add_argument("--status", type=str, default="real_historical_trace_sample")
    args = parser.parse_args()
    print(
        summarize_tau_bench(
            args.output_dir,
            args.result_dir,
            args.dataset_dir,
            output_base=args.output_base,
            dataset_name=args.dataset_name,
            status=args.status,
        )
    )


if __name__ == "__main__":
    main()
