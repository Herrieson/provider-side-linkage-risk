from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from agent_privacy.reporting import write_csv


DEFENSE_RUNS = [
    (
        "baseline_defense_probe",
        Path("results/open_swe_traces_raw_1000_sample100_turns_3_6_9_12_defense_probe_fast"),
    ),
    (
        "selective_workspace_probe",
        Path("results/open_swe_traces_raw_1000_sample100_turns_3_6_9_12_selective_mitigation_fast"),
    ),
]


def summarize_defense_frontier(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for run_label, result_dir in DEFENSE_RUNS:
        cluster_rows = _read_csv(result_dir / "clustering_metrics_all.csv")
        utility_rows = _read_csv(result_dir / "utility_metrics_all.csv")
        defenses = sorted({row["defense"] for row in cluster_rows})
        for defense in defenses:
            utility = _find(utility_rows, defense=defense, ablation="none")
            item = {
                "run": run_label,
                "defense": defense,
                "token_retention": _float(utility.get("token_retention")),
                "message_retention": _float(utility.get("message_retention")),
                "char_retention": _float(utility.get("char_retention")),
                "tool_char_retention": _float(utility.get("tool_char_retention")),
                "workspace_paths_removed": _int(utility.get("workspace_path_count_removed")),
                "domains_removed": _int(utility.get("domain_count_removed")),
                "repository_fields_removed": _int(utility.get("repository_field_count_removed")),
            }
            for level in ["session", "project", "org"]:
                metric = _find(cluster_rows, defense=defense, method="hybrid", level=level)
                item[f"hybrid_{level}_f1"] = _float(metric.get("pairwise_f1"))
                item[f"hybrid_{level}_purity"] = _float(metric.get("purity"))
            rows.append(item)
    csv_path = output_dir / "open_swe_defense_utility_frontier.csv"
    md_path = output_dir / "open_swe_defense_utility_frontier.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return {"defense_frontier": str(csv_path)}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _find(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    return {}


def _float(value: str | None) -> float:
    return float(value) if value not in {None, ""} else 0.0


def _int(value: str | None) -> int:
    return int(float(value)) if value not in {None, ""} else 0


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = [
        "run",
        "defense",
        "hybrid_session_f1",
        "hybrid_project_f1",
        "hybrid_org_f1",
        "token_retention",
        "message_retention",
        "tool_char_retention",
        "workspace_paths_removed",
        "domains_removed",
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
    parser = argparse.ArgumentParser(description="Summarize Open-SWE defense utility frontier.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(summarize_defense_frontier(args.output_dir))


if __name__ == "__main__":
    main()
