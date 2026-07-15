# Provider-Side Linkage Risk in LLM Agent API Traffic

This repository contains a research pipeline for studying content-side de-anonymization risks
in LLM Agent API logs. The paper-facing artifacts are organized around a provider-view threat
model: a passive model API provider observes plaintext Agent requests but not broker-side
customer identifiers. The paper is problem-driven: it measures persistent content handles and
context replay as two cross-domain mechanisms that survive protocol-level identifier stripping;
CARP is the bounded reference attack used to instantiate that measurement.

## Release Model

The Git repository is intentionally small. It contains source code, configs, tests, the anonymous
paper source, all paper-facing aggregate tables, dataset/result catalogs, and a fully synthetic
six-request smoke example. It does not contain the 16 GB local dataset tree or the 3.2 GB raw result
tree.

| Layer | Distribution |
| --- | --- |
| Code, configs, tests, paper tables, figures | Normal Git files |
| Synthetic smoke fixture | `examples/tool_agent_smoke/` in Git |
| Compact raw paper predictions and metrics | Optional GitHub Release ZIP |
| Synthetic Dataset A | Regenerable; optional GitHub Release ZIP |
| Adapted Open-SWE, tau-bench, SWE-bench content | Rebuild from upstream after license review |

See `docs/github-release.md`, `artifacts/dataset-manifest.json`, and
`results/result-manifest.json` for the exact release boundary.

## Install

The default environment contains CARP, evaluation, TF-IDF CARP-Content, and the test suite without
downloading Torch or a sentence-transformer model:

```bash
uv sync --group dev
```

Install only the optional capabilities needed for a run:

```bash
uv sync --group dev --extra data       # Hugging Face dataset import
uv sync --group dev --extra paper      # Matplotlib paper figures
uv sync --group dev --extra semantic   # MiniLM and HNSW experiments
uv sync --group dev --all-extras       # Complete research environment
```

## Smoke Example

Run the bundled synthetic tool-agent fixture without downloading a paper dataset:

```bash
uv run agent-privacy-run \
  --dataset-dir examples/tool_agent_smoke/dataset \
  --output /tmp/agent-privacy-smoke \
  --defenses M0 \
  --levels session user project org \
  --methods provider_lowcost \
  --ablations none \
  --feature-ablations none \
  --skip-profile \
  --skip-ordering \
  --stream-provider-lowcost
```

The fixture and deterministic expected outputs are documented in
`examples/tool_agent_smoke/README.md`. They validate the software path only and are not paper
evidence.

## Where To Start

Read these first instead of scanning raw `artifacts/` or `results/` directories:

| Need | Start Here |
| --- | --- |
| GitHub upload and release assets | `docs/github-release.md` |
| Dataset distribution status and local sizes | `artifacts/dataset-manifest.json` |
| Result bundle contents and table lineage | `results/result-manifest.json` |
| Paper tables, dataset cards, and regeneration commands | `docs/artifact-index.md` |
| Dataset roles, paths, provider-view contract, and claim boundaries | `docs/dataset-index.md` |
| Raw result directory map and archive policy | `docs/result-index.md` |
| Code package responsibilities and CLI map | `docs/code-map.md` |
| Reproduction commands | `docs/reproduction.md` |
| Current paper readiness and remaining limitations | `docs/tables/paper_experiment_readiness.md` |

The curated quantitative outputs live in `docs/tables/`. Treat those tables as the primary
paper interface; inspect raw result directories only when auditing or regenerating a table.

## Current Evidence

- Open-SWE-Traces is the main real-repo provider-view dataset. It supports workflow/session
  reconstruction, project/repo linkage, GitHub owner-like linkage, turn ordering, and partial
  technical profile reconstruction.
- Open-SWE does not contain reliable real `user_id` ground truth. Real Open-SWE user-level
  reconstruction must be reported as N/A.
- Dataset B is an Open-SWE-grounded semi-synthetic user overlay. It injects controlled
  user-level/profile truth into real Open-SWE trace substrate, then mixes requests over
  longitudinal snapshots. Use it for user-level mechanism evidence, not as proof of real
  Open-SWE user identities.
- Synthetic Dataset A is a controlled full-truth benchmark for scale, difficulty, and profile
  reconstruction sweeps. Use it as mechanism evidence only.
- SWE-bench Lite adapted datasets are repaired workflow boundary/validation evidence, not raw
  provider-log evidence.

## Main Results

| Topic | Table |
| --- | --- |
| Open-SWE scaffold/split attack matrix | `docs/tables/open_swe_2x2_attack_matrix.md` |
| Main 2x2 bootstrap confidence intervals | `docs/tables/open_swe_2x2_bootstrap_ci.md` |
| Provider-lowcost two-stage chain | `docs/tables/open_swe_provider_lowcost.md` |
| Main session baselines, bootstrap CIs, and ordering | `docs/tables/open_swe_main_session_evidence.md` |
| Direct exposure, strict removal, and semantic project linkage | `docs/tables/open_swe_direct_exposure_audit.md`; `docs/tables/open_swe_strict_signal_removal.md`; `docs/tables/open_swe_strict_semantic_project_linkage.md`; `docs/tables/open_swe_sweagent_strict_semantic_project_linkage.md` |
| Zero-target-label cross-scaffold transfer | `docs/tables/open_swe_cross_scaffold_zero_tuning.md` |
| Cross-workflow entity validity and repository/owner-anchor control | `docs/tables/open_swe_cross_workflow_entity_validity.md` |
| Provider-lowcost longitudinal snapshots | `docs/tables/open_swe_provider_lowcost_longitudinal_full_turns.md` |
| Feature ablations and turn ordering | `docs/tables/open_swe_gap_feature_ablation.md`; `docs/tables/open_swe_gap_ordering.md` |
| Profile reconstruction and risk levels | `docs/tables/open_swe_gap_profile.md`; `docs/tables/open_swe_profile_risk_levels.md` |
| Structured profile reconstruction comparison | `docs/tables/open_swe_structured_profile_comparison.md` |
| Calibrated MiniLM semantic profile comparison | `docs/tables/open_swe_semantic_profile_comparison.md`; `docs/tables/open_swe_semantic_profile_novel_evidence.md` |
| Runtime, 100K scale, and held-out threshold robustness | `docs/tables/open_swe_runtime_cost.md`; `docs/tables/carp_synthetic_scale.md`; `docs/tables/open_swe_heldout_threshold_robustness.md` |
| Dataset B user overlay linkage and CIs | `docs/tables/open_swe_user_overlay_linkage_summary.md`; `docs/tables/open_swe_user_overlay_12k_bootstrap_ci.md` |
| Dataset B longitudinal/profile results | `docs/tables/open_swe_user_overlay_longitudinal.md`; `docs/tables/open_swe_user_overlay_profile_reconstruction.md` |
| tau-bench T3 entity percolation and watchlist | `docs/tables/tau_bench_t3_entity_percolation.md`; `docs/tables/tau_bench_t3_entity_watchlist.md` |
| T3 anchor statistics and stability/collision stress | `docs/tables/tau_bench_t3_anchor_statistics.md`; `docs/tables/tau_bench_t3_anchor_robustness.md` |
| Held-out historical tau-bench baselines and high-precision operating point | `docs/tables/tau_bench_historical_evidence.md`; `docs/tables/tau_bench_historical_operating_points.md` |
| Cross-domain persistent-handle audit and natural tau user linkage | `docs/tables/cross_domain_stable_handle_audit.md`; `docs/tables/tau_bench_stable_user_linkage.md` |
| tau-bench temporal/rephrasing stress and CARP-Content ablation | `docs/tables/tau_bench_temporal_stress.md`; `docs/tables/tau_bench_content_linkage_ablation.md` |
| tau-bench natural user watchlist and HNSW ANN comparison | `docs/tables/tau_bench_natural_user_watchlist.md`; `docs/tables/tau_bench_hnsw_ann_baseline.md` |
| Extension bootstrap confidence intervals | `docs/tables/paper_extension_bootstrap_ci.md` |
| Synthetic controlled matrix | `docs/tables/synthetic_matrix_summary.md` |

The upload-ready manuscript is under `docs/overleaf/`; frozen claim scope and evidence audits remain
under `docs/paper/`. The migrated template build uses seven body pages and eight pages including
references. The paper includes only mitigation implications derived from attack-surface controls;
it does not claim a defense method, utility experiment, or defense contribution.

## Repository Layout

| Path | Contents |
| --- | --- |
| `src/agent_privacy/` | Dataset import/generation, feature extraction, attacks, evaluation, defenses, profiling, and experiment CLIs. |
| `configs/` | MVP and Dataset B generation configs. |
| `examples/tool_agent_smoke/` | Git-tracked, fully synthetic end-to-end fixture and expected outputs. |
| `artifacts/` | Git-tracked dataset catalog plus ignored local datasets and snapshots. |
| `results/` | Git-tracked result catalog plus ignored local raw experiment outputs. |
| `docs/` | Narrative docs, dataset cards, indexes, reproduction guide, and result tables. |
| `docs/overleaf/` | Self-contained anonymous AAAI manuscript, bibliography, styles, and referenced figures. |
| `scripts/` | Release-boundary validation and deterministic GitHub Release bundle builder. |
| `tests/` | Unit tests for core data/evaluation behavior. |

## Quick Checks

```bash
uv sync --group dev
uv run ruff check .
uv run pytest -q
uv run python scripts/release_check.py
uv run python -m json.tool docs/artifact-manifest.json
```

## Rebuild Current Tables

Most current tables can be regenerated from existing datasets/results:

```bash
uv run python -m agent_privacy.experiments.summarize_open_swe --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_provider_lowcost --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_longitudinal --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_gap_results --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_controls --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_runtime_cost --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_user_overlay --output-dir docs/tables
uv run python -m agent_privacy.experiments.summarize_user_overlay_profiles --output-dir docs/tables
```

See `docs/reproduction.md` for full experiment commands, Dataset B generation, bootstrap CIs,
synthetic matrix runs, and profile examples. Those commands require the ignored local datasets or
an approved external release asset.

## License

Original project code and documentation are released under the [MIT License](LICENSE). Upstream
datasets, repository-derived content, Python dependencies, and AAAI author-kit files retain their
own terms; see [THIRD_PARTY.md](THIRD_PARTY.md). In particular, the MIT License does not grant
permission to redistribute excluded Open-SWE, tau-bench, or SWE-bench payloads.

## Claim Boundaries

- Open-SWE `org_id` means GitHub owner / owner-like label, not an enterprise organization.
- Open-SWE cache and semantic signals are provider-view approximations; Open-SWE does not expose
  true provider cache telemetry.
- `provider_lowcost` is the scalable provider-side method. `hybrid` is a high-fidelity baseline
  and should not be used for large-scale cost claims.
- Archived results and datasets are retained only for traceability unless they are regenerated
  and reintroduced through `docs/artifact-index.md`.
