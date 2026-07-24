# Artifact Index

This project is organized around three artifact layers:

1. **Code** under `src/agent_privacy/`.
2. **Dataset catalogs and local payloads** under `artifacts/`.
3. **Result catalogs, local raw outputs, and paper tables** under `results/` and `docs/tables/`.

The normal Git clone contains the catalogs, cards, curated tables, and a synthetic smoke fixture;
large dataset and raw result payloads are ignored. In the complete local workspace,
historical/debug runs and datasets remain under `results/_archive/` and
`artifacts/datasets/_archive/` without deletion. For paper writing, use the curated tables below.
For request-level audit, obtain the optional release asset or regenerate the referenced local run.

Release catalogs: `artifacts/dataset-manifest.json` and `results/result-manifest.json`.
Upload procedure: `docs/github-release.md`.

## Curated Tables and Supplementary Evidence

| Purpose | Artifact |
| --- | --- |
| Open-SWE scaffold/split attack matrix | `docs/tables/open_swe_2x2_attack_matrix.md` |
| Open-SWE scaffold/split bootstrap CI | `docs/tables/open_swe_2x2_bootstrap_ci.md` |
| Open-SWE dataset matrix | `docs/tables/open_swe_2x2_dataset_matrix.csv` |
| OpenHands/minimax sample-size sweep | `docs/tables/open_swe_openhands_minimax_sample_size_sweep.md` |
| SWE-agent/minimax local reservoir sweep | `docs/tables/open_swe_sweagent_minimax_local_reservoir_sweep.md` |
| Provider-lowcost two-stage chain | `docs/tables/open_swe_provider_lowcost.md` |
| Main Open-SWE session baselines, CIs, and ordering | `docs/tables/open_swe_main_session_evidence.md` |
| Pair imbalance, false-link rate, and cost-ratio sensitivity | `docs/tables/open_swe_pairwise_cost_audit.md` |
| Open-SWE direct repository/owner exposure audit | `docs/tables/open_swe_direct_exposure_audit.md` |
| Open-SWE candidate recall and banded bottom-k shingle-sketch diagnostic | `docs/tables/open_swe_candidate_diagnostics.md` |
| Open-SWE strict content-removal stress test | `docs/tables/open_swe_strict_signal_removal.md` |
| Open-SWE strict-removal second-stage semantic project linkage | `docs/tables/open_swe_strict_semantic_project_linkage.md` |
| SWE-agent strict-removal second-stage semantic project linkage | `docs/tables/open_swe_sweagent_strict_semantic_project_linkage.md` |
| Source-calibrated zero-target-label cross-scaffold transfer | `docs/tables/open_swe_cross_scaffold_zero_tuning.md` |
| Full 1,000-workflow sensitivity bootstrap CIs | `docs/tables/open_swe_carp_full_1000_bootstrap_ci.md`; `docs/tables/open_swe_hybrid_full_1000_bootstrap_ci.md` |
| Open-SWE cross-workflow entity validity and repository/owner-anchor control | `docs/tables/open_swe_cross_workflow_entity_validity.md` |
| Provider-lowcost longitudinal fixed-budget snapshots | `docs/tables/open_swe_provider_lowcost_longitudinal.md` |
| Provider-lowcost full-snapshot fixed-turn longitudinal results | `docs/tables/open_swe_provider_lowcost_longitudinal_full_turns.md` |
| CARP/provider-lowcost candidate reduction and cost model | `docs/tables/open_swe_provider_lowcost_cost_model.md` |
| Feature ablation | `docs/tables/open_swe_gap_feature_ablation.md` |
| Turn ordering | `docs/tables/open_swe_gap_ordering.md` |
| Field-level profile reconstruction | `docs/tables/open_swe_gap_profile.md` |
| Rule vs structured-evidence profile reconstruction | `docs/tables/open_swe_structured_profile_comparison.md` |
| Calibrated dense-semantic profile reconstruction | `docs/tables/open_swe_semantic_profile_comparison.md` |
| Semantic-only profile evidence audit | `docs/tables/open_swe_semantic_profile_novel_evidence.md` |
| Random/oracle-size controls | `docs/tables/open_swe_controls_sample100.md` |
| Bootstrap CI for controls | `docs/tables/open_swe_controls_sample100_bootstrap_ci.md` |
| Threshold/runtime sensitivity | `docs/tables/open_swe_lowcost_threshold_sweep.md`; `docs/tables/open_swe_heldout_threshold_robustness.md` |
| Profile truth-cluster upper bound | `docs/tables/open_swe_profile_bounds.md` |
| L1-L5 profile risk stratification | `docs/tables/open_swe_profile_risk_levels.md` |
| Runtime/cost scale table | `docs/tables/open_swe_runtime_cost.md` |
| Controlled 10K--100K CARP scaling | `docs/tables/carp_synthetic_scale.md` |
| Observation-equivalence impossibility bound and controlled validation | `docs/tables/observation_indistinguishability.md` |
| Synthetic scale/difficulty/profile sweep | `docs/tables/synthetic_matrix_summary.md` |
| Open-SWE user overlay linkage/longitudinal tables | `docs/tables/open_swe_user_overlay_linkage_summary.md`; `docs/tables/open_swe_user_overlay_longitudinal.md` |
| Open-SWE user overlay feature ablation | `docs/tables/open_swe_user_overlay_user_ablation.md` |
| Open-SWE user overlay profile reconstruction | `docs/tables/open_swe_user_overlay_profile_reconstruction.md` |
| Open-SWE user overlay 12k bootstrap CI | `docs/tables/open_swe_user_overlay_12k_bootstrap_ci.md` |
| Open-SWE user overlay warm-start watchlist | `docs/tables/open_swe_user_overlay_warm_start_watchlist.md` |
| Open-SWE user overlay warm-start target retrieval | `docs/tables/open_swe_user_overlay_warm_start_retrieval.md` |
| tau-bench historical non-code Agent linkage | `docs/tables/tau_bench_historical_sample200_provider_lowcost.md` |
| Held-out tau-bench baselines, CIs, domain breakdown, and high-precision operating point | `docs/tables/tau_bench_historical_evidence.md`; `docs/tables/tau_bench_historical_operating_points.md` |
| Cross-domain stable-handle audit | `docs/tables/cross_domain_stable_handle_audit.md` |
| Held-out natural tau stable-handle user linkage | `docs/tables/tau_bench_stable_user_linkage.md` |
| tau-bench concurrency/jitter and intent-rephrasing stress | `docs/tables/tau_bench_temporal_stress.md` |
| tau-bench time-independent CARP-Content ablation | `docs/tables/tau_bench_content_linkage_ablation.md` |
| tau-bench natural historical user watchlist | `docs/tables/tau_bench_natural_user_watchlist.md` |
| tau-bench HNSW dense-ANN baseline | `docs/tables/tau_bench_hnsw_ann_baseline.md` |
| tau-bench T3 three-layer overlay linkage | `docs/tables/tau_bench_overlay_t3_first_2500_provider_lowcost.md` |
| tau-bench T3 cross-cache entity percolation | `docs/tables/tau_bench_t3_entity_percolation.md` |
| tau-bench T3 cross-snapshot entity watchlist | `docs/tables/tau_bench_t3_entity_watchlist.md` |
| tau-bench T3 anchor statistics and robustness sweeps | `docs/tables/tau_bench_t3_anchor_statistics.md`; `docs/tables/tau_bench_t3_anchor_robustness.md` |
| CARP stage contract and parameter scope | `docs/tables/carp_stage_parameters.md` |
| Dataset-specific label and harm semantics | `docs/tables/dataset_label_semantics.md` |
| T3, watchlist, and semantic-profile bootstrap CIs | `docs/tables/paper_extension_bootstrap_ci.md` |
| Exploratory mitigation frontier (excluded from the submission) | `docs/tables/open_swe_defense_utility_frontier.md` |
| Redacted reconstructed profile examples | `docs/redacted-profile-examples.md` |
| Provider-view audit summary | `docs/tables/provider_view_audit_summary.md` |
| tau-bench historical provider-view audit | `docs/tables/tau_bench_historical_provider_view_audit.md` |
| tau-bench T3 provider-view audit | `docs/tables/tau_bench_overlay_t3_provider_view_audit.md` |
| Paper readiness checklist | `docs/tables/paper_experiment_readiness.md` |

## Submission Package

| Purpose | Artifact |
| --- | --- |
| English AAAI manuscript | `docs/overleaf/api.tex` |
| Supplementary parameter, validity, baseline, and impossibility analysis | `docs/overleaf/supplement.tex` |
| Bibliography | `docs/overleaf/references.bib` |
| Supplied AAAI LaTeX style and bibliography style | `docs/overleaf/aaai.sty`; `docs/overleaf/aaai.bst` |
| Visual overview of provider-side linkage and longitudinal reconstruction | `docs/overleaf/figures/carp_pipeline.pdf` |
| Editable PowerPoint source for the main framework figure | `docs/overleaf/figures/provider_linkage_overview_editable.pptx` |
| Supplementary evidence-layer figure | `docs/overleaf/figures/evidence_layers.pdf` |
| Hierarchical longitudinal-linkage figure | `docs/overleaf/figures/t3_longitudinal.pdf` |
| Four-panel channels, concurrency, Agent-state, and impossibility figure | `docs/overleaf/figures/results_overview.pdf` |
| Frozen submission scope | `docs/paper/submission-scope.md` |
| Claim-to-evidence audit | `docs/paper/claim-audit.md` |
| Artifact release checklist | `docs/paper/artifact-release-checklist.md` |
| Submission readiness report | `docs/paper/submission-readiness-report.md` |

The pre-review migration fit seven body pages; the current review revision adds a supplement and
requires a fresh Overleaf pdfLaTeX page/layout check. Defense remains limited to mitigation
implications; it is not a research question, contribution, or main-table result.

## Dataset Cards

| Dataset | Card |
| --- | --- |
| Open-SWE-Traces adapted | `docs/dataset-card-open-swe-traces-adapted.md` |
| SWE-bench Lite adapted | `docs/dataset-card-swe-bench-lite-adapted.md` |
| Synthetic Dataset A | `docs/dataset-card-synthetic-a.md` |
| tau-bench historical adapted | `docs/dataset-card-tau-bench-adapted.md` |

## Narrative Documents

| Purpose | Document |
| --- | --- |
| Original research plan | `docs/llm-agent-api-privacy-research-plan.md` |
| Classmate-facing background note | `docs/paper/background-for-classmate-zh.md` |
| Historical plain-language planning draft (superseded) | `docs/paper/plain-paper-draft-zh.md` |
| Plain-language paper story outline | `docs/paper/paper-story-outline-zh.md` |
| CARP method note | `docs/paper/carp-method.md` |
| Paper strengthening TODO | `docs/paper/paper-strengthening-todolist.md` |
| Mitigation implications from linkage-surface controls | `docs/paper/content-linkage-defense-frontier.md` |
| Ethics and governance note | `docs/paper/ethics-and-governance.md` |
| Heterogeneous Agent dataset plan | `docs/paper/heterogeneous-agent-dataset-plan.md` |
| Threat model | `docs/threat-model.md` |
| Provider-view schema | `docs/data-schema.md` |
| Code map | `docs/code-map.md` |
| Open-SWE user overlay injection plan | `docs/open-swe-user-overlay-injection-plan.md` |
| Open-SWE results summary | `docs/open-swe-traces-results-summary.md` |
| SWE-bench results summary | `docs/swe-bench-lite-repaired-results-summary.md` |
| Paper experiment todo/readiness | `docs/paper-experiment-todolist.md` |
| Result archive policy | `results/_archive/README.md` |
| Dataset archive policy | `artifacts/datasets/_archive/README.md` |

## Code Map

For a more detailed implementation map, see `docs/code-map.md`.

| Package | Responsibility |
| --- | --- |
| `agent_privacy.data` | Dataset generators/importers, provider-view audit, sampling, turn-delta conversion, longitudinal snapshots. |
| `agent_privacy.features` | Provider-visible feature extraction. |
| `agent_privacy.attacks` | Baseline, hybrid, and provider-lowcost attacks. |
| `agent_privacy.evaluation` | Clustering, ordering, workflow, profile, and control-baseline evaluation. |
| `agent_privacy.profiling` | Rule, structured-evidence, and calibrated dense-semantic profile reconstruction plus profile/entity watchlists. |
| `agent_privacy.defenses` | Redaction/minimization transforms and utility proxies. |
| `agent_privacy.experiments` | CLI entry points for runs, sweeps, confidence intervals, summaries, and dataset cards. |

## Dataset B Configs

| Purpose | Config |
| --- | --- |
| Open-SWE user overlay U3 multi-signal main setting | `configs/open_swe_user_overlay_u3.json` |
| Open-SWE user overlay U4 hard shared setting | `configs/open_swe_user_overlay_u4_hard_shared.json` |
| tau-bench T3 non-code three-layer overlay | `configs/tau_bench_overlay_t3.json` |

## Regeneration Commands

Use these commands to rebuild the main derived tables from existing datasets/results:

```bash
uv run python -m agent_privacy.experiments.summarize_open_swe --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_provider_lowcost --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_open_swe_entity_validity --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_open_swe_main_session --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_longitudinal --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_gap_results --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_controls --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_runtime_cost --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_lowcost_cost_model --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_user_overlay --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_user_overlay_profiles --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_warm_start_watchlist --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_warm_start_retrieval --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_tau_bench --output-dir docs/tables
uv run python -m agent_privacy.experiments.generate_paper_figures --output-dir docs/paper/figures
uv run python -m agent_privacy.experiments.summarize_sweagent_reservoir --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_defense_frontier --output-dir docs/tables
uv run python -m agent_privacy.experiments.write_dataset_cards --output-dir docs/tables
```

The control CI and threshold sweep are experiment runs rather than pure summaries:

```bash
uv run python -m agent_privacy.experiments.bootstrap_ci \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --predictions results/open_swe_controls_sample100_turns_3_6_9_12/M0/predictions.json \
  --output docs/tables/open_swe_controls_sample100_bootstrap_ci.csv \
  --methods provider_lowcost random oracle_size_random \
  --levels session project org \
  --turn-ids 3 6 9 12 \
  --iterations 200

uv run python -m agent_privacy.experiments.sweep_lowcost_thresholds \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --output docs/tables/open_swe_lowcost_threshold_sweep.csv \
  --turn-ids 3 6 9 12

uv run python -m agent_privacy.experiments.bootstrap_open_swe \
  --output-dir docs/tables \
  --iterations 200

uv run python -m agent_privacy.experiments.run_synthetic_matrix \
  --output-dir results/synthetic_matrix

uv run python -m agent_privacy.experiments.profile_examples \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --predictions results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_profile/M0/predictions.json \
  --output docs/redacted-profile-examples.md \
  --limit 3
```

For the large Dataset B provider-scale run, use the cache-bucket streamed low-cost path rather
than the high-fidelity `hybrid` baseline:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_user_overlay_u3_mixed_1000_snapshots/first_12000_requests \
  --output results/open_swe_user_overlay_u3_first_12000_provider_lowcost_streamed \
  --defenses M0 \
  --levels session user project org \
  --methods provider_lowcost \
  --ablations none \
  --feature-ablations none \
  --skip-profile \
  --open-swe-fast-features \
  --feature-window-chars 24000 \
  --feature-max-shingles 1200 \
  --feature-max-words 1500 \
  --skip-ordering \
  --stream-provider-lowcost
```

The streamed path keeps the provider-lowcost output identical to the materialized budgeted run
while reducing Dataset B U3 12k peak RSS from `3333.051 MB` to `1301.781 MB` in the recorded local
run. It uses repeated JSONL scans as a prototype implementation; a production provider could
route requests into cache-bucket queues in one pass.
