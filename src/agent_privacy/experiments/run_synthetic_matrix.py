from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from agent_privacy.attacks.pipeline import run_attacks
from agent_privacy.data.generator import generate_dataset
from agent_privacy.data.schemas import DatasetConfig
from agent_privacy.evaluation.clustering import evaluate_all
from agent_privacy.evaluation.profile import evaluate_profiles
from agent_privacy.io import read_jsonl, write_json
from agent_privacy.profiling.rule_profiler import profile_clusters
from agent_privacy.reporting import write_csv


DEFAULT_SCENARIOS = {
    "small": DatasetConfig(
        seed=7,
        num_orgs=8,
        users_per_org=3,
        projects_per_org=2,
        workflows_per_user=6,
        turns_per_workflow=5,
        noise_rate=0.10,
    ),
    "medium": DatasetConfig(
        seed=7,
        num_orgs=12,
        users_per_org=4,
        projects_per_org=3,
        workflows_per_user=8,
        turns_per_workflow=5,
        noise_rate=0.12,
    ),
    "hard_shared": DatasetConfig(
        seed=7,
        num_orgs=12,
        users_per_org=4,
        projects_per_org=3,
        workflows_per_user=8,
        turns_per_workflow=5,
        noise_rate=0.20,
        shared_template_rate=0.95,
        shared_repo_name_rate=0.75,
        shared_service_name_rate=0.75,
        shared_stack_rate=0.90,
        cross_user_same_project_rate=0.75,
        context_carryover_rate=0.65,
        time_mixing_window_minutes=180,
    ),
}


def run_synthetic_matrix(
    *,
    output_root: Path,
    methods: list[str] | None = None,
) -> dict[str, str]:
    selected_methods = methods or ["temporal", "rare", "tool", "hybrid", "provider_lowcost"]
    output_root.mkdir(parents=True, exist_ok=True)
    cluster_rows_all: list[dict[str, Any]] = []
    profile_rows_all: list[dict[str, Any]] = []
    dataset_rows: list[dict[str, Any]] = []
    for scenario, config in DEFAULT_SCENARIOS.items():
        dataset_dir = output_root / scenario / "dataset"
        result_dir = output_root / scenario / "M0"
        if dataset_dir.exists():
            shutil.rmtree(dataset_dir)
        if result_dir.exists():
            shutil.rmtree(result_dir)
        summary = generate_dataset(config, dataset_dir)
        attack_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
        truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
        predictions = run_attacks(attack_rows, methods=selected_methods)
        write_json(result_dir / "predictions.json", predictions)
        cluster_rows = evaluate_all(predictions, truth_rows, levels=["session", "user", "project", "org"])
        for row in cluster_rows:
            row["scenario"] = scenario
            row["requests"] = len(attack_rows)
            row["method"] = row["method"]
        write_csv(result_dir / "clustering_metrics.csv", cluster_rows)
        cluster_rows_all.extend(cluster_rows)
        profile_method = "hybrid" if "hybrid" in predictions else selected_methods[0]
        profile_labels = predictions[profile_method]["org"]
        profiles = profile_clusters(attack_rows, profile_labels)
        write_json(result_dir / "hybrid_org_profiles.json", profiles)
        profile_rows = evaluate_profiles(profiles, truth_rows, profile_labels)
        for row in profile_rows:
            row["scenario"] = scenario
            row["method"] = profile_method
            row["level"] = "org"
        write_csv(result_dir / "profile_metrics.csv", profile_rows)
        profile_rows_all.extend(profile_rows)
        dataset_rows.append({"scenario": scenario, **summary, **asdict(config)})
    cluster_csv = output_root / "synthetic_matrix_clustering.csv"
    profile_csv = output_root / "synthetic_matrix_profile.csv"
    dataset_csv = output_root / "synthetic_matrix_datasets.csv"
    write_csv(cluster_csv, cluster_rows_all)
    write_csv(profile_csv, profile_rows_all)
    write_csv(dataset_csv, dataset_rows)
    _write_summary_table(output_root / "synthetic_matrix_summary.md", cluster_rows_all, profile_rows_all)
    return {
        "clustering": str(cluster_csv),
        "profile": str(profile_csv),
        "datasets": str(dataset_csv),
        "summary": str(output_root / "synthetic_matrix_summary.md"),
    }


def _write_summary_table(
    path: Path,
    cluster_rows: list[dict[str, Any]],
    profile_rows: list[dict[str, Any]],
) -> None:
    rows = []
    scenarios = sorted({row["scenario"] for row in cluster_rows})
    for scenario in scenarios:
        item = {"scenario": scenario}
        for level in ["session", "user", "project", "org"]:
            metric = _find(cluster_rows, scenario=scenario, method="hybrid", level=level)
            item[f"hybrid_{level}_f1"] = float(metric.get("pairwise_f1", 0.0)) if metric else 0.0
        micro = _find(profile_rows, scenario=scenario, field="__micro__")
        item["profile_micro_f1"] = float(micro.get("f1", 0.0)) if micro else 0.0
        rows.append(item)
    headers = list(rows[0]) if rows else []
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format(row.get(header)) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _find(rows: list[dict[str, Any]], **criteria: str) -> dict[str, Any]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    return {}


def _format(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run controlled synthetic scale/difficulty/profile experiments.")
    parser.add_argument("--output-root", type=Path, default=Path("results/synthetic_matrix"))
    parser.add_argument("--methods", nargs="*")
    args = parser.parse_args()
    print(json.dumps(run_synthetic_matrix(output_root=args.output_root, methods=args.methods), indent=2))


if __name__ == "__main__":
    main()
