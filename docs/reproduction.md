# Reproduction Guide

This guide lists the commands needed to rebuild the currently curated paper artifacts.

## Environment And Artifact Availability

```bash
uv sync --group dev
```

The base environment runs CARP, TF-IDF CARP-Content, evaluation, and tests. Add `--extra data` for
Hugging Face imports, `--extra paper` for Matplotlib figures, and `--extra semantic` for MiniLM/HNSW.

The Git repository intentionally omits large upstream-derived datasets and raw result directories.
Consult `artifacts/dataset-manifest.json` and `results/result-manifest.json` before running a command.
Paths under `artifacts/datasets/` or `results/` must be regenerated or restored from an approved
GitHub Release asset. The bundled `examples/tool_agent_smoke/` fixture is sufficient for a clean-clone
software check but not for reproducing paper numbers.

## Checks

```bash
uv run ruff check .
uv run pytest -q
uv run python scripts/release_check.py
```

## Dataset Cards And Audit Summary

```bash
uv run python -m agent_privacy.experiments.write_dataset_cards --output-dir docs/tables
```

## Main Summary Tables

```bash
uv run python -m agent_privacy.experiments.summarize_open_swe --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_provider_lowcost --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_open_swe_entity_validity --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_open_swe_main_session --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_open_swe_direct_exposure --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_open_swe_candidate_diagnostics --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_open_swe_strict_removal --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_open_swe_semantic_project --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_open_swe_semantic_project \
  --dataset-dir artifacts/datasets/open_swe_traces_sweagent_minimax_raw_500 \
  --output-base open_swe_sweagent_strict_semantic_project_linkage \
  --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_longitudinal --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_gap_results --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_controls --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_runtime_cost --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_lowcost_cost_model --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_sweagent_reservoir --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_user_overlay --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_user_overlay_profiles --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_warm_start_watchlist --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_warm_start_retrieval --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_tau_bench_temporal_stress --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_stable_handle_audit --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_tau_bench_stable_user_linkage --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_tau_bench_natural_watchlist --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_tau_bench_hnsw --output-dir docs/tables
```

The exploratory mitigation-proxy table is outside the submission claim set. It can be regenerated
separately with `uv run python -m agent_privacy.experiments.summarize_defense_frontier --output-dir docs/tables`.

The entity-validity summary recomputes project/owner metrics after excluding every request pair
from the same workflow. It also evaluates a direct baseline that groups requests only by normalized
workspace repository/owner anchors:

```bash
uv run python -m agent_privacy.experiments.summarize_open_swe_entity_validity \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_12000_requests \
  --predictions results/open_swe_provider_lowcost_longitudinal_full_first_12000_turns/M0/feature_no_semantic/predictions.json \
  --iterations 200 \
  --output-dir docs/tables
```

Regenerate the bounded context-only diagnostic and the held-out workflow-bootstrap intervals:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --output results/open_swe_context_only_sample100_turns \
  --defenses M0 \
  --levels session project org \
  --methods context_only \
  --ablations none \
  --feature-ablations no_semantic \
  --skip-profile \
  --turn-ids 3 6 9 12 \
  --open-swe-fast-features \
  --skip-ordering

uv run python -m agent_privacy.experiments.bootstrap_ci \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --predictions results/open_swe_context_only_sample100_turns/M0/feature_no_semantic/predictions.json \
  --output docs/tables/open_swe_context_only_sample100_bootstrap_ci.csv \
  --methods context_only \
  --levels session \
  --unit-level session \
  --iterations 500 \
  --seed 7 \
  --turn-ids 3 6 9 12

uv run python -m agent_privacy.experiments.summarize_open_swe_main_session \
  --output-dir docs/tables
```

## Main 2x2 Bootstrap CI

```bash
uv run python -m agent_privacy.experiments.bootstrap_open_swe \
  --output-dir docs/tables \
  --iterations 200
```

## Provider-Lowcost Controls

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --output results/open_swe_controls_sample100_turns_3_6_9_12 \
  --defenses M0 \
  --levels session project org \
  --methods random oracle_size_random provider_lowcost \
  --ablations none \
  --feature-ablations none no_shingles \
  --skip-profile \
  --turn-ids 3 6 9 12 \
  --write-reconstructed-workflows \
  --open-swe-fast-features

uv run python -m agent_privacy.experiments.bootstrap_ci \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --predictions results/open_swe_controls_sample100_turns_3_6_9_12/M0/predictions.json \
  --output docs/tables/open_swe_controls_sample100_bootstrap_ci.csv \
  --methods provider_lowcost random oracle_size_random \
  --levels session project org \
  --turn-ids 3 6 9 12 \
  --iterations 200

uv run python -m agent_privacy.experiments.summarize_controls --output-dir docs/tables
```

## Threshold Sweep

```bash
uv run python -m agent_privacy.experiments.sweep_lowcost_thresholds \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --output docs/tables/open_swe_lowcost_threshold_sweep.csv \
  --turn-ids 3 6 9 12

uv run python -m agent_privacy.experiments.sweep_lowcost_thresholds \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000 \
  --output docs/tables/open_swe_heldout_threshold_sweep.csv \
  --turn-ids 3 6 9 12 \
  --containments 0.62 0.70 0.78 0.86 0.94 \
  --jaccards 0.16 0.20 0.24 \
  --candidate-caps 100 400 800 \
  --axis-only

uv run python -m agent_privacy.experiments.summarize_threshold_robustness
```

## Cross-Scaffold Transfer, Watchlist CI, And Controlled Scale

```bash
uv run python -m agent_privacy.experiments.summarize_open_swe_cross_scaffold_transfer
uv run python -m agent_privacy.experiments.summarize_tau_bench_natural_watchlist \
  --bootstrap-iterations 500 --seed 7
uv run python -m agent_privacy.experiments.summarize_carp_scale \
  --sizes 10000 50000 100000 \
  --conditions clean shared_alias_collision
```

The cross-scaffold run selects weights, margins, and thresholds only from source-scaffold
calibration projects. The target scaffold contributes no labels to parameter selection. The scale
run uses compact synthetic features with four requests per workflow and a fixed collision rate; it
measures computational growth rather than production prevalence.

## Profile Bounds And Risk Levels

```bash
uv run python -m agent_privacy.experiments.profile_bounds \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --output-dir docs/tables \
  --predictions results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_profile/M0/predictions.json \
  --method hybrid \
  --level org
```

Compare the flat rule profiler with structured evidence aggregation on the same predicted and
truth clusters:

```bash
uv run python -m agent_privacy.experiments.compare_profilers \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --predictions results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_profile/M0/predictions.json \
  --rule-metrics results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_profile/M0/profile_metrics.csv \
  --output-dir results/open_swe_profile_structured_comparison \
  --method hybrid \
  --level org
```

Run the calibrated dense-semantic profiler. The first run downloads
`sentence-transformers/all-MiniLM-L6-v2`; subsequent runs can use the local Hugging Face cache.

```bash
uv run python -m agent_privacy.experiments.run_semantic_profile \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --predictions results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_profile/M0/predictions.json \
  --output-dir results/open_swe_semantic_profile \
  --method hybrid \
  --level org \
  --model sentence-transformers/all-MiniLM-L6-v2 \
  --calibration-fraction 0.20 \
  --seed 7

uv run python -m agent_privacy.experiments.summarize_semantic_profile \
  --result-dir results/open_swe_semantic_profile \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --output-dir docs/tables
```

## Synthetic Dataset A

Generate the audited synthetic benchmark dataset without running the full defense matrix:

```bash
uv run python -c "from pathlib import Path; import json; from dataclasses import fields; from agent_privacy.data.schemas import DatasetConfig; from agent_privacy.data.generator import generate_dataset; raw=json.loads(Path('configs/mvp.json').read_text()); allowed={f.name for f in fields(DatasetConfig)}; config=DatasetConfig(**{k:v for k,v in raw.items() if k in allowed}); print(generate_dataset(config, Path('artifacts/datasets/synthetic_mvp')))"
```

Then rebuild cards:

```bash
uv run python -m agent_privacy.experiments.write_dataset_cards --output-dir docs/tables
```

Run the controlled scale/difficulty/profile matrix:

```bash
uv run python -m agent_privacy.experiments.run_synthetic_matrix \
  --output-dir results/synthetic_matrix
```

The generated summary is mirrored to `docs/tables/synthetic_matrix_summary.md`.

## Redacted Profile Examples

```bash
uv run python -m agent_privacy.experiments.profile_examples \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --predictions results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_profile/M0/predictions.json \
  --output docs/redacted-profile-examples.md \
  --limit 3
```

## Open-SWE User Overlay Dataset B

Generate U3 and U4 trace-grounded semi-synthetic user overlays:

```bash
uv run python -m agent_privacy.data.open_swe_user_overlay \
  --config configs/open_swe_user_overlay_u3.json

uv run python -m agent_privacy.data.open_swe_user_overlay \
  --config configs/open_swe_user_overlay_u4_hard_shared.json
```

Run first-1k high-fidelity linkage checks. These use `hybrid` as a diagnostic baseline, not as
the scalable provider method:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_user_overlay_u3_mixed_1000_snapshots/first_1000_requests \
  --output results/open_swe_user_overlay_u3_first_1000_m0_fast \
  --defenses M0 \
  --levels session user project org \
  --methods temporal rare tool hybrid \
  --ablations none \
  --skip-profile \
  --open-swe-fast-features

uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000_snapshots/first_1000_requests \
  --output results/open_swe_user_overlay_u4_first_1000_m0_fast \
  --defenses M0 \
  --levels session user project org \
  --methods temporal rare tool hybrid \
  --ablations none \
  --skip-profile \
  --open-swe-fast-features

uv run python -m agent_privacy.experiments.summarize_user_overlay --output-dir docs/tables
```

Run provider-scale linkage checks with cache-bucket streaming and explicit feature budgets.
The paper-facing longitudinal tables use U3/U4 snapshots at 1k/4k/8k/12k requests; the 12k U3
command is shown here as the largest single example:

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

uv run python -m agent_privacy.experiments.summarize_runtime_cost --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_lowcost_cost_model --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_user_overlay --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_user_overlay_profiles --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_warm_start_watchlist --output-dir docs/tables
```

Bootstrap the U3/U4 12k streamed provider-lowcost rows:

```bash
uv run python -m agent_privacy.experiments.bootstrap_ci \
  --dataset-dir artifacts/datasets/open_swe_user_overlay_u3_mixed_1000_snapshots/first_12000_requests \
  --predictions results/open_swe_user_overlay_u3_first_12000_provider_lowcost_streamed/M0/predictions.json \
  --output docs/tables/open_swe_user_overlay_u3_12k_bootstrap_ci.csv \
  --methods provider_lowcost \
  --levels session user project org \
  --unit-level session \
  --iterations 100

uv run python -m agent_privacy.experiments.bootstrap_ci \
  --dataset-dir artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000_snapshots/first_12000_requests \
  --predictions results/open_swe_user_overlay_u4_first_12000_provider_lowcost_streamed/M0/predictions.json \
  --output docs/tables/open_swe_user_overlay_u4_12k_bootstrap_ci.csv \
  --methods provider_lowcost \
  --levels session user project org \
  --unit-level session \
  --iterations 100
```

## Timed Provider-Lowcost Sample100

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --output results/open_swe_provider_lowcost_cumulative_sample100_cluster_timed \
  --defenses M0 \
  --levels session project org \
  --methods provider_lowcost \
  --ablations none \
  --feature-ablations none no_semantic no_shingles \
  --skip-profile \
  --turn-ids 3 6 9 12 \
  --write-reconstructed-workflows \
  --open-swe-fast-features
```

## tau-bench Historical Non-Code Agent Sample

The current tau-bench experiment uses the official historical trajectories from a local clone of
the upstream repository. The original tau-bench README marks the airline/retail task version as
outdated and points to tau^3-bench; report this run as a historical non-code supplement.

```bash
git clone --depth 1 https://github.com/sierra-research/tau-bench /tmp/tau-bench

uv run python -m agent_privacy.data.tau_bench \
  --input-path /tmp/tau-bench/historical_trajectories \
  --output-dir artifacts/datasets/tau_bench_historical_adapted \
  --limit 660 \
  --max-turns-per-workflow 12

uv run python -m agent_privacy.data.sample_dataset \
  --dataset-dir artifacts/datasets/tau_bench_historical_adapted \
  --output-dir artifacts/datasets/tau_bench_historical_sample200 \
  --limit-workflows 200 \
  --sample-mode reservoir \
  --seed 7

uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/tau_bench_historical_sample200 \
  --output results/tau_bench_historical_sample200_provider_lowcost \
  --defenses M0 \
  --levels session user project org \
  --methods provider_lowcost random oracle_size_random \
  --ablations none \
  --feature-ablations none no_tool_schema no_paths no_repo_ids \
  --skip-profile \
  --skip-ordering \
  --stream-provider-lowcost

uv run python -m agent_privacy.data.audit \
  --dataset-dir artifacts/datasets/tau_bench_historical_adapted \
  --output docs/tables/tau_bench_historical_provider_view_audit.md

uv run python -m agent_privacy.experiments.summarize_tau_bench --output-dir docs/tables

uv run python -m agent_privacy.experiments.summarize_tau_bench_historical_evidence \
  --dataset-dir artifacts/datasets/tau_bench_historical_sample200 \
  --output-dir docs/tables \
  --iterations 200 \
  --seed 7
```

The second summary deterministically reserves 40 workflows for calibration and evaluates all
reported historical tau-bench baselines on the remaining 160 workflows. It selects a stricter
semantic-signature operating point on calibration workflows only, reports airline/retail
breakdowns, and bootstraps held-out workflows.

Build and evaluate the tau-bench three-layer overlay:

```bash
uv run python -m agent_privacy.data.tau_bench_overlay \
  --config configs/tau_bench_overlay_t3.json

uv run python -m agent_privacy.data.audit \
  --dataset-dir artifacts/datasets/tau_bench_overlay_t3 \
  --output docs/tables/tau_bench_overlay_t3_provider_view_audit.md

uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/tau_bench_overlay_t3_snapshots/first_2500_requests \
  --output results/tau_bench_overlay_t3_first_2500_provider_lowcost \
  --defenses M0 \
  --levels session user project org \
  --methods provider_lowcost random oracle_size_random \
  --ablations none \
  --feature-ablations none no_tool_schema no_paths no_repo_ids \
  --skip-profile \
  --skip-ordering \
  --stream-provider-lowcost

uv run python -m agent_privacy.experiments.summarize_tau_bench \
  --output-dir docs/tables \
  --result-dir results/tau_bench_overlay_t3_first_2500_provider_lowcost \
  --dataset-dir artifacts/datasets/tau_bench_overlay_t3_snapshots/first_2500_requests \
  --output-base tau_bench_overlay_t3_first_2500_provider_lowcost \
  --dataset-name tau_bench_overlay_t3_first_2500 \
  --status trace_grounded_three_layer_overlay
```

Run the cross-cache strong-entity percolation variant and summarize the improvement:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/tau_bench_overlay_t3_snapshots/first_2500_requests \
  --output results/tau_bench_overlay_t3_first_2500_provider_lowcost_stable_handles \
  --defenses M0 \
  --levels session user project org \
  --methods provider_lowcost \
  --ablations none \
  --feature-ablations none \
  --skip-profile \
  --skip-ordering \
  --stream-provider-lowcost

uv run python -m agent_privacy.experiments.summarize_tau_bench_entity_percolation \
  --baseline-dir results/tau_bench_overlay_t3_first_2500_provider_lowcost \
  --improved-dir results/tau_bench_overlay_t3_first_2500_provider_lowcost_stable_handles \
  --output-dir docs/tables

uv run python -m agent_privacy.experiments.summarize_tau_bench_watchlist \
  --dataset-dir artifacts/datasets/tau_bench_overlay_t3 \
  --train-snapshot-dir artifacts/datasets/tau_bench_overlay_t3_snapshots/first_2500_requests \
  --predictions results/tau_bench_overlay_t3_first_2500_provider_lowcost_stable_handles/M0/predictions.json \
  --output-dir docs/tables

uv run python -m agent_privacy.experiments.summarize_tau_bench_anchor_robustness \
  --dataset-dir artifacts/datasets/tau_bench_overlay_t3 \
  --train-snapshot-dir artifacts/datasets/tau_bench_overlay_t3_snapshots/first_2500_requests \
  --predictions results/tau_bench_overlay_t3_first_2500_provider_lowcost_stable_handles/M0/predictions.json \
  --output-dir docs/tables \
  --seed 7
```

## Paper Extension Confidence Intervals And Figures

Regenerate the paired T3 entity-percolation intervals, later-traffic watchlist intervals, and
held-out semantic-versus-structured profile interval:

```bash
uv run python -m agent_privacy.experiments.bootstrap_paper_extensions \
  --t3-dataset-dir artifacts/datasets/tau_bench_overlay_t3_snapshots/first_2500_requests \
  --t3-baseline-predictions results/tau_bench_overlay_t3_first_2500_provider_lowcost/M0/predictions.json \
  --t3-improved-predictions results/tau_bench_overlay_t3_first_2500_provider_lowcost_stable_handles/M0/predictions.json \
  --t3-full-dataset-dir artifacts/datasets/tau_bench_overlay_t3 \
  --semantic-dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --semantic-result-dir results/open_swe_semantic_profile \
  --output docs/tables/paper_extension_bootstrap_ci.csv \
  --iterations 500 \
  --seed 7

uv run python -m agent_privacy.experiments.generate_paper_figures \
  --output-dir docs/paper/figures
```

Compile the anonymous upload project with the supplied AAAI style files stored in
`docs/overleaf/`. In Overleaf, set `api.tex` as the main document and select pdfLaTeX. A local
multi-pass smoke build can use Tectonic:

```bash
cd docs/overleaf
tectonic -X compile api.tex --outdir /tmp/paper-build --keep-logs
```

The validated migration build uses seven body pages and eight pages including references, with no
BibTeX errors, unresolved citations, or overfull boxes. The generated PDF remains a local build
product and is ignored. Because Tectonic uses XeTeX-compatible fallbacks for the supplied
pdfLaTeX-oriented style, run the final font-embedding check on the PDF exported by Overleaf.

## Optional Follow-Up Runs

These are robustness extensions, not blockers for the scoped seven-body-page submission:

- Full original Open-SWE longitudinal bootstrap CIs beyond the main matrix and extension CIs.
- SWE-agent/minimax full-source HF reservoir 100/250/500 if network/compute budget allows;
  the local-from-raw500 reservoir robustness sweep is already summarized.
- Full all-turn 12k original Open-SWE provider-lowcost run. Dataset B U3 12k provider-lowcost
  has a completed cache-bucket streamed budgeted run.
