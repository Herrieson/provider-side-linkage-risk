from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from agent_privacy.reporting import write_csv


DEFAULT_CONTROLS = Path("results/open_swe_controls_sample100_turns_3_6_9_12")
DEFAULT_CI = Path("docs/tables/open_swe_controls_sample100_bootstrap_ci.csv")


def summarize_controls(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics = _read_csv(DEFAULT_CONTROLS / "clustering_metrics_all.csv")
    ci_rows = _read_csv(DEFAULT_CI) if DEFAULT_CI.exists() else []
    out = []
    for row in metrics:
        if row.get("feature_ablation") != "none":
            continue
        ci = _find_ci(ci_rows, method=row["method"], level=row["level"])
        out.append(
            {
                "method": row["method"],
                "level": row["level"],
                "feature_ablation": row["feature_ablation"],
                "precision": _float(row["pairwise_precision"]),
                "recall": _float(row["pairwise_recall"]),
                "f1": _float(row["pairwise_f1"]),
                "f1_ci_low": _float(ci.get("f1_ci_low")),
                "f1_ci_high": _float(ci.get("f1_ci_high")),
                "purity": _float(row["purity"]),
                "clusters": _int(row["clusters"]),
                "items": _int(row["items"]),
            }
        )
    csv_path = output_dir / "open_swe_controls_sample100.csv"
    md_path = output_dir / "open_swe_controls_sample100.md"
    write_csv(csv_path, out)
    _write_markdown(md_path, out)
    return {"controls": str(csv_path)}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _find_ci(rows: list[dict[str, str]], *, method: str, level: str) -> dict[str, str]:
    for row in rows:
        if row.get("method") == method and row.get("level") == level:
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
    parser = argparse.ArgumentParser(description="Summarize Open-SWE control baselines.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(summarize_controls(args.output_dir))


if __name__ == "__main__":
    main()
