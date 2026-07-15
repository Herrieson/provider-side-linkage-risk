from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.build_release_bundles import include_result_file


ROOT = Path(__file__).resolve().parents[1]


def test_release_catalog_references_exist() -> None:
    datasets = json.loads((ROOT / "artifacts/dataset-manifest.json").read_text(encoding="utf-8"))
    results = json.loads((ROOT / "results/result-manifest.json").read_text(encoding="utf-8"))
    artifacts = json.loads((ROOT / "docs/artifact-manifest.json").read_text(encoding="utf-8"))

    assert (ROOT / datasets["bundled_example"]["path"]).is_dir()
    for entry in datasets["datasets"]:
        for field in ("config", "dataset_card", "reproduction"):
            if value := entry.get(field):
                assert (ROOT / value).is_file(), (entry["id"], field, value)
    for run in results["curated_runs"]:
        for table in run["tables"]:
            assert (ROOT / table).is_file(), (run["id"], table)
    for label, value in artifacts["release"].items():
        if isinstance(value, str):
            assert (ROOT / value).exists(), (label, value)


def test_result_bundle_policy_excludes_content_payloads() -> None:
    manifest = json.loads((ROOT / "results/result-manifest.json").read_text(encoding="utf-8"))
    include = tuple(manifest["bundle_policy"]["include"])
    exclude = tuple(manifest["bundle_policy"]["exclude"])

    assert include_result_file(Path("M0/predictions.json"), include, exclude)
    assert include_result_file(Path("clustering_metrics_all.csv"), include, exclude)
    assert not include_result_file(Path("M0/attack_view.jsonl"), include, exclude)
    assert not include_result_file(Path("M0/reconstructed_workflows.jsonl"), include, exclude)
    assert not include_result_file(Path("medium/dataset/attack_view.jsonl"), include, exclude)
    assert not include_result_file(Path("semantic_predicted_clusters.json"), include, exclude)


def test_smoke_example_ids_and_metrics_are_consistent() -> None:
    example = ROOT / "examples/tool_agent_smoke"
    attack_ids = {
        json.loads(line)["request_id"]
        for line in (example / "dataset/attack_view.jsonl").read_text(encoding="utf-8").splitlines()
    }
    truth_ids = {
        json.loads(line)["request_id"]
        for line in (example / "dataset/ground_truth.jsonl").read_text(encoding="utf-8").splitlines()
    }
    predictions = json.loads((example / "expected/predictions.json").read_text(encoding="utf-8"))
    assert attack_ids == truth_ids
    assert len(attack_ids) == 6
    for labels in predictions["provider_lowcost"].values():
        assert set(labels) == attack_ids

    with (example / "expected/clustering_metrics_all.csv").open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    f1_by_level = {row["level"]: float(row["pairwise_f1"]) for row in rows}
    assert f1_by_level == {"session": 1.0, "user": 1.0, "project": 1.0, "org": 0.0}
