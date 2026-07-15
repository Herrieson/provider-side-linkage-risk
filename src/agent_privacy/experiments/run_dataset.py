from __future__ import annotations

import argparse
import json
import resource
import shutil
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from agent_privacy.attacks.pipeline import (
    hybrid_candidate_edges_from_features,
    run_provider_lowcost_from_jsonl,
    run_attacks_from_features,
)
from agent_privacy.defenses.transforms import apply_defense
from agent_privacy.defenses.utility import summarize_utility
from agent_privacy.evaluation.clustering import evaluate_all
from agent_privacy.evaluation.controls import control_predictions, split_control_methods
from agent_privacy.evaluation.ordering import evaluate_ordering_all
from agent_privacy.evaluation.profile import evaluate_profiles
from agent_privacy.evaluation.workflows import (
    reconstruct_workflows,
    workflow_reconstruction_summary,
)
from agent_privacy.experiments.ablations import apply_ablation, apply_ablation_to_row
from agent_privacy.experiments.feature_ablations import feature_options_for_ablation
from agent_privacy.features.extract import extract_features_from_jsonl
from agent_privacy.features.extract import extract_features_from_rows
from agent_privacy.io import iter_jsonl, read_jsonl, write_json, write_jsonl
from agent_privacy.profiling.watchlist import (
    build_profile_watchlist,
    score_watchlist,
    summarize_watchlist_scores,
)
from agent_privacy.profiling.rule_profiler import profile_clusters
from agent_privacy.reporting import write_csv


DEFAULT_DEFENSES = ["M0", "M1", "M2", "M3", "M4", "M6"]
DEFAULT_LEVELS = ["session", "user", "project", "org"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run attacks on an existing dataset directory.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--defenses", nargs="*", default=DEFAULT_DEFENSES)
    parser.add_argument("--levels", nargs="*", default=DEFAULT_LEVELS)
    parser.add_argument(
        "--methods", nargs="*", default=["temporal", "rare", "prefix", "tool", "hybrid"]
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--profile-level", choices=["org", "session"], default="org")
    parser.add_argument("--skip-profile", action="store_true")
    parser.add_argument(
        "--ablations",
        nargs="*",
        default=["none"],
        help="Content ablations to apply after each defense. Use 'none' for the unablated view.",
    )
    parser.add_argument(
        "--feature-ablations",
        nargs="*",
        default=["none"],
        help=(
            "Feature families to disable without rewriting the attack view, e.g. "
            "no_paths no_repo_ids no_shingles no_tool_system no_time_length."
        ),
    )
    parser.add_argument(
        "--write-edge-diagnostics",
        action="store_true",
        help="Write hybrid candidate edge diagnostics for each defense/ablation view.",
    )
    parser.add_argument(
        "--edge-diagnostics-limit",
        type=int,
        default=1000,
        help="Maximum hybrid candidate edges to write per defense/ablation view.",
    )
    parser.add_argument(
        "--write-attack-views",
        action="store_true",
        help="Write transformed attack_view.jsonl files under the output directory.",
    )
    parser.add_argument(
        "--write-reconstructed-workflows",
        action="store_true",
        help="Write ordered reconstructed workflow files for the profile method.",
    )
    parser.add_argument(
        "--write-profile-watchlist",
        action="store_true",
        help="Write profile-derived token watchlists and same-snapshot retrieval metrics.",
    )
    parser.add_argument(
        "--turn-ids",
        type=int,
        nargs="*",
        help="Restrict evaluation to specific ground-truth turn ids, useful for large cumulative traces.",
    )
    parser.add_argument(
        "--open-swe-fast-features",
        action="store_true",
        help="Skip expensive domain/trace scans for large Open-SWE-style code traces.",
    )
    parser.add_argument(
        "--feature-window-chars",
        type=int,
        help="Override the bounded text window used for word/shingle feature extraction.",
    )
    parser.add_argument(
        "--feature-max-shingles",
        type=int,
        help="Override the maximum shingles retained per request.",
    )
    parser.add_argument(
        "--feature-max-words",
        type=int,
        help="Override the maximum normalized words retained per request.",
    )
    parser.add_argument(
        "--skip-ordering",
        action="store_true",
        help="Skip turn-ordering evaluation for linkage-only scale runs.",
    )
    parser.add_argument(
        "--stream-provider-lowcost",
        action="store_true",
        help=(
            "Run provider_lowcost directly from attack_view.jsonl by cache bucket instead of "
            "materializing all request features. Requires M0/none/no-profile streaming path."
        ),
    )
    args = parser.parse_args()

    attack_path = args.dataset_dir / "attack_view.jsonl"
    truth_path = args.dataset_dir / "ground_truth.jsonl"
    truth_rows = read_jsonl(truth_path)
    if args.turn_ids:
        allowed_turns = set(args.turn_ids)
        truth_rows = [row for row in truth_rows if int(row.get("turn_id", -1)) in allowed_turns]
    selected_request_ids = {row["request_id"] for row in truth_rows}

    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True, exist_ok=True)
    feature_methods, control_methods = split_control_methods(args.methods)

    all_cluster_rows: list[dict[str, Any]] = []
    all_ordering_rows: list[dict[str, Any]] = []
    all_profile_rows: list[dict[str, Any]] = []
    all_workflow_rows: list[dict[str, Any]] = []
    all_watchlist_rows: list[dict[str, Any]] = []
    all_utility_rows: list[dict[str, Any]] = []
    run_summary: dict[str, Any] = {
        "dataset_dir": str(args.dataset_dir),
        "requests": len(truth_rows),
        "truth": len(truth_rows),
        "levels": args.levels,
        "ablations": args.ablations,
        "feature_ablations": args.feature_ablations,
        "feature_budget_overrides": {
            "feature_window_chars": args.feature_window_chars,
            "feature_max_shingles": args.feature_max_shingles,
            "feature_max_words": args.feature_max_words,
            "skip_ordering": args.skip_ordering,
            "stream_provider_lowcost": args.stream_provider_lowcost,
        },
        "defenses": {},
    }

    if _can_use_streaming_attack_path(args.defenses, args.ablations, args.skip_profile):
        ablation = args.ablations[0]
        run_dir = args.output / "M0"
        feature_summaries: dict[str, Any] = {}
        for feature_ablation in args.feature_ablations:
            feature_start = time.perf_counter()
            feature_options = feature_options_for_ablation(
                methods=feature_methods,
                fast_features=args.open_swe_fast_features,
                feature_ablation=feature_ablation,
            )
            feature_options = _apply_feature_budget_overrides(feature_options, args)
            stream_provider_only = (
                args.stream_provider_lowcost
                and ablation == "none"
                and feature_methods == ["provider_lowcost"]
            )
            provider_stats: dict[str, Any] = {}
            if stream_provider_only:
                features = {}
            elif ablation == "none":
                features = extract_features_from_jsonl(
                    attack_path,
                    options=feature_options,
                    request_ids=selected_request_ids if args.turn_ids else None,
                )
            else:
                rows = iter_jsonl(attack_path)
                if args.turn_ids:
                    rows = (row for row in rows if row.get("request_id") in selected_request_ids)
                features = extract_features_from_rows(
                    (apply_ablation_to_row(row, ablation) for row in rows),
                    options=feature_options,
                )
            feature_seconds = time.perf_counter() - feature_start
            attack_start = time.perf_counter()
            if stream_provider_only:
                provider_prediction, provider_stats = run_provider_lowcost_from_jsonl(
                    attack_path,
                    options=feature_options,
                    request_ids=selected_request_ids if args.turn_ids else None,
                )
                predictions = {"provider_lowcost": provider_prediction}
                feature_seconds = float(provider_stats.get("feature_extract_seconds", 0.0))
            else:
                predictions = (
                    run_attacks_from_features(features, methods=feature_methods)
                    if feature_methods
                    else {}
                )
            if control_methods:
                request_ids = sorted(features) if features else sorted(selected_request_ids)
                predictions.update(
                    control_predictions(
                        request_ids=request_ids,
                        truth_rows=truth_rows,
                        methods=control_methods,
                        seed=args.seed,
                        levels=args.levels,
                    )
                )
            attack_seconds = (
                float(provider_stats.get("linkage_seconds", 0.0))
                if stream_provider_only
                else time.perf_counter() - attack_start
            )
            evaluation_start = time.perf_counter()
            feature_dir = (
                run_dir
                if feature_ablation == "none"
                else run_dir / f"feature_{feature_ablation}"
            )
            write_json(feature_dir / "predictions.json", predictions)
            if args.write_edge_diagnostics and "hybrid" in feature_methods:
                write_jsonl(
                    feature_dir / "hybrid_candidate_edges.jsonl",
                    hybrid_candidate_edges_from_features(features, limit=args.edge_diagnostics_limit),
                )
            cluster_rows = evaluate_all(predictions, truth_rows, levels=args.levels)
            for row in cluster_rows:
                row["defense"] = "M0"
                row["ablation"] = ablation
                row["feature_ablation"] = feature_ablation
            write_csv(feature_dir / "clustering_metrics.csv", cluster_rows)
            all_cluster_rows.extend(cluster_rows)
            ordering_rows = (
                []
                if args.skip_ordering
                else evaluate_ordering_all(
                    _ordering_rows_from_path(
                        attack_path,
                        request_ids=selected_request_ids if args.turn_ids else None,
                    ),
                    predictions,
                    truth_rows,
                )
            )
            for row in ordering_rows:
                row["defense"] = "M0"
                row["ablation"] = ablation
                row["feature_ablation"] = feature_ablation
            write_csv(feature_dir / "ordering_metrics.csv", ordering_rows)
            all_ordering_rows.extend(ordering_rows)
            workflow_rows: list[dict[str, Any]] = []
            if args.write_reconstructed_workflows:
                workflow_method = "provider_lowcost" if "provider_lowcost" in predictions else "hybrid"
                if workflow_method in predictions:
                    ordering_rows_full = _ordering_rows_from_path(
                        attack_path,
                        request_ids=selected_request_ids if args.turn_ids else None,
                        include_messages=True,
                    )
                    workflows = reconstruct_workflows(
                        ordering_rows_full,
                        predictions[workflow_method]["session"],
                        truth_rows,
                    )
                    write_jsonl(feature_dir / "reconstructed_workflows.jsonl", workflows)
                    workflow_rows = workflow_reconstruction_summary(workflows)
                    for row in workflow_rows:
                        row["defense"] = "M0"
                        row["ablation"] = ablation
                        row["feature_ablation"] = feature_ablation
                        row["method"] = workflow_method
                        row["level"] = "session"
                    write_csv(feature_dir / "workflow_reconstruction_metrics.csv", workflow_rows)
                    all_workflow_rows.extend(workflow_rows)
            evaluation_seconds = time.perf_counter() - evaluation_start
            feature_summaries[feature_ablation] = {
                "requests": len(features) if features else len(truth_rows),
                "cluster_metric_rows": len(cluster_rows),
                "ordering_metric_rows": len(ordering_rows),
                "workflow_metric_rows": len(workflow_rows),
                "profile_metric_rows": 0,
                "feature_seconds": feature_seconds,
                "attack_seconds": attack_seconds,
                "evaluation_seconds": evaluation_seconds,
                "max_rss_mb": _max_rss_mb(),
                "stream_provider_lowcost_stats": provider_stats,
                "cache_scan_seconds": provider_stats.get("cache_scan_seconds", 0.0),
                "candidate_pairs_considered": provider_stats.get(
                    "candidate_pairs_considered", 0
                ),
                "candidate_pairs_linked": provider_stats.get("candidate_pairs_linked", 0),
            }
        run_summary["defenses"]["M0"] = {
            "requests": len(truth_rows),
            "streaming_features": True,
            "ablations": {
                ablation: {
                    "requests": len(truth_rows),
                    "feature_ablations": feature_summaries,
                    "cluster_metric_rows": sum(
                        item["cluster_metric_rows"] for item in feature_summaries.values()
                    ),
                    "ordering_metric_rows": sum(
                        item["ordering_metric_rows"] for item in feature_summaries.values()
                    ),
                    "workflow_metric_rows": sum(
                        item["workflow_metric_rows"] for item in feature_summaries.values()
                    ),
                    "profile_metric_rows": 0,
                }
            },
            "cluster_metric_rows": sum(
                item["cluster_metric_rows"] for item in feature_summaries.values()
            ),
            "ordering_metric_rows": sum(
                item["ordering_metric_rows"] for item in feature_summaries.values()
            ),
            "workflow_metric_rows": sum(
                item["workflow_metric_rows"] for item in feature_summaries.values()
            ),
            "profile_metric_rows": 0,
        }
        write_csv(args.output / "clustering_metrics_all.csv", all_cluster_rows)
        write_csv(args.output / "ordering_metrics_all.csv", all_ordering_rows)
        write_csv(args.output / "workflow_reconstruction_metrics_all.csv", all_workflow_rows)
        write_csv(args.output / "profile_metrics_all.csv", all_profile_rows)
        write_csv(args.output / "profile_watchlist_metrics_all.csv", all_watchlist_rows)
        write_csv(args.output / "utility_metrics_all.csv", all_utility_rows)
        write_json(args.output / "run_summary.json", run_summary)
        print(json.dumps(run_summary, indent=2, sort_keys=True))
        return

    base_rows = read_jsonl(attack_path)
    if args.turn_ids:
        base_rows = [row for row in base_rows if row.get("request_id") in selected_request_ids]
    run_summary["requests"] = len(base_rows)
    for defense in args.defenses:
        defense_dir = args.output / defense
        defended_rows = apply_defense(base_rows, defense, seed=args.seed)
        defense_summary: dict[str, Any] = {"requests": len(defended_rows), "ablations": {}}

        for ablation in args.ablations:
            run_rows = apply_ablation(defended_rows, ablation)
            run_dir = defense_dir if ablation == "none" else defense_dir / ablation
            if args.write_attack_views:
                write_jsonl(run_dir / "attack_view.jsonl", run_rows)

            utility_row = summarize_utility(
                base_rows,
                run_rows,
                defense=defense,
                ablation=ablation,
            )
            utility_row["feature_ablation"] = "none"
            write_csv(run_dir / "utility_metrics.csv", [utility_row])
            all_utility_rows.append(utility_row)

            ablation_summary: dict[str, Any] = {
                "requests": len(run_rows),
                "utility_metric_rows": 1,
                "feature_ablations": {},
            }
            for feature_ablation in args.feature_ablations:
                feature_start = time.perf_counter()
                feature_options = feature_options_for_ablation(
                    methods=feature_methods,
                    fast_features=args.open_swe_fast_features,
                    feature_ablation=feature_ablation,
                )
                feature_options = _apply_feature_budget_overrides(feature_options, args)
                features = extract_features_from_rows(run_rows, options=feature_options)
                feature_seconds = time.perf_counter() - feature_start
                attack_start = time.perf_counter()
                predictions = (
                    run_attacks_from_features(features, methods=feature_methods)
                    if feature_methods
                    else {}
                )
                if control_methods:
                    predictions.update(
                        control_predictions(
                            request_ids=sorted(features),
                            truth_rows=truth_rows,
                            methods=control_methods,
                            seed=args.seed,
                            levels=args.levels,
                        )
                    )
                attack_seconds = time.perf_counter() - attack_start
                evaluation_start = time.perf_counter()
                feature_dir = (
                    run_dir
                    if feature_ablation == "none"
                    else run_dir / f"feature_{feature_ablation}"
                )
                write_json(feature_dir / "predictions.json", predictions)
                if args.write_edge_diagnostics and "hybrid" in feature_methods:
                    write_jsonl(
                        feature_dir / "hybrid_candidate_edges.jsonl",
                        hybrid_candidate_edges_from_features(
                            features, limit=args.edge_diagnostics_limit
                        ),
                    )

                cluster_rows = evaluate_all(predictions, truth_rows, levels=args.levels)
                for row in cluster_rows:
                    row["defense"] = defense
                    row["ablation"] = ablation
                    row["feature_ablation"] = feature_ablation
                write_csv(feature_dir / "clustering_metrics.csv", cluster_rows)
                all_cluster_rows.extend(cluster_rows)
                ordering_rows = (
                    [] if args.skip_ordering else evaluate_ordering_all(run_rows, predictions, truth_rows)
                )
                for row in ordering_rows:
                    row["defense"] = defense
                    row["ablation"] = ablation
                    row["feature_ablation"] = feature_ablation
                write_csv(feature_dir / "ordering_metrics.csv", ordering_rows)
                all_ordering_rows.extend(ordering_rows)
                workflow_rows: list[dict[str, Any]] = []
                if args.write_reconstructed_workflows:
                    workflow_method = (
                        "provider_lowcost" if "provider_lowcost" in predictions else "hybrid"
                    )
                    if workflow_method in predictions:
                        workflows = reconstruct_workflows(
                            run_rows,
                            predictions[workflow_method]["session"],
                            truth_rows,
                        )
                        write_jsonl(feature_dir / "reconstructed_workflows.jsonl", workflows)
                        workflow_rows = workflow_reconstruction_summary(workflows)
                        for row in workflow_rows:
                            row["defense"] = defense
                            row["ablation"] = ablation
                            row["feature_ablation"] = feature_ablation
                            row["method"] = workflow_method
                            row["level"] = "session"
                        write_csv(feature_dir / "workflow_reconstruction_metrics.csv", workflow_rows)
                        all_workflow_rows.extend(workflow_rows)

                profile_rows: list[dict[str, Any]] = []
                watchlist_rows: list[dict[str, Any]] = []
                if not args.skip_profile:
                    profile_method = "hybrid" if "hybrid" in predictions else next(iter(predictions))
                    profile_labels = predictions[profile_method][args.profile_level]
                    profiles = profile_clusters(run_rows, profile_labels)
                    write_json(
                        feature_dir / f"hybrid_{args.profile_level}_profiles.json",
                        profiles,
                    )
                    profile_rows = evaluate_profiles(profiles, truth_rows, profile_labels)
                    for row in profile_rows:
                        row["defense"] = defense
                        row["ablation"] = ablation
                        row["feature_ablation"] = feature_ablation
                        row["method"] = profile_method
                        row["level"] = args.profile_level
                    write_csv(feature_dir / "profile_metrics.csv", profile_rows)
                    all_profile_rows.extend(profile_rows)
                    if args.write_profile_watchlist:
                        watchlist = build_profile_watchlist(profiles)
                        write_json(feature_dir / "profile_watchlist.json", watchlist)
                        watchlist_rows = score_watchlist(
                            watchlist,
                            run_rows,
                            truth_rows,
                            profile_labels,
                            truth_level=args.profile_level,
                        )
                        for row in watchlist_rows:
                            row["defense"] = defense
                            row["ablation"] = ablation
                            row["feature_ablation"] = feature_ablation
                            row["method"] = profile_method
                            row["level"] = args.profile_level
                        write_csv(feature_dir / "profile_watchlist_metrics.csv", watchlist_rows)
                        write_csv(
                            feature_dir / "profile_watchlist_summary.csv",
                            summarize_watchlist_scores(watchlist_rows),
                        )
                        all_watchlist_rows.extend(watchlist_rows)
                evaluation_seconds = time.perf_counter() - evaluation_start

                ablation_summary["feature_ablations"][feature_ablation] = {
                    "requests": len(run_rows),
                    "cluster_metric_rows": len(cluster_rows),
                    "ordering_metric_rows": len(ordering_rows),
                    "workflow_metric_rows": len(workflow_rows),
                    "profile_metric_rows": len(profile_rows),
                    "watchlist_metric_rows": len(watchlist_rows),
                    "feature_seconds": feature_seconds,
                    "attack_seconds": attack_seconds,
                    "evaluation_seconds": evaluation_seconds,
                    "max_rss_mb": _max_rss_mb(),
                }

            ablation_summary["cluster_metric_rows"] = sum(
                item["cluster_metric_rows"]
                for item in ablation_summary["feature_ablations"].values()
            )
            ablation_summary["profile_metric_rows"] = sum(
                item["profile_metric_rows"]
                for item in ablation_summary["feature_ablations"].values()
            )
            ablation_summary["ordering_metric_rows"] = sum(
                item["ordering_metric_rows"]
                for item in ablation_summary["feature_ablations"].values()
            )
            ablation_summary["workflow_metric_rows"] = sum(
                item["workflow_metric_rows"]
                for item in ablation_summary["feature_ablations"].values()
            )
            ablation_summary["watchlist_metric_rows"] = sum(
                item["watchlist_metric_rows"]
                for item in ablation_summary["feature_ablations"].values()
            )
            defense_summary["ablations"][ablation] = ablation_summary

        defense_summary["cluster_metric_rows"] = sum(
            item["cluster_metric_rows"] for item in defense_summary["ablations"].values()
        )
        defense_summary["profile_metric_rows"] = sum(
            item["profile_metric_rows"] for item in defense_summary["ablations"].values()
        )
        defense_summary["ordering_metric_rows"] = sum(
            item["ordering_metric_rows"] for item in defense_summary["ablations"].values()
        )
        defense_summary["workflow_metric_rows"] = sum(
            item["workflow_metric_rows"] for item in defense_summary["ablations"].values()
        )
        defense_summary["watchlist_metric_rows"] = sum(
            item["watchlist_metric_rows"] for item in defense_summary["ablations"].values()
        )
        defense_summary["utility_metric_rows"] = sum(
            item["utility_metric_rows"] for item in defense_summary["ablations"].values()
        )
        run_summary["defenses"][defense] = defense_summary

    write_csv(args.output / "clustering_metrics_all.csv", all_cluster_rows)
    write_csv(args.output / "ordering_metrics_all.csv", all_ordering_rows)
    write_csv(args.output / "workflow_reconstruction_metrics_all.csv", all_workflow_rows)
    write_csv(args.output / "profile_metrics_all.csv", all_profile_rows)
    write_csv(args.output / "profile_watchlist_metrics_all.csv", all_watchlist_rows)
    write_csv(args.output / "utility_metrics_all.csv", all_utility_rows)
    write_json(args.output / "run_summary.json", run_summary)
    print(json.dumps(run_summary, indent=2, sort_keys=True))


def _can_use_streaming_attack_path(
    defenses: list[str], ablations: list[str], skip_profile: bool
) -> bool:
    return defenses == ["M0"] and len(ablations) == 1 and skip_profile


def _ordering_rows_from_path(
    path: Path, request_ids: set[str] | None, *, include_messages: bool = False
) -> list[dict[str, Any]]:
    rows = []
    for row in iter_jsonl(path):
        if request_ids is not None and row.get("request_id") not in request_ids:
            continue
        item = {"request_id": row["request_id"], "timestamp": row["timestamp"]}
        if include_messages:
            item["messages"] = row.get("messages", [])
        rows.append(item)
    return rows


def _apply_feature_budget_overrides(options: Any, args: argparse.Namespace) -> Any:
    updates: dict[str, int] = {}
    if args.feature_window_chars is not None:
        updates["text_feature_window_chars"] = args.feature_window_chars
    if args.feature_max_shingles is not None:
        updates["max_shingles"] = args.feature_max_shingles
    if args.feature_max_words is not None:
        updates["max_words"] = args.feature_max_words
    return replace(options, **updates) if updates else options


def _max_rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return usage / 1024


if __name__ == "__main__":
    main()
