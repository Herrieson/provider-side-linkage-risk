from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from agent_privacy.reporting import write_csv


DEFAULT_CUMULATIVE = Path("results/open_swe_traces_raw_1000_sample100_turns_3_6_9_12_feature_ablation_full_features")
DEFAULT_TURN_DELTA = Path("results/open_swe_traces_raw_1000_turn_delta_sample100_feature_ablation_full_features")
DEFAULT_PROFILE = Path("results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_profile")


def summarize_gap_results(
    *,
    cumulative_dir: Path = DEFAULT_CUMULATIVE,
    turn_delta_dir: Path = DEFAULT_TURN_DELTA,
    profile_dir: Path = DEFAULT_PROFILE,
) -> dict[str, list[dict[str, Any]]]:
    feature_rows = []
    for view, result_dir in [("cumulative", cumulative_dir), ("turn_delta", turn_delta_dir)]:
        feature_rows.extend(_feature_rows(view, result_dir / "clustering_metrics_all.csv"))
    ordering_rows = []
    for view, result_dir in [("cumulative", cumulative_dir), ("turn_delta", turn_delta_dir)]:
        ordering_rows.extend(_ordering_rows(view, result_dir / "ordering_metrics_all.csv"))
    profile_rows = _profile_rows(profile_dir / "profile_metrics_all.csv")
    return {
        "feature_ablation": feature_rows,
        "ordering": ordering_rows,
        "profile": profile_rows,
    }


def write_gap_summary_tables(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = summarize_gap_results()
    outputs = {}
    for name, rows in summaries.items():
        csv_path = output_dir / f"open_swe_gap_{name}.csv"
        md_path = output_dir / f"open_swe_gap_{name}.md"
        write_csv(csv_path, rows)
        _write_markdown(md_path, rows)
        outputs[name] = str(csv_path)
    return outputs


def _feature_rows(view: str, path: Path) -> list[dict[str, Any]]:
    rows = _read_csv(path)
    out = []
    for feature_ablation in _ordered_unique(row["feature_ablation"] for row in rows):
        item = {"view": view, "feature_ablation": feature_ablation}
        for level in ["session", "project", "org"]:
            metric = _find(rows, method="hybrid", level=level, feature_ablation=feature_ablation)
            item[f"hybrid_{level}_f1"] = _float(metric.get("pairwise_f1"))
        out.append(item)
    return out


def _ordering_rows(view: str, path: Path) -> list[dict[str, Any]]:
    rows = _read_csv(path)
    out = []
    for feature_ablation in _ordered_unique(row["feature_ablation"] for row in rows):
        metric = _find(rows, method="hybrid", feature_ablation=feature_ablation)
        out.append(
            {
                "view": view,
                "feature_ablation": feature_ablation,
                "timestamp_adjacent_accuracy": _float(metric.get("adjacent_pair_accuracy")),
                "timestamp_pairwise_accuracy": _float(metric.get("pairwise_order_accuracy")),
                "context_adjacent_accuracy": _float(metric.get("context_adjacent_pair_accuracy")),
                "context_pairwise_accuracy": _float(metric.get("context_pairwise_order_accuracy")),
                "adjacent_pairs": _int(metric.get("adjacent_pairs")),
                "ordered_pairs": _int(metric.get("ordered_pairs")),
                "evaluated_clusters": _int(metric.get("evaluated_clusters")),
            }
        )
    return out


def _profile_rows(path: Path) -> list[dict[str, Any]]:
    rows = _read_csv(path)
    keep = {
        "build_tools",
        "package_managers",
        "frameworks",
        "languages",
        "ci_cd_systems",
        "repo_names",
        "service_names",
        "__micro__",
    }
    out = []
    for row in rows:
        if row["field"] not in keep:
            continue
        out.append(
            {
                "field": row["field"],
                "precision": _float(row.get("precision")),
                "recall": _float(row.get("recall")),
                "f1": _float(row.get("f1")),
                "tp": _int(row.get("tp")),
                "fp": _int(row.get("fp")),
                "fn": _int(row.get("fn")),
                "predicted_values": _int(row.get("predicted_values")),
                "evidence_coverage": _float(row.get("evidence_coverage")),
            }
        )
    return out


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
    parser = argparse.ArgumentParser(description="Summarize gap-closing Open-SWE experiments.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(write_gap_summary_tables(args.output_dir))


if __name__ == "__main__":
    main()
