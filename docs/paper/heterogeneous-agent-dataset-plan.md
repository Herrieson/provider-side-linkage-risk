# Heterogeneous Agent Dataset Plan

Open-SWE is software-engineering-heavy and contains strong repository/workspace fingerprints.
To address external-validity concerns, the paper should add at least one non-code Agent setting.
This document defines the recommended path without fabricating results.

## Candidate Datasets

| Candidate | Domain | Fit | Cost/Risk |
| --- | --- | --- | --- |
| tau-bench | Tool/API agents in customer-service-like domains. | Best first target: provider-visible tool calls, user requests, policies, and stateful business objects. | Requires importer and task-log conversion; no browser runtime needed. |
| WebArena / BrowserGym | Browser/web agents. | Strong heterogeneity: websites, accounts, UI actions, browser observations. | Heavier runtime and environment management. |
| OSWorld | Desktop/web/OS agents. | Broadest non-code environment, includes desktop apps and file I/O. | Highest setup and execution cost. |

## Recommended First Target: tau-bench

tau-bench is the most direct complement to Open-SWE because it has tool-use and business-process
state without GitHub repo/workspace paths. It can test whether CARP relies only on software
engineering fingerprints or also works with non-code Agent signals.

Expected provider-visible signals:

- tool/schema names;
- policy fragments;
- customer/order/account/product identifiers;
- repeated business entities across turns;
- task state updates;
- conversation history;
- temporal/context growth.

Expected evaluation labels:

- task/session ID;
- domain;
- user/customer/account-like synthetic ID if available;
- tool-state entity IDs where available.

## Provider-View Conversion Contract

The importer should write the standard dataset contract:

- `attack_view.jsonl`: provider-visible messages, tool schemas, timestamps, token counts, and
  cache-like bucket.
- `ground_truth.jsonl`: task/session/domain/entity labels for evaluation.
- `request_provenance.jsonl`: source split, original task ID, and conversion metadata.
- `source_manifest.json`: dataset source, split, counts, and known limitations.

Do not put ground-truth labels into `attack_view.jsonl`.

## Minimum Experiment Matrix

| Experiment | Purpose |
| --- | --- |
| CARP/provider_lowcost linkage on tau-bench | Test non-code Agent linkage. |
| no-tool-schema ablation | Measure dependence on tool/API schema. |
| no-entity-token ablation | Simulate redaction of customer/order/account IDs. |
| turn-delta vs cumulative | Measure cumulative-context leakage outside coding agents. |
| runtime/cost row | Compare candidate-pair reduction to Open-SWE. |

## Paper Use

If tau-bench results are strong:

> CARP generalizes beyond software-engineering traces: non-code tool agents also expose
> stable entity-state and schema signals.

If tau-bench results are weak:

> The attack surface is domain-dependent. Software-engineering agents are especially vulnerable
> because repo/workspace artifacts are strong quasi-identifiers; non-code agents require richer
> entity/state repetition for comparable linkage.

Either result is useful because it addresses the external-validity criticism.

## Current Implementation Status

- [x] Added importer: `src/agent_privacy/data/tau_bench.py`.
- [x] Added provider-view conversion test and smoke fixture.
- [x] Converted official historical airline/retail trajectories into
  `artifacts/datasets/tau_bench_historical_adapted`.
- [x] Built a 200-workflow reservoir sample:
  `artifacts/datasets/tau_bench_historical_sample200`.
- [x] Ran provider_lowcost with `none`, `no_tool_schema`, `no_paths`, and `no_repo_ids` feature
  ablations.
- [x] Wrote current result table:
  `docs/tables/tau_bench_historical_sample200_provider_lowcost.md`.
- [x] Built a trace-grounded three-layer tau-bench overlay:
  `artifacts/datasets/tau_bench_overlay_t3`.
- [x] Ran the first T3 2,500-request provider_lowcost table:
  `docs/tables/tau_bench_overlay_t3_first_2500_provider_lowcost.md`.
- [x] Wrote dataset card:
  `docs/dataset-card-tau-bench-adapted.md`.

Current result interpretation:

- A domain-stratified split reserves 40 workflows for calibration and evaluates 160 workflows
  (1,736 requests). The strongest baseline is 10-minute temporal grouping at F1 0.736. Default
  CARP transfers the shared thresholds without tau-specific retuning and reaches F1 0.495.
- A separately calibrated high-precision semantic operating point reaches precision 0.805, recall
  0.416, and F1 0.548. Removing time collapses CARP precision to 0.011, so the evidence supports
  measurable non-code session linkage under controlled timestamps, not content-only recovery.
- The direct historical sample supports benchmark-user linkage through provider-visible stable
  handles: the held-out structured-handle pipeline reaches precision/recall/F1
  1.000/0.400/0.571 and cross-workflow F1 0.561. These are benchmark records, not natural-person
  identities; project/tenant hierarchy remains controlled in T3.
- The T3 overlay supplies controlled three-layer non-code labels: 24 synthetic tenants,
  140 synthetic customers, and 72 synthetic business project/case lines on top of real
  tau-bench trajectories. Structured JSON/ID-handle extraction plus cross-cache percolation raises
  first-2,500 user/project/org F1 from 0.214/0.159/0.297 to 0.771/0.686/0.777 while preserving
  precision at 0.952/0.998/1.000.
- A first-2,500 entity watchlist evaluated on all later requests reaches user/project/org F1
  0.702/0.830/0.876. This converts the former high-precision, low-recall cold-start boundary into
  a higher-coverage longitudinal result without using region, loyalty tier, standalone service
  line, or random case IDs as strong union anchors.

## Implementation TODO

- [x] Add `src/agent_privacy/data/tau_bench.py`.
- [x] Add dataset card `docs/dataset-card-tau-bench-adapted.md`.
- [x] Add provider-view audit row.
- [x] Run small smoke conversion locally.
- [x] Run CARP/provider_lowcost linkage and ablations on a real historical sample.
- [x] Add result table to `docs/tables/`.
- [x] Add a tau-bench three-layer overlay dataset.
- [x] Run a first three-layer T3 linkage table.
- [x] Add a business-entity-aware tau-bench second stage for user/project/entity profiling.
- [x] Improve T3 recall with customer/order/reservation/product/case-aware linking and longitudinal
  watchlists.
- [ ] Repeat on tau^3-bench if the updated dataset/runtime is adopted.
