# tau-bench Historical Adapted Dataset Card

## Purpose

This dataset adapts tau-bench historical airline/retail tool-agent trajectories into the common
provider-view API log schema used in this project. It is included to test whether linkage effects
are limited to software-engineering agents with repo/workspace fingerprints.

## Source

- Source repository: official tau-bench historical trajectories.
- Local source used for the current run: `$TAU_BENCH_DIR/historical_trajectories`.
- Source files include airline and retail historical trajectories.
- Important version note: the tau-bench repository README says the original airline/retail tasks
  are outdated and points users to tau^3-bench for the latest benchmark. The current artifact is
  therefore a real historical trajectory supplement, not a latest-leaderboard reproduction.

## Conversion

Converter:

```bash
uv run python -m agent_privacy.data.tau_bench \
  --input-path "$TAU_BENCH_DIR/historical_trajectories" \
  --output-dir artifacts/datasets/tau_bench_historical_adapted \
  --limit 660 \
  --max-turns-per-workflow 12
```

Sampling for the current paper table:

```bash
uv run python -m agent_privacy.data.sample_dataset \
  --dataset-dir artifacts/datasets/tau_bench_historical_adapted \
  --output-dir artifacts/datasets/tau_bench_historical_sample200 \
  --limit-workflows 200 \
  --sample-mode reservoir \
  --seed 7
```

## Provider-View Contract

The converter writes:

- `attack_view.jsonl`: cumulative provider-visible messages before assistant turns, tool schemas,
  timestamps, token counts, cache-like buckets, and provider metadata.
- `ground_truth.jsonl`: domain, user, business-entity proxy, workflow, turn ID, and profile truth.
- `request_provenance.jsonl`: source task, source domain, event index, and conversion metadata.
- `source_manifest.json`: conversion config and counts.

Ground-truth labels and provenance are not stored in `attack_view.jsonl`.

## Current Shape

Full converted historical set:

- 660 workflows.
- 7,099 provider-view requests.
- 2 domains: airline and retail.
- 87 user IDs after excluding missing/unknown labels.

Paper sample:

- 200 reservoir-sampled workflows.
- 2,175 provider-view requests.

## Current Result

The current provider_lowcost table is:

- `docs/tables/tau_bench_historical_sample200_provider_lowcost.md`
- `docs/tables/tau_bench_overlay_t3_first_2500_provider_lowcost.md`

Main interpretation:

- Non-code tool-agent session reconstruction is possible without software repo/workspace
  artifacts: provider_lowcost session F1 is 0.458 on the 2,175-request sample, compared with
  random session F1 0.008.
- `no_paths`, `no_repo_ids`, and `no_tool_schema` leave the session result unchanged in this
  sample, suggesting the signal comes from cumulative dialogue/tool context and repeated business
  state rather than software paths or tool schemas.
- The direct historical sample is used for non-code session reconstruction. Its user/project/org
  labels are too coarse for real organization profiling claims; three-layer mechanism evaluation
  is handled by the T3 overlay below.

## Limitations

- The source trajectories are historical and the original tau-bench airline/retail tasks are not
  the latest tau^3-bench version.
- The current `project_id` is a business-entity proxy, not a software project.
- `org_id` is the domain label (`airline` or `retail`), not a company organization.
- Current user/project/org results should not be used to claim non-code organization profiling.

## Three-Layer Overlay

In addition to the direct historical conversion, the project now includes a trace-grounded
three-layer overlay:

- Config: `configs/tau_bench_overlay_t3.json`.
- Generator: `src/agent_privacy/data/tau_bench_overlay.py`.
- Dataset: `artifacts/datasets/tau_bench_overlay_t3`.
- Snapshots: `artifacts/datasets/tau_bench_overlay_t3_snapshots`.

This overlay follows the same logic as the Open-SWE user overlay: real tau-bench historical
dialogue/tool trajectories are preserved as the substrate, while org/user/project labels are
synthetic business-layer truth. Provider-visible account/case context is injected as normal
tool-observation content, and source tau-bench labels remain provenance-only.

Current T3 shape:

- 24 synthetic tenant/org labels.
- 140 synthetic customer/user labels.
- 72 synthetic business project/case-line labels.
- 660 workflows and 7,099 provider-view requests.
- Snapshots at 1,000, 2,500, 5,000, and 7,099 requests.

Current T3 first-2,500 result:

- provider_lowcost session precision/recall/F1: 0.736 / 0.328 / 0.454.
- provider_lowcost user precision/recall/F1: 0.954 / 0.121 / 0.214.
- provider_lowcost project precision/recall/F1: 1.000 / 0.087 / 0.159.
- provider_lowcost org precision/recall/F1: 1.000 / 0.174 / 0.297.
- Candidate-pair reduction versus all pairs: 35.632x.
- Peak RSS in the streamed run: about 105 MB.

Interpretation:

- The three-layer dataset now exists and is auditable.
- Business-entity-aware CARP refinement now recovers high-precision, low-recall user/project/org
  clusters using provider-visible `customer_ref`, `account_cache`, `queue`, `internal_domain`, and
  `tenant` anchors.
- Broad or unstable fields such as `loyalty_tier`, `region`, standalone `service_line`, and
  random `case_id` are not used as strong union anchors because they are shared across many
  entities or are not stable across requests.
- T3 remains trace-grounded semi-synthetic mechanism evidence. It should not be reported as real
  tau-bench user identity recovery or real enterprise organization recovery.
