from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from agent_privacy.experiments.summarize_runtime_cost import summarize_runtime_cost
from agent_privacy.reporting import write_csv


SOURCE_TABLE = Path("docs/tables/open_swe_runtime_cost.csv")
OUTPUT_BASE = "open_swe_provider_lowcost_cost_model"


def summarize_lowcost_cost_model(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not SOURCE_TABLE.exists():
        summarize_runtime_cost(output_dir)
    rows = [_cost_row(row) for row in _read_csv(SOURCE_TABLE)]
    rows = [row for row in rows if row["candidate_pairs"] != "not_recorded"]
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    headers = [
        "label",
        "evaluated_requests",
        "all_pairs",
        "candidate_pairs",
        "candidate_pairs_per_request",
        "candidate_reduction_factor",
        "measured_total_seconds",
        "seconds_per_1k_requests",
        "extrapolated_cpu_hours_per_1m_requests",
        "max_rss_mb",
        "session_f1",
        "user_f1",
        "project_f1",
        "org_f1",
    ]
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows, headers)
    return {"cost_model": str(csv_path), "rows": str(len(rows))}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _cost_row(row: dict[str, str]) -> dict[str, Any]:
    requests = _to_int(row.get("evaluated_requests"))
    candidate_pairs = _to_int(row.get("candidate_edges"))
    all_pairs = requests * (requests - 1) // 2 if requests else 0
    total_seconds = sum(
        _to_float(row.get(key))
        for key in [
            "feature_seconds",
            "attack_seconds",
            "evaluation_seconds",
            "cache_scan_seconds",
        ]
    )
    return {
        "label": row.get("label", ""),
        "evaluated_requests": requests,
        "all_pairs": all_pairs,
        "candidate_pairs": candidate_pairs if candidate_pairs else "not_recorded",
        "candidate_pairs_per_request": _round(candidate_pairs / requests)
        if requests and candidate_pairs
        else "not_recorded",
        "candidate_reduction_factor": _round(all_pairs / candidate_pairs)
        if all_pairs and candidate_pairs
        else "not_recorded",
        "measured_total_seconds": _round(total_seconds) if total_seconds else "not_recorded",
        "seconds_per_1k_requests": _round(total_seconds / requests * 1000)
        if total_seconds and requests
        else "not_recorded",
        "extrapolated_cpu_hours_per_1m_requests": _round(total_seconds / requests * 1_000_000 / 3600)
        if total_seconds and requests
        else "not_recorded",
        "max_rss_mb": _copy_float(row.get("max_rss_mb")),
        "session_f1": _copy_float(row.get("session_f1")),
        "user_f1": _copy_float(row.get("user_f1")),
        "project_f1": _copy_float(row.get("project_f1")),
        "org_f1": _copy_float(row.get("org_f1")),
    }


def _to_int(value: str | None) -> int:
    if value in {None, "", "not_recorded"}:
        return 0
    return int(float(value))


def _to_float(value: str | None) -> float:
    if value in {None, "", "not_recorded"}:
        return 0.0
    return float(value)


def _copy_float(value: str | None) -> float | str:
    if value in {None, "", "not_recorded"}:
        return "not_recorded"
    return _round(float(value))


def _round(value: float) -> float:
    return round(value, 3)


def _write_markdown(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format(row.get(header, "")) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize CARP/provider-lowcost cost model.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(summarize_lowcost_cost_model(args.output_dir))


if __name__ == "__main__":
    main()
