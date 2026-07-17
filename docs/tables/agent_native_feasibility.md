# Agent-Native Linkage Feasibility Results

These are feasibility and transfer results for the experimental `agent_native_v0` reference
attack. The same configuration is used for the bundled smoke data, Open-SWE, and tau-bench. They
do not establish prevalence in enterprise traffic and do not yet satisfy the TODO's main-paper
promotion rule because systematic evidence-family ablations remain pending.

## Linkage and selective-risk results

| Dataset | Requests | Method | Session precision | Session recall | Session F1 | Accepted-edge precision | True-edge coverage | Abstention | Contaminated requests |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| Tool-agent smoke | 6 | CARP hybrid | 1.000 | 1.000 | 1.000 | — | — | — | — |
| Tool-agent smoke | 6 | Agent-native v0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.500 | 0 |
| Open-SWE turn-delta sample | 400 | CARP hybrid | 0.474 | 0.060 | 0.107 | — | — | — | not measured |
| Open-SWE turn-delta sample | 400 | Agent-native v0 | 1.000 | 0.245 | 0.394 | 1.000 | 0.390 | 0.703 | 0 |
| tau-bench historical sample | 2,175 | CARP hybrid | 0.975 | 0.055 | 0.104 | — | — | — | not measured |
| tau-bench historical sample | 2,175 | Agent-native v0 | 1.000 | 0.090 | 0.164 | 1.000 | 0.374 | 0.646 | 0 |

## Generic non-Agent text baseline

| Dataset | Method | Precision | Recall | F1 | Contaminated requests | Comparisons/request |
|---|---|---:|---:|---:|---:|---:|
| Open-SWE turn-delta sample | Hashed text nearest neighbor | 1.000 | 0.113 | 0.204 | 0 | 19.97 |
| Open-SWE turn-delta sample | Agent-native v0 | 1.000 | 0.245 | 0.394 | 0 | 5.09 |
| tau-bench historical sample | Hashed text nearest neighbor | 0.938 | 0.010 | 0.019 | 11 | 61.68 |
| tau-bench historical sample | Agent-native v0 | 1.000 | 0.090 | 0.164 | 0 | 23.97 |

The text baseline uses a fixed 32,768-dimensional hashing vectorizer and nearest-neighbor cosine
similarity within the same 90-minute active window. It is a reproducible generic-linkage control,
not a substitute for every learned entity-resolution architecture.

The selective metrics are edge-level: roots with no plausible predecessor are valid abstentions.
Cluster F1 remains the directly comparable metric. The zero-contamination result follows a
risk-gate refinement prompted by inspecting false-merge amplification, not dataset-specific
threshold tuning.

Evidence-family ablations are in `docs/tables/agent_native_ablations.md`. Open-SWE's incremental
windows require tool/resource continuity (replay-only F1 0), whereas tau's cumulative requests
benefit from replay and typed handles. Removing conflicts does not change these two strict
operating-point results; conflict value is therefore claimed only for the adversarial fixtures,
not as a measured improvement on these corpora.

## Controlled computation scale

The scale input deterministically rekeys and retimestamps public smoke traces. It validates
computation only; it is not evidence about real traffic prevalence or month-long workload mix.

| Requests | Seconds | Requests/s | Candidates/request | Peak active states | Peak active postings | Peak RSS KiB | Gate |
|---:|---:|---:|---:|---:|---:|---:|---|
| 10,000 | 3.68 | 2,714 | 1.695 | 1,801 | 17,716 | 42,176 | pass |
| 100,000 | 38.99 | 2,565 | 0.620 | 1,801 | 17,716 | 120,784 | pass |
| 500,000 | 188.82 | 2,648 | 0.524 | 1,801 | 17,716 | 445,444 | pass |

The active candidate work set is bounded by the 90-minute window and posting caps. Total memory
is not constant: union-find and output labels retain one entry per request, producing the expected
linear output-state cost.

## Fidelity audit

The trace-preserving smoke transformation changes 20 declared spans (17.9% of source characters)
without adding or deleting Agent events. Role sequence, tool sequence, message counts, tool names,
and tool schemas are preserved. Its structural two-sample AUC is 0.861 on six requests, so the
output is labeled `F0 controlled intervention`, not represented as real provider traffic. The
identity-control audit has JS/KS divergence 0 and AUC 0.5.

## Reproduction

```bash
.venv/bin/python -m agent_privacy.experiments.run_agent_native \
  --dataset-dir examples/tool_agent_smoke/dataset

.venv/bin/python -m agent_privacy.experiments.run_agent_native \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12_sample100

.venv/bin/python -m agent_privacy.experiments.run_agent_native \
  --dataset-dir artifacts/datasets/tau_bench_historical_sample200

.venv/bin/python -m agent_privacy.experiments.run_agent_native --scale-requests 100000

.venv/bin/python -m agent_privacy.experiments.audit_trace_fidelity \
  --dataset-dir examples/tool_agent_smoke/dataset \
  --output-dir results/agent_native/fidelity_smoke

.venv/bin/python -m agent_privacy.experiments.generic_text_baseline \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12_sample100 \
  --dataset-dir artifacts/datasets/tau_bench_historical_sample200 \
  --output-base docs/tables/generic_text_linkage_baseline
```
