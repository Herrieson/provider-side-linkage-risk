from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import fields
from pathlib import Path
from typing import Any

from agent_privacy.attacks.pipeline import run_attacks
from agent_privacy.data.generator import generate_dataset
from agent_privacy.data.schemas import DatasetConfig
from agent_privacy.defenses.transforms import apply_defense
from agent_privacy.evaluation.clustering import evaluate_all
from agent_privacy.evaluation.ordering import evaluate_ordering_all
from agent_privacy.evaluation.profile import evaluate_profiles
from agent_privacy.io import read_jsonl, write_json, write_jsonl
from agent_privacy.profiling.rule_profiler import profile_clusters
from agent_privacy.reporting import write_csv


DEFENSES = ["M0", "M1", "M2", "M3", "M4", "M6"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LLM Agent API privacy MVP.")
    parser.add_argument("--config", type=Path, default=Path("configs/smoke.json"))
    parser.add_argument("--output", type=Path, default=Path("results/smoke"))
    parser.add_argument("--defenses", nargs="*", default=DEFENSES)
    args = parser.parse_args()

    config = _load_config(args.config)
    if args.output.exists():
        shutil.rmtree(args.output)
    dataset_dir = args.output / "dataset_m0"
    summary = generate_dataset(config, dataset_dir)
    base_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")

    all_cluster_rows: list[dict[str, Any]] = []
    all_ordering_rows: list[dict[str, Any]] = []
    all_profile_rows: list[dict[str, Any]] = []
    run_summary = {"dataset": summary, "defenses": {}}

    for defense in args.defenses:
        defended_rows = apply_defense(base_rows, defense, seed=config.seed)
        defense_dir = args.output / defense
        write_jsonl(defense_dir / "attack_view.jsonl", defended_rows)
        predictions = run_attacks(defended_rows)
        write_json(defense_dir / "predictions.json", predictions)

        cluster_rows = evaluate_all(predictions, truth_rows)
        for row in cluster_rows:
            row["defense"] = defense
        write_csv(defense_dir / "clustering_metrics.csv", cluster_rows)
        all_cluster_rows.extend(cluster_rows)

        ordering_rows = evaluate_ordering_all(defended_rows, predictions, truth_rows)
        for row in ordering_rows:
            row["defense"] = defense
        write_csv(defense_dir / "ordering_metrics.csv", ordering_rows)
        all_ordering_rows.extend(ordering_rows)

        hybrid_org_labels = predictions["hybrid"]["org"]
        profiles = profile_clusters(defended_rows, hybrid_org_labels)
        write_json(defense_dir / "hybrid_org_profiles.json", profiles)
        profile_rows = evaluate_profiles(profiles, truth_rows, hybrid_org_labels)
        for row in profile_rows:
            row["defense"] = defense
            row["method"] = "hybrid"
            row["level"] = "org"
        write_csv(defense_dir / "profile_metrics.csv", profile_rows)
        all_profile_rows.extend(profile_rows)

        run_summary["defenses"][defense] = {
            "requests": len(defended_rows),
            "cluster_metric_rows": len(cluster_rows),
            "ordering_metric_rows": len(ordering_rows),
            "profile_metric_rows": len(profile_rows),
        }

    write_csv(args.output / "clustering_metrics_all.csv", all_cluster_rows)
    write_csv(args.output / "ordering_metrics_all.csv", all_ordering_rows)
    write_csv(args.output / "profile_metrics_all.csv", all_profile_rows)
    write_json(args.output / "run_summary.json", run_summary)


def _load_config(path: Path) -> DatasetConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    allowed = {field.name for field in fields(DatasetConfig)}
    return DatasetConfig(**{key: value for key, value in raw.items() if key in allowed})


if __name__ == "__main__":
    main()
