# CARP Stage Contract and Parameters

CARP is a provider-view threat-evaluation pipeline composed from established blocking,
similarity, union-find, and connected-component primitives. It is not presented as a new graph
learning algorithm.

## Algorithm Contract

```text
Input:
  identifier-stripped provider-visible requests R
  per-request candidate budget B
  typed persistent-handle schema V

1. Extract bounded structural, context, time, and tool features; parse JSON/explicit-ID handles.
2. Partition requests by provider-visible cache-like block; missing metadata uses one fallback block.
3. Generate local candidates from bounded rare, semantic-signature, shingle, and identifier indexes.
4. Apply deterministic session and dataset-specific typed-entity edge rules.
5. Build separate session, user/customer-like, project/process, and tenant/owner-like components.
6. Keep shared resources candidate-only; reject aliases that bridge stronger typed components.
7. Propagate unambiguous typed-entity components across cache blocks without request all-pairs.
8. Build an early-traffic anchor-to-component watchlist and assign later requests by unique vote.
9. Optionally run CARP-Content over discovered sessions using MiniLM and structured sparse evidence.

Output:
  dataset-specific pseudonymous partitions, candidate diagnostics, and later-traffic assignments
```

## Shared Parameters

| Stage | Parameter | Value | Role |
| --- | --- | ---: | --- |
| Rare session index | maximum bucket | 20 | excludes common trace-like values |
| User/customer index | maximum bucket | 80 | bounds customer-like exact anchors |
| Project/owner index | maximum bucket | 400 | bounds repository/business anchors |
| Semantic-signature candidates | maximum bucket | 20 | bounded local word-signature blocking |
| Shingle candidates | maximum bucket | 35 | bounded cumulative-context blocking |
| Refinement candidates | maximum bucket | 20 | bounded identifier/domain refinement |
| All local passes | per-request pair budget | 400 | caps pair materialization per blocking family |
| Structured stable handles | maximum total/shared-resource values | 512 / 256 | bounds tool-JSON fan-out and prioritizes strong handles |
| Semantic edge | signature overlap | at least 2 | default CARP semantic rule |
| Semantic edge | shingle Jaccard | at least 0.32 | default CARP semantic rule |
| Semantic edge | identifier overlap | at least 3 | default CARP semantic rule |
| Semantic edge | time gap | at most 90 min | default CARP semantic rule |
| Context edge | smaller-context containment | at least 0.78 | cumulative-context rule |
| Context edge | shingle Jaccard | at least 0.20 | cumulative-context rule |
| Context edge | identifiers/repository | at least 2 / exact repo | cumulative-context rule |
| Context edge | time gap | at most 180 min | cumulative-context rule |
| Refinement edge A | Jaccard / identifiers / time | 0.22 / 2 / 180 min | session refinement |
| Refinement edge B | Jaccard / semantic / identifiers / time | 0.24 / 2 / 3 / 90 min | session refinement |

## Protocol-Specific Settings

| Protocol | Calibration or fixed setting | Evaluation boundary |
| --- | --- | --- |
| Open-SWE main | local thresholds checked on fixed 100-workflow development slice; semantic pass disabled | remaining 900 workflows, turns 3/6/9/12 |
| Open-SWE candidate diagnostic | 24K characters, 1,200 shingles, 1,500 words | held-out 900 workflows; diagnostic, not exact main-run telemetry |
| Historical tau-bench | maximum calibration F1 subject to precision at least 0.8 over fixed semantic grid | 40 calibration workflows, 160 held-out workflows |
| Historical tau-bench default CARP | shared CARP thresholds transferred without tau-bench retuning | 160 held-out workflows |
| Selected historical tau rule | 4 semantic matches, Jaccard 0.32, 3 identifiers, 30-minute gap | frozen before held-out scoring |
| T3 overlay | typed overlay schema plus deterministic JSON/explicit-ID parser; ambiguity by provider-visible co-occurrence | first 2,500 requests for cold start; later traffic scored separately |
| U3/U4 scale | 24K characters, 1,200 shingles, 1,500 words | 12,000-request streamed overlays |
| tau-bench CARP-Content | identifier-masked initial intent; MiniLM top-24 retrieval; cosine 0.98; typed-anchor bucket at most 20 | 40 calibration workflows, 160 held-out workflows; no timestamps |
| tau-bench temporal stress | arrivals compressed to 60/15/0 seconds; jitter 2/5/10 minutes; peak concurrency 10/41/146 | held-out workflows only; within-workflow order preserved |
| tau-bench intent rephrasing | deterministic synonym substitution, clause rotation, and light token deletion | fixed 0.98 threshold from unmodified calibration split |
| Open-SWE CARP-Content | 40K TF--IDF vocabulary; MiniLM weight 0.50; sparse floor 0.20; threshold 0.44; top 24 | project-disjoint 160-project calibration, 479 unseen-project evaluation; no paths/domains/timestamps |
| SWE-agent CARP-Content | same structural/dense grid, calibrated on project-disjoint source projects | 280 unseen-project evaluation; no paths/domains/timestamps |
| Zero-label scaffold transfer | source-selected MiniLM/TF--IDF weight and sparse floor; mutual-nearest edges; source-selected best-vs-second margin | target scaffold labels never enter parameter selection; evaluated in both directions |
| Natural tau stable-user linkage | deterministic structured handles, no threshold calibration | 160 held-out workflows; workflow-bootstrap CI and cross-workflow metric |
| Natural tau watchlist | early 100 workflows; exact user token/email/name--zip alias graph; self-supervised semantic calibration | later 100 workflows; base-task-disjoint semantic control reported separately |
| HNSW ANN | cosine space; M=16; efConstruction=200; efSearch=16/64/200; top 24 | 1,736 held-out tau requests; threshold 0.98 |
| Held-out context sensitivity | containment 0.62--0.94; Jaccard 0.16--0.24; pair budget 100--800 | 900 held-out Open-SWE workflows; single-axis changes around the default |
| Controlled scale | 4 requests/workflow; 200 requests/cache bucket; clean and fixed shared-alias-collision conditions | 10K/50K/100K compact pre-extracted features; computational diagnostic only |

## Scalable Retrieval Control

The Open-SWE candidate diagnostic also reports a banded bottom-k shingle sketch. Each request keeps
the 32 lexicographically smallest SHA-1 shingle hashes, splits them into eight bands of four, and
generates candidates from exact band matches. Buckets are capped at 80 requests and use the same
400-pairs-per-request materialization budget. This is a reproducible scalable control, not a claim
to cover all MinHash, ANN, learned-matcher, or entity-resolution implementations.

## Complexity

With per-request candidate budget `B`, local pair processing is bounded by `O(nB)` per blocking
family. Cross-cache propagation operates over extracted typed anchors and connected components,
not request all-pairs. Exact constants and memory use depend on bucket occupancy and retained
feature caps.
