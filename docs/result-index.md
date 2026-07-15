# Result Index

The `results/` root is reserved for current paper-facing, boundary, and active experiment runs, but
raw payloads are ignored by Git. A clean clone contains `results/result-manifest.json` and the
canonical aggregate outputs in `docs/tables/`. The optional GitHub Release result ZIP contains a
curated subset of metrics, run summaries, and cluster assignments; it excludes prompt/truth copies,
reconstructed workflow dumps, large profile objects, and archives. The complete local workspace
keeps historical/debug/failed runs under `results/_archive/` without deletion.

Prefer `docs/tables/` for writing. Use this index and the manifest when tracing a table back to a raw
run, then download the release asset or regenerate the run with `docs/reproduction.md`.

## Curated Paper Runs

| Result Directory | Purpose | Main Outputs |
| --- | --- | --- |
| `results/open_swe_provider_lowcost_cumulative_sample100_cluster` | Provider-lowcost chain on cumulative Open-SWE sample100 fixed turns. | `clustering_metrics_all.csv`, `workflow_reconstruction_metrics_all.csv`, reconstructed workflows under `M0/`. |
| `results/open_swe_provider_lowcost_turn_delta_sample100_cluster` | Provider-lowcost turn-delta control. | Same as above. |
| `results/open_swe_controls_sample100_turns_3_6_9_12` | Random/oracle-size controls plus provider-lowcost. | `clustering_metrics_all.csv`, `M0/predictions.json`. |
| `results/open_swe_provider_lowcost_longitudinal_full_first_1000_turns` | Full snapshot fixed-turn longitudinal 1k. | Clustering and workflow reconstruction metrics. |
| `results/open_swe_provider_lowcost_longitudinal_full_first_4000_turns` | Full snapshot fixed-turn longitudinal 4k. | Clustering and workflow reconstruction metrics. |
| `results/open_swe_provider_lowcost_longitudinal_full_first_8000_turns` | Full snapshot fixed-turn longitudinal 8k. | Clustering and workflow reconstruction metrics. |
| `results/open_swe_provider_lowcost_longitudinal_full_first_12000_turns` | Full snapshot fixed-turn longitudinal 12k. | Clustering and workflow reconstruction metrics. |
| `results/open_swe_traces_raw_1000_sample100_turns_3_6_9_12_feature_ablation_full_features` | Cumulative feature ablation. | `clustering_metrics_all.csv`, `ordering_metrics_all.csv`. |
| `results/open_swe_traces_raw_1000_turn_delta_sample100_feature_ablation_full_features` | Turn-delta feature ablation. | `clustering_metrics_all.csv`, `ordering_metrics_all.csv`. |
| `results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_profile` | Open-SWE technical profile reconstruction. | `profile_metrics_all.csv`, predictions for profile bounds. |
| `results/open_swe_traces_raw_1000_sample100_turns_3_6_9_12_defense_probe_fast` | Preliminary baseline defenses. | Clustering and utility proxy metrics. |
| `results/open_swe_traces_raw_1000_sample100_turns_3_6_9_12_selective_mitigation_fast` | Selective workspace/path mitigation probe. | Clustering and utility proxy metrics. |
| `results/open_swe_provider_lowcost_cumulative_sample100_cluster_timed` | Timed provider-lowcost sample100 run. | `run_summary.json` records feature/attack/evaluation seconds; workflow reconstruction metrics. |
| `results/synthetic_matrix` | Controlled synthetic scale/difficulty/profile matrix. | `synthetic_matrix_*.csv`, `synthetic_matrix_summary.md`. |
| `results/open_swe_user_overlay_u3_first_1000_m0_fast` | Dataset B U3 first-1k high-fidelity smoke linkage run. | Session/user/project/org clustering metrics. |
| `results/open_swe_user_overlay_u4_first_1000_m0_fast` | Dataset B U4 hard-shared first-1k high-fidelity smoke linkage run. | Session/user/project/org clustering metrics. |
| `results/open_swe_user_overlay_u3_first_12000_provider_lowcost_budgeted` | Dataset B U3 12k materialized provider-lowcost budgeted scale run. | `run_summary.json` records feature/attack/evaluation seconds and peak RSS; clustering metrics. |
| `results/open_swe_user_overlay_u3_first_{1000,4000,8000,12000}_provider_lowcost_streamed` | Dataset B U3 cache-bucket streamed provider-lowcost longitudinal scale runs. | Clustering metrics plus runtime/RSS/cache-bucket stats in `run_summary.json`. |
| `results/open_swe_user_overlay_u4_first_{1000,4000,8000,12000}_provider_lowcost_streamed` | Dataset B U4 hard-shared cache-bucket streamed provider-lowcost longitudinal scale runs. | Clustering metrics plus runtime/RSS/cache-bucket stats in `run_summary.json`. |
| `results/tau_bench_historical_sample200_provider_lowcost` | Direct non-code tau-bench historical linkage. | Session linkage metrics and provider-view ablations. |
| `results/tau_bench_overlay_t3_first_2500_provider_lowcost` | T3 bucket-local baseline. | Session/user/project/org predictions and metrics. |
| `results/tau_bench_overlay_t3_first_2500_provider_lowcost_stable_handles` | T3 cross-cache typed stable-handle percolation. | Improved hierarchy predictions used by the watchlist and paired bootstrap. |
| `results/open_swe_profile_structured_comparison` | Rule versus structured technical profiling. | Audited predicted- and truth-cluster profile outputs. |
| `results/open_swe_semantic_profile` | Org-disjoint MiniLM profile baseline. | Calibration/test split, semantic predictions, evidence audit, and runtime summary. |
| `results/open_swe_context_only_sample100_turns` | Bounded cumulative-context diagnostic on the fixed-turn sample100 view. | Session-only predictions used to isolate how much of CARP session linkage is explained by context/identifier rules. |

## Open-SWE 2x2 And Sample-Size Runs

The Open-SWE scaffold/split matrix is summarized in `docs/tables/open_swe_2x2_attack_matrix.md`.
The OpenHands/minimax sample-size sweep is summarized in
`docs/tables/open_swe_openhands_minimax_sample_size_sweep.md`.
The SWE-agent/minimax local-from-raw500 reservoir sweep is summarized in
`docs/tables/open_swe_sweagent_minimax_local_reservoir_sweep.md`.

Relevant result directory patterns:

- `results/open_swe_traces_openhands_*`
- `results/open_swe_traces_sweagent_*`

Use `docs/tables/open_swe_2x2_dataset_matrix.csv` to map each row to its dataset and audit
document.

## SWE-bench Runs

| Result Directory Pattern | Purpose |
| --- | --- |
| `results/swe_bench_lite_natural_balanced_*` | Natural repaired workflow boundary results. |
| `results/swe_bench_lite_repaired_*` | Explicit repair-context variants and ablations. |

These are validation/boundary results, not raw provider-log evidence.

## Active But Secondary Runs

These remain in the `results/` root because they are still referenced by summary docs or are
useful boundary evidence, but they are not the first paths to cite:

| Pattern | Purpose |
| --- | --- |
| `results/open_swe_provider_lowcost_longitudinal_first_*` | Earlier longitudinal provider-lowcost runs without the current full fixed-turn framing. |
| `results/open_swe_traces_raw_1000_m0` and `results/open_swe_traces_raw_1000_no_workspace_paths` | Large historical full-context raw/no-workspace comparison. |
| `results/open_swe_traces_raw_1000_turn12_*` and `results/open_swe_traces_raw_1000_turns_3_6_9_12_*` | Development runs that support the Open-SWE results summary. |
| `results/open_swe_traces_raw_1000_turn_delta_feature_ablation` | Earlier full turn-delta feature ablation; curated tables use the sample100 full-feature ablation rows. |
| `results/open_swe_user_overlay_u*_first_*_m0_ablation` | Dataset B high-fidelity ablation inputs summarized in `docs/tables/open_swe_user_overlay_user_ablation.md`. |

## Archived Historical / Debug Runs

Archived runs live under `results/_archive/`; see `results/_archive/README.md` for the policy.
The archive is non-destructive and exists to keep active result discovery readable.

| Archive Path | Contents |
| --- | --- |
| `results/_archive/failed_empty/` | Empty or interrupted runs, including failed full 12k high-fidelity Dataset B attempts. |
| `results/_archive/debug_diagnostics/` | Edge diagnostics, no-workspace diagnostics, and superseded optimized Dataset B smoke output. |
| `results/_archive/legacy_mvp_smoke/` | Early MVP and smoke outputs. |
| `results/_archive/legacy_open_swe_samples/` | Early raw/repaired/sample Open-SWE result outputs. |
| `results/_archive/legacy_provider_lowcost/` | Early provider-lowcost chain/cluster prototypes. |

## Current Known Gaps

- Historical longitudinal runs do not record full wall-clock runtime or candidate-edge counts.
  `docs/tables/open_swe_runtime_cost.md` now includes measured runtime for the timed sample100
  provider-lowcost rerun and Dataset B streamed/materialized provider-lowcost 12k runs, while
  older longitudinal rows still report `not_recorded`.
- Dataset B high-fidelity `hybrid` on the full 12k cumulative Open-SWE overlay is retained as a
  strong linkage baseline for smaller snapshots, not as the scalable provider method. The full
  12k high-fidelity run was killed before writing `run_summary.json`; the scalable claim should
  use `provider_lowcost` with explicit feature budgets and cache-bucket streaming.
- Main 2x2, Dataset B, T3 entity-percolation, later-watchlist, and semantic-profile bootstrap CIs
  are complete. Full original Open-SWE longitudinal CIs remain an optional robustness extension,
  not a blocker for the scoped main-paper claims.
- SWE-agent/minimax reservoir 100/250/500 is complete as a local-from-raw500 robustness sweep;
  a full Hugging Face streaming reservoir sweep remains optional if network budget allows.
- Synthetic scale/difficulty/profile tables are complete for controlled mechanism evidence in
  `docs/tables/synthetic_matrix_summary.md`.
