from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from agent_privacy.experiments.bootstrap_ci import bootstrap_clustering_ci
from agent_privacy.experiments.summarize_open_swe import DEFAULT_CELLS
from agent_privacy.reporting import write_csv


def bootstrap_open_swe_2x2(
    *,
    output_dir: Path,
    iterations: int = 200,
    seed: int = 7,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for cell in DEFAULT_CELLS:
        views = [
            ("cumulative_raw", Path(cell.dataset_dir), Path(cell.cumulative_raw) / "M0" / "predictions.json", None),
            ("cumulative_no_workspace", Path(cell.dataset_dir), Path(cell.cumulative_no_workspace) / "M0" / "predictions.json", None),
            ("turn_delta_raw", Path(cell.turn_delta_dir), Path(cell.turn_delta_raw) / "M0" / "predictions.json", None),
            ("turn_delta_no_workspace", Path(cell.turn_delta_dir), Path(cell.turn_delta_no_workspace) / "M0" / "predictions.json", None),
        ]
        for view, dataset_dir, predictions_path, turn_ids in views:
            if not predictions_path.exists():
                continue
            tmp_output = output_dir / f".tmp_{cell.scaffold}_{cell.split}_{view}_ci.csv"
            ci_rows = bootstrap_clustering_ci(
                dataset_dir=dataset_dir,
                predictions_path=predictions_path,
                output=tmp_output,
                methods=["hybrid"],
                levels=["session", "project", "org"],
                unit_level="session",
                iterations=iterations,
                seed=seed,
                turn_ids=turn_ids,
            )
            for row in ci_rows:
                rows.append(
                    {
                        "scaffold": cell.scaffold,
                        "split": cell.split,
                        "sample_size": cell.sample_size,
                        "view": view,
                        **row,
                    }
                )
            tmp_output.unlink(missing_ok=True)
            tmp_output.with_suffix(".md").unlink(missing_ok=True)
    csv_path = output_dir / "open_swe_2x2_bootstrap_ci.csv"
    md_path = output_dir / "open_swe_2x2_bootstrap_ci.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return rows


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = [
        "scaffold",
        "split",
        "view",
        "level",
        "observed_f1",
        "f1_ci_low",
        "f1_ci_high",
        "units",
        "requests",
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
    parser = argparse.ArgumentParser(description="Bootstrap CI for the Open-SWE 2x2 matrix.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    rows = bootstrap_open_swe_2x2(
        output_dir=args.output_dir,
        iterations=args.iterations,
        seed=args.seed,
    )
    print({"rows": len(rows), "output": str(args.output_dir / "open_swe_2x2_bootstrap_ci.csv")})


if __name__ == "__main__":
    main()
