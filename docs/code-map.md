# Code Map

Start here when modifying or auditing the implementation. The code is organized around the
same three stages as the paper narrative: provider-view data construction, provider-side
linkage/reconstruction, and evaluation/reporting.

## Main Packages

| Package | Responsibility | Typical Entry Points |
| --- | --- | --- |
| `src/agent_privacy/data/` | Dataset generation, Open-SWE/SWE-bench import, Dataset B user overlay injection, provider-view audit, sampling, turn-delta conversion, and longitudinal snapshots. | `open_swe_traces.py`, `open_swe_user_overlay.py`, `swe_workflows.py`, `time_snapshots.py`, `audit.py` |
| `src/agent_privacy/features/` | Provider-visible feature extraction from API-log shaped requests. | `extract.py` |
| `src/agent_privacy/attacks/` | Baseline, hybrid, and provider-lowcost linkage attacks. | `pipeline.py`, `cluster.py` |
| `src/agent_privacy/evaluation/` | Clustering, ordering, workflow reconstruction, profile, and control-baseline metrics. | `clustering.py`, `ordering.py`, `workflows.py`, `profile.py`, `controls.py` |
| `src/agent_privacy/profiling/` | Rule, structured-evidence, and dense-semantic profile reconstruction plus profile-derived watchlists. | `rule_profiler.py`, `structured_profiler.py`, `semantic_profiler.py`, `watchlist.py` |
| `src/agent_privacy/defenses/` | Redaction/minimization transforms and utility proxies. | `transforms.py`, `utility.py` |
| `src/agent_privacy/experiments/` | CLI entry points for experiments, table summaries, bootstrap CIs, sweeps, dataset cards, and profile examples. | `run_dataset.py`, `summarize_*.py`, `bootstrap_*.py` |
| `scripts/` | GitHub release boundary checks and deterministic external-asset packaging. These are repository maintenance scripts, not runtime library modules. | `release_check.py`, `build_release_bundles.py` |

## Important CLIs

| Task | Command Module |
| --- | --- |
| Run a dataset attack/evaluation pipeline | `agent-privacy-run` or `python -m agent_privacy.experiments.run_dataset` |
| Run the generated synthetic MVP | `agent-privacy-smoke` or `python -m agent_privacy.experiments.run_mvp` |
| Regenerate paper figures | `agent-privacy-figures` or `python -m agent_privacy.experiments.generate_paper_figures` |
| Generate Dataset B overlays | `python -m agent_privacy.data.open_swe_user_overlay` |
| Import Open-SWE traces | `python -m agent_privacy.data.open_swe_traces` |
| Import SWE-bench workflow datasets | `python -m agent_privacy.data.swe_workflows` |
| Build longitudinal snapshots | `python -m agent_privacy.data.time_snapshots` |
| Rebuild current summary tables | `python -m agent_privacy.experiments.summarize_*` |
| Bootstrap Open-SWE tables | `python -m agent_privacy.experiments.bootstrap_open_swe` |
| Bootstrap arbitrary prediction files | `python -m agent_privacy.experiments.bootstrap_ci` |
| Audit cross-workflow Open-SWE entity linkage | `python -m agent_privacy.experiments.summarize_open_swe_entity_validity` |
| Summarize held-out Open-SWE baselines and ordering | `python -m agent_privacy.experiments.summarize_open_swe_main_session` |
| Run synthetic scale/difficulty/profile matrix | `python -m agent_privacy.experiments.run_synthetic_matrix` |
| Validate GitHub candidates | `python scripts/release_check.py` |
| Build GitHub Release ZIPs | `python scripts/build_release_bundles.py` |

## Optional Dependencies

| Extra | Capability |
| --- | --- |
| base | CARP, evaluation, NumPy, and TF-IDF CARP-Content |
| `data` | Hugging Face `datasets` import path |
| `paper` | Matplotlib figure generation |
| `semantic` | Sentence-transformer and HNSW experiments |

The `dev` dependency group includes pytest, Ruff, and the small HNSW test dependency. It does not
install sentence-transformers or Torch.

## Provider-View Boundary

The provider-visible request contract is `attack_view.jsonl`. Evaluation-only labels and source
metadata belong in `ground_truth.jsonl`, `request_provenance.jsonl`, and manifests. See
`docs/data-schema.md` and `docs/dataset-index.md` before changing data fields.

## Main Implementation Notes

- `provider_lowcost` in `attacks/pipeline.py` is the scalable provider-side chain used for the
  main low-cost narrative.
- The non-code path parses structured tool JSON and explicit ID phrases into stable user,
  process/project, organization, and shared-resource handles. Only level-appropriate strong
  handles percolate across cache blocks; aliases bridging stronger components are rejected.
- `run_dataset.py` exposes feature budgets and `--stream-provider-lowcost` for large Dataset B
  runs.
- `hybrid` is a high-fidelity baseline. It is useful for small and ablation runs, but it is not
  the scalable provider method used for 12k Dataset B evidence.
- Summary scripts in `experiments/summarize_*.py` are the source of truth for `docs/tables/`.
