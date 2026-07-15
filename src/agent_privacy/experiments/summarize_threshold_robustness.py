from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from agent_privacy.experiments.semantic_linkage import write_markdown
from agent_privacy.reporting import write_csv


DEFAULT_INPUT = Path("docs/tables/open_swe_heldout_threshold_sweep.csv")
DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "open_swe_heldout_threshold_robustness"


def summarize_threshold_robustness(
    *, input_path: Path = DEFAULT_INPUT, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> dict[str, str]:
    with input_path.open(newline="", encoding="utf-8") as handle:
        source = list(csv.DictReader(handle))
    rows = []
    for row in source:
        if row["variant"] != "context_sweep":
            continue
        containment = float(row["containment_threshold"])
        jaccard = float(row["jaccard_threshold"])
        cap = int(row["max_pairs_per_request"])
        axis = None
        value: float | int = 0.0
        if jaccard == 0.20 and cap == 400:
            axis, value = "containment", containment
        elif containment == 0.78 and cap == 400:
            axis, value = "jaccard", jaccard
        elif containment == 0.78 and jaccard == 0.20:
            axis, value = "pair_budget", cap
        if axis is None:
            continue
        rows.append(
            {
                "axis": axis,
                "value": value,
                "candidate_pairs": int(row["candidate_pairs"]),
                "candidate_recall": float(row["candidate_recall"]),
                "candidate_precision": float(row["candidate_precision"]),
                "session_precision": float(row["session_precision"]),
                "session_recall": float(row["session_recall"]),
                "session_f1": float(row["session_f1"]),
                "attack_seconds": float(row["attack_seconds"]),
            }
        )
    rows = _deduplicate(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
    write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path)}


def _deduplicate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, float | int]] = set()
    output = []
    for row in rows:
        key = (str(row["axis"]), row["value"])
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(summarize_threshold_robustness(input_path=args.input, output_dir=args.output_dir))


if __name__ == "__main__":
    main()
