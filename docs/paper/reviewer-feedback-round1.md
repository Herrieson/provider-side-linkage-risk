# Reviewer Feedback Round 1: Planned and Implemented Revisions

This note tracks the first five pre-submission review comments and the concrete revision made for
each one. It is an internal response draft rather than submission text.

## 1. Readability and excessive configuration detail

### Reviewer concern

The main text introduced CARP through many acronyms, thresholds, time gaps, bucket sizes, and
experiment-specific configurations. The method section read like a configuration file, while the
dataset/setup section mixed data sources, baselines, calibration, and transformations.

### Revision

- Rewrote the main CARP description around two signal families---persistent handles and continuity---and
  five conceptual stages: local blocking, rare-handle indexing, context growth, local refinement,
  and typed cross-block propagation.
- Removed numerical thresholds and feature caps from the main method narrative.
- Split the setup into `Data Sources and Claim Boundaries`, `Comparisons and Controls`, and
  `Evaluation Protocol`.
- Expanded `T3` on first use and described `CARP-Content` as an optional content-similarity second
  stage rather than assuming the acronym is self-explanatory.
- Added `docs/overleaf/supplement.tex`, containing the complete parameter table, protocol-specific
  calibration, transformations, and robustness interpretation.
- Removed repeated defensive qualifiers from the introduction, threat model, datasets, method, and
  results. Dataset scope, production prevalence, stronger supervised attackers, omitted network
  metadata, utility proxies, and legal/retention conditions are now consolidated in one compact
  `Limitations and Ethics` section. The main narrative retains only assumptions needed to interpret
  an experiment, such as truth isolation and later-only watchlist evaluation.

### Response draft

We agree that the previous presentation obscured the central idea. We rewrote the main method around
the two observable mechanisms and five algorithmic stages, moved exact thresholds and caps to a new
supplement, and reorganized the experimental setup by data source, comparison, and protocol. The
main text now explains why each stage exists before describing any implementation choice.

## 2. Practical applicability of the threat model

### Reviewer concern

The paper documented plaintext-retention configurations but did not justify why a regulated provider
would perform linkage. Excluding IP/TLS/account metadata also appeared artificial.

### Revision

- Clarified that `honest-but-curious` is a capability model, not an allegation about named providers.
- Added concrete access/motivation scenarios: authorized analytics, abuse investigation, insiders or
  contractors, post-breach analysis, acquisition/due diligence, legal compulsion, competitive
  intelligence, and state pressure.
- Stated the three necessary deployment conditions: plaintext reaches inference, some actor has
  cross-request access, and retention is long enough for aggregation.
- Explained that excluding network/account metadata is a lower-capability isolation test: if those
  identifiers survive, the privacy failure is easier and no content attack is needed.
- Strengthened legal, contractual, auditing, access-control, and zero-retention limitations.

### Response draft

We agree that configuration documentation alone does not establish motive or prevalence. The revised
threat section now separates technical capability from provider intent, gives several realistic
authorized and unauthorized access scenarios, and states that the paper measures conditional
severity rather than prevalence, legality, or actual provider behavior. We also explain that the
network-metadata exclusion deliberately isolates the residual content channel and makes the attacker
weaker, not stronger.

## 3. Dataset representativeness and external validity

### Reviewer concern

Open-SWE exposes complete repository/owner paths; tau-bench and the overlays are benchmark or
semi-synthetic data; no production enterprise logs are used. The 100K experiment demonstrates
computation rather than prevalence.

### Revision

- Renamed Open-SWE the main `real-trace substrate` rather than implying production provider logs.
- Elevated the OpenHands repository/owner result to a sanitization-boundary audit and explicitly
  denied that it demonstrates hidden inference or universal enterprise behavior.
- Added a main-text handle-coverage audit across domains: Open-SWE repository/owner coverage 100%;
  historical tau identity/process coverage 62.6%/17.8%; shared-resource ambiguity 49.8%.
- Added a supplementary evidence-boundary table distinguishing natural trace substrate, repaired or
  injected fields, and the exact claim supported by each dataset.
- Stated repeatedly that the coverage rates are qualitative occurrence evidence, not a population
  prevalence estimate, and specified what a governed production-log validation study would require.

### Response draft

We agree that the original text did not make the generalization boundary prominent enough. The
revision treats Open-SWE path results as direct-exposure auditing, uses historical tau only to show
that stable handles also occur in non-code traces, and labels every overlay and repaired field. We
now report cross-domain handle coverage and ambiguity as qualitative evidence while explicitly
reserving prevalence claims for future consented production-log studies.

## 4. Scientific positioning of CARP and entity-resolution comparisons

### Reviewer concern

It was unclear whether CARP was a central algorithmic contribution or a measurement tool. Hand-built
rules and weak cross-scaffold recall raised generalization concerns, while deep entity-resolution
methods were cited but not experimentally contextualized.

### Revision

- Defined CARP as an interpretable, bounded reference attack and explicitly denied novelty claims for
  union-find, connected components, ANN, or entity-resolution primitives.
- Positioned the measurement protocol---sealed truth, paired transformations, multi-level scoring,
  later-only watchlists, and bounded candidates---as the primary methodological contribution.
- Added explicit learned-representation comparisons: exact MiniLM top-k, HNSW ANN, dense-only strict
  project linkage, and dense-only cross-scaffold transfer.
- Added the relevant negative results: dense-only strict Open-SWE F1 0.070 and zero-label
  cross-scaffold F1 0.037/0.084.
- Explained that Ditto-style supervised pair matchers require labeled pairs and a fixed schema,
  changing the cold-start/no-target attacker assumption. They are described as stronger-attacker
  upper-bound extensions, not dismissed as irrelevant.

### Response draft

We agree that the prior wording left CARP's role ambiguous. The revised paper consistently calls it a
reference attack whose purpose is to instantiate the measurement contract under a pair budget. We
also foreground learned MiniLM/HNSW comparisons and their negative cross-domain results. Supervised
entity matching remains an important extension, but it requires labeled pairs unavailable to the
paper's cold-start attacker; we now state this assumption difference directly rather than implying
CARP dominates that literature.

## 5. Missing lower bound or impossibility analysis

### Reviewer concern

The paper showed when attacks succeed but did not specify when linkage is impossible, including the
case where agents share prompts, schemas, and business objects.

### Revision

- Added an observation-equivalence model. If `k` equally likely entities with `m` requests each have
  exchangeable complete provider-visible sequences, closed-set identity accuracy is at most `1/k`.
- Derived the expected pairwise precision bound `(m-1)/(km-1)` and F1 bound
  `2(m-1)/(m(k+1)-2)`; merging the full equivalence class attains the bound.
- Added a reproducible generator and table for `k=1,2,4,8,16`, giving four-request/entity F1 bounds
  `1.000, 0.600, 0.333, 0.176, 0.091`.
- Connected the formal condition to empirical negative controls: U4 user F1 0.029, zero linkage
  after complete later-alias rotation, and zero watchlist reach when stable-handle retention is zero.
- Clarified that identical system prompts or schemas alone are insufficient; the complete visible
  sequence, including content, timing, length, handles, and context growth, must be exchangeable.

### Response draft

We agree and added both a formal conditional bound and a reproducible controlled validation. The new
analysis makes the defense target explicit: shared prompts and schemas do not guarantee unlinkability
if task objects or replayed context remain distinct, whereas exchangeability of the complete
provider-visible sequence imposes an attack-independent ceiling.

## 7. Evaluation metrics and asymmetric error costs

### Revision

- Added exact TP/FP/FN/TN pair counts and positive-pair prevalence for held-out Open-SWE.
- Showed that the singleton baseline reaches 99.9166% pairwise accuracy with zero recall/F1 because
  only 0.0834% of request pairs are positive.
- Added false links per million negative pairs: 27.2 for Hybrid and 56.9 for CARP.
- Added a false-positive/false-negative cost-ratio sweep. At equal costs, weighted error per true pair
  is 0.034/0.068 for Hybrid/CARP; at a 100:1 false-positive cost, conservative abstention is preferred.
- Clarified that false positives contaminate profiles/watchlists while false negatives understate
  aggregation reach; no cost ratio is universal.

## 8. Mitigation and safety--utility tradeoffs

### Revision

- Expanded the main mitigation discussion and added a detailed supplementary section.
- Explained request/session-scoped identifiers, broker-side translation, typed-field minimization,
  local memory plus selective summaries/retrieval, and provider retention/access governance.
- Enumerated functional costs: broken cross-turn references, cache loss, debugging/audit difficulty,
  authorization/disambiguation failures, summary omissions, latency, and reasoning-quality loss.
- Reported the existing exploratory frontier, including session-scoped pseudonyms (session F1 .593,
  tool-character retention .995), type-only paths (.529/.888), and the combined transform
  (.030/.043).
- Explicitly retained the limitation that text retention is not task success; a deployable defense
  needs task completion, correctness, latency, tool-error, debugging, audit, and privacy metrics.

## 9. Insufficient figures

### Revision

- Added a four-panel overview figure that visualizes paired channel removal, concurrency stress,
  sparse scaling, and observation-equivalence bounds.
- Replaced the text-heavy takeaway table rather than simply adding more material.
- Kept the existing framework figure and T3 longitudinal result figure, yielding one method figure
  and two result figures in the main paper.

## 10. Writing style and missing formal definitions

### Revision

- Added a formal mathematical definition of provider-side linkage risk as excess achievable linkage
  score over no-information controls.
- Defined a linkage channel through a controlled transformation that reduces the risk while truth is
  held fixed.
- Replaced repeated `CARP-Content` terminology with the plain-language `content stage` in the main
  paper and rewrote CARP around five active-voice verbs.
- Replaced compressed parameter prose with conceptual explanations and moved exact configurations to
  the supplement.
