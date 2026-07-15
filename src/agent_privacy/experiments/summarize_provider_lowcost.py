from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from agent_privacy.reporting import write_csv


DEFAULT_CUMULATIVE = Path("results/open_swe_provider_lowcost_cumulative_sample100_cluster")
DEFAULT_TURN_DELTA = Path("results/open_swe_provider_lowcost_turn_delta_sample100_cluster")


def summarize_provider_lowcost(
    *,
    cumulative_dir: Path = DEFAULT_CUMULATIVE,
    turn_delta_dir: Path = DEFAULT_TURN_DELTA,
) -> dict[str, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for view, result_dir in [("cumulative", cumulative_dir), ("turn_delta", turn_delta_dir)]:
        cluster_rows = _read_csv(result_dir / "clustering_metrics_all.csv")
        workflow_rows = _read_csv(result_dir / "workflow_reconstruction_metrics_all.csv")
        for feature_ablation in _ordered_unique(row["feature_ablation"] for row in cluster_rows):
            item: dict[str, Any] = {"view": view, "feature_ablation": feature_ablation}
            for level in ["session", "project", "org"]:
                metric = _find(cluster_rows, level=level, feature_ablation=feature_ablation)
                item[f"{level}_f1"] = _float(metric.get("pairwise_f1"))
                item[f"{level}_purity"] = _float(metric.get("purity"))
            workflow = _find(workflow_rows, feature_ablation=feature_ablation)
            item["reconstructed_workflows"] = _int(workflow.get("workflows"))
            item["workflow_mean_purity"] = _float(workflow.get("mean_purity"))
            item["workflow_pairwise_order_accuracy"] = _float(
                workflow.get("mean_pairwise_order_accuracy")
            )
            rows.append(item)
    return {"provider_lowcost": rows}


def write_provider_lowcost_tables(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = summarize_provider_lowcost()
    outputs = {}
    for name, rows in summaries.items():
        csv_path = output_dir / f"open_swe_{name}.csv"
        md_path = output_dir / f"open_swe_{name}.md"
        write_csv(csv_path, rows)
        _write_markdown(md_path, rows)
        outputs[name] = str(csv_path)
    return outputs


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
    parser = argparse.ArgumentParser(description="Summarize provider-lowcost Open-SWE runs.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(write_provider_lowcost_tables(args.output_dir))


if __name__ == "__main__":
    main()
