# Agent-Native Linkage and Fidelity Upgrade TODO

Status markers: `[ ]` planned, `[~]` implemented but gate not passed, `[x]` gate passed,
`[!]` blocked with the documented fallback in effect.

This document is the execution contract for the post-review upgrade. The existing CARP
implementation and its reported tables remain a frozen, reproducible baseline. New code lives
behind separate modules and is promoted into the paper only after its stated gate passes.

## Research invariants

1. **Agent-native evidence first.** Linkage is driven by state replay, context growth,
   tool-call/result causality, typed persistent handles, and structural conflicts. Generic text
   similarity may be a comparison, but is not the causal explanation of the method.
2. **One provider pass.** The hot path consumes requests once in timestamp order. It may retain
   a fixed-size state per request for output/evaluation, but may not rescan the traffic file.
3. **Bound every non-essential structure.** Sketches, posting lists, candidates per request, and
   component evidence are capped. Union-find labels are the unavoidable linear output state.
4. **Precision before forced coverage.** A merge needs multiple independent evidence families,
   no hard conflict, and a best-versus-runner-up margin. Otherwise the method abstains.
5. **Provenance is evaluation-only.** Source IDs, truth labels, fidelity metadata, and edit logs
   never enter the attack view or attack features.
6. **No invented realism.** Fidelity-focused transformations may replace existing spans but may
   not add messages, tool calls, tool results, or claims of timestamps absent from the source.
7. **Evidence before prose.** A result enters the main paper only after code, a deterministic
   command, a test, and a machine-readable result exist.

## Phase summary

| Phase | Deliverable | Status | Promotion evidence |
|---|---|---:|---|
| P0 | Baseline freeze and contracts | [x] | Existing CARP unchanged; smoke baseline recorded below |
| P1 | Fixed-size Agent request state | [x] | State-cap and replay-containment tests |
| P2 | Replay, tool-causality, and conflict evidence | [x] | Positive/negative smoke pair matrix |
| P3 | One-pass bounded candidate index | [x] | Posting/candidate caps, expiry, one-shot iterator |
| P4 | Risk-controlled workflow merge | [x] | Smoke + two-corpus precision/contamination gates |
| P5 | Hierarchical typed linkage | [x] | Level-specific handles; schema/domain do not merge identity |
| E0 | Selective and contamination metrics | [x] | Exact fixtures and cross-corpus reports |
| D0 | Fidelity taxonomy and manifests | [x] | Schema/round-trip and exactness guards |
| D1 | Span-level trace-preserving transformer | [x] | Structural invariance and edit replay audit |
| D2 | Distribution/fidelity audit | [x] | JS, KS, edit ratio, classifier AUC report |
| S0 | 10K feasibility | [x] | Runtime, comparisons, postings, bytes/request |
| S1 | 100K regression | [x] | Near-linear slope and bounded active work set |
| S2 | 500K/1M optional scale gate | [x] | 500K passed; 1M unnecessary repetition |
| X0 | Cross-dataset comparison and paper promotion | [x] | CARP, generic text, and Agent-evidence ablations passed |

## P0 — Freeze baseline and define interfaces

### P0.1 Preserve the current reference attack

- **Objective:** keep every existing CARP command/result reproducible while developing the new
  method independently.
- **Input/output contract:** no behavior change in `attacks/pipeline.py`; new entry points use a
  distinct `agent_state` package and method name.
- **Feasibility gate:** existing full test suite passes before and after the upgrade; the bundled
  tool-agent smoke baseline remains session F1 = 1.0.
- **Failure fallback:** remove integration hooks and retain the new implementation as an
  experimental standalone command.
- **Paper evidence:** CARP remains the fixed reference attack; any new method is reported as an
  extension rather than silently changing old rows.
- **Status:** [x] Baseline inspected. Current hybrid smoke: session F1 1.0; user/project/org F1 0.0.

### P0.2 Define attack-state and decision contracts

- **Objective:** make bounded memory and abstention inspectable rather than implicit.
- **Input:** one provider-visible request row.
- **Output:** a fixed-cap `AgentRequestState`; candidate `LinkDecision` records with support,
  conflicts, evidence families, margin, and disposition; level-specific cluster labels; runtime
  counters.
- **Feasibility gate:** state serialization contains no raw message text or truth/provenance
  fields, and every variable-length field has a tested cap.
- **Failure fallback:** hash or drop the offending unbounded field; never raise a cap merely to
  pass a fixture.
- **Paper evidence:** method pseudocode, memory bound, and auditable abstention definition.
- **Status:** [x] Contract implemented in `agent_state/model.py`; cap and raw-text absence tested.

## P1 — Agent-native request representation

### P1.1 State-evolution sketches

- **Objective:** represent cumulative Agent context as a directed state extension rather than a
  symmetric bag-of-text comparison.
- **Input:** ordered role/name/content events in one provider-visible request.
- **Output:** capped bottom-k hashes for replayable events, initial task, recent context, and tool
  observations; role/message counts and context length.
- **Feasibility gate:** for every two-turn smoke workflow, directed containment from turn 1 to
  turn 2 is at least 0.8; every cross-workflow pair is below the acceptance threshold.
- **Failure fallback:** combine exact event hashes with capped within-event shingles; do not use
  an unbounded full-text shingle set.
- **Paper evidence:** replay-containment distribution and ablation.
- **Status:** [x] Cumulative smoke extensions have replay containment 1.0; cross-workflow pairs stay below 0.75. Incremental Open-SWE windows use the documented resource-continuity path.

### P1.2 Tool transition and typed handle state

- **Objective:** expose Agent-specific action/observation continuity.
- **Input:** tool-role messages, tool names/schemas, structured content, and explicit identifiers.
- **Output:** capped tool names, argument keys, observation hashes, action types, error/resource
  fingerprints, and user/project/org/context handles.
- **Feasibility gate:** the smoke second turns expose the correct tool observations and retain the
  workflow's order/reservation/customer/account handles; schemas alone cannot create a link.
- **Failure fallback:** retain only conservative structured/explicit handle patterns and mark
  unsupported fields unknown instead of guessing a type.
- **Paper evidence:** evidence-family frequency and causal-transition ablation.
- **Status:** [x] Tool/action/typed-handle extraction and schema-only negative case pass.

## P2 — Support and negative evidence

### P2.1 Directed support score

- **Objective:** require independent causal evidence instead of a single tuned similarity score.
- **Input:** an earlier and later `AgentRequestState`.
- **Output:** replay containment, initial-root agreement, handle overlap, tool/resource continuity,
  time/length growth, evidence-family count, and a bounded score.
- **Feasibility gate:** all true smoke turn pairs pass the minimum support and family count; tool
  schema/system prompt equality by itself scores below acceptance.
- **Failure fallback:** increase abstention and report coverage loss; do not weaken the independent
  family requirement to recover recall.
- **Paper evidence:** interpretable edge examples and threshold-insensitivity grid.
- **Status:** [x] Independent evidence families, score, gap, and runner-up margin are emitted per decision.

### P2.2 Hard conflicts and component contamination guards

- **Objective:** prevent transitive false merges from overwhelming locally plausible edges.
- **Input:** pair and component summaries.
- **Output:** named conflicts for incompatible strong users/tenants, competing initial roots,
  time reversal, and alias bridges across strong components.
- **Feasibility gate:** customer/order conflicts block cross-workflow smoke merges; shared retail
  schemas do not collapse the retail workflows.
- **Failure fallback:** quarantine the ambiguous handle as a heavy hitter and abstain on the
  component merge.
- **Paper evidence:** false-merge amplification and conflict-ablation table.
- **Status:** [x] Strong user/org conflicts and competing roots are tested; weak resource continuity abstains.

## P3 — One-pass bounded retrieval

### P3.1 Streaming candidate index

- **Objective:** retrieve plausible predecessors without all-pairs comparison or repeated scans.
- **Input:** one state at a time in timestamp order.
- **Output:** candidates from replay bands, initial-task roots, typed handles, tool observations,
  and an active temporal window.
- **Feasibility gate:** posting list length, active postings, and candidates/request never exceed
  configuration caps; the input iterator is consumed exactly once.
- **Failure fallback:** suppress overfull heavy-hitter keys and rely on the remaining independent
  indexes; log the suppressed-key count.
- **Paper evidence:** asymptotic analysis plus empirical candidate comparisons/request.
- **Status:** [x] One-shot iterators pass; candidates cap at 96; postings cap at 64 and expire after the active window.

### P3.2 Memory accounting

- **Objective:** make scale claims based on measured retained state, not only wall-clock time.
- **Input:** state/index/union-find counters during a run.
- **Output:** peak postings, retained state hashes, estimated bytes/request, component sizes, and
  candidate/decision counters.
- **Feasibility gate:** sketches and posting lists stay capped on adversarial repeated-schema and
  repeated-handle fixtures.
- **Failure fallback:** replace exact retained evidence with capped hashes and evict expired weak
  postings; preserve strong-label output state.
- **Paper evidence:** memory slope and heavy-hitter stress plot.
- **Status:** [x] Active state/posting peaks are measured separately from linear union-find/output state.

## P4/P5 — Risk-controlled hierarchical linkage

### P4.1 Workflow component merge

- **Objective:** recover request-to-workflow chains with high precision.
- **Input:** ranked predecessor candidates and component summaries.
- **Output:** accept/reject/abstain decision; accepted edges update workflow union-find and bounded
  component evidence.
- **Feasibility gate:** bundled smoke workflow/session pairwise F1 = 1.0, zero cross-workflow
  merges, and at least one explicit abstention on a schema-only distractor test.
- **Failure fallback:** retain pair predictions without transitive component merge and report the
  loss of workflow reconstruction.
- **Paper evidence:** precision/recall and risk-coverage curve.
- **Status:** [x] Smoke workflow F1/precision/recall = 1.0. Open-SWE and tau accepted-edge precision = 1.0 with zero contaminated requests at the validated operating point.

### P5.1 Workflow-to-entity hierarchy

- **Objective:** separate strong workflow reconstruction from more uncertain cross-workflow
  user/project/tenant linkage.
- **Input:** completed workflow summaries with typed handles.
- **Output:** separate user, project, and org labels; a level merges only on evidence valid for
  that level.
- **Feasibility gate:** workflow edges propagate within a hierarchy; cross-workflow user/project/
  org merges require same-level handles and never infer retail-wide identity from schema/domain
  alone.
- **Failure fallback:** leave higher levels as singleton workflows and report unavailable recall.
- **Paper evidence:** hierarchy-specific validity and abstention table.
- **Status:** [x] Workflow edges propagate internally; cross-workflow levels use only same-level typed handles. Smoke user/project F1 = 1.0; org stays conservative (F1 0.6).

## E0 — Evaluation beyond F1

### E0.1 Selective linkage and risk coverage

- **Objective:** quantify the precision/coverage tradeoff of abstention.
- **Input:** scored decisions and pair truth.
- **Output:** accepted-edge precision, true-edge coverage, abstention rate, and risk-coverage points
  over score/margin thresholds.
- **Feasibility gate:** exact hand-computed fixtures agree with the implementation.
- **Failure fallback:** report edge-level selective metrics separately from cluster metrics.
- **Paper evidence:** risk-coverage curve and chosen operating point.
- **Status:** [x] Exact fixture passes. Reports include accepted-edge precision, true-edge coverage, abstention, and rejection.

### E0.2 False-merge amplification

- **Objective:** measure how one bad edge contaminates downstream profiles/components.
- **Input:** predicted labels and workflow/entity truth.
- **Output:** mixed components, contaminated requests, largest mixed component, false-positive
  pairs, and contaminated-requests-per-false-edge.
- **Feasibility gate:** a synthetic bridge joining two pure clusters produces the expected closed-
  form counts.
- **Failure fallback:** report the raw mixed-component and contaminated-request counts.
- **Paper evidence:** safety comparison against CARP and conflict ablations.
- **Status:** [x] Closed-form bridge fixture passes; corpus reports show zero mixed components after risk-gate refinement.

## D0/D1 — Fidelity-certified trace reconstruction

### D0.1 Fidelity taxonomy and manifest

- **Objective:** distinguish evidence strength at dataset and field level.
- **Contract:** `F3` exact provider payload; `F2` framework-faithful reconstruction; `F1`
  trajectory-prefix reconstruction; `F0` controlled intervention/stress. Each manifest records
  source, field fidelity, timestamp status, transformations, and unsupported claims.
- **Feasibility gate:** enum/schema round-trip and validation reject unknown levels or a claimed
  exact field with a declared transformation.
- **Failure fallback:** downgrade the affected field/dataset and surface the reason.
- **Paper evidence:** concise dataset evidence table and explicit claim boundary.
- **Status:** [x] `F0`–`F3`, field fidelity, manifest validation, and exactness guard implemented and tested.

### D1.1 Trace-preserving span transformer

- **Objective:** increase environmental diversity by pseudonymizing/recombining existing trace
  spans without fabricating Agent behavior.
- **Input:** provider rows plus a stable scope and declared replacement categories.
- **Output:** transformed provider rows and separate `RequestLineage` records containing content
  hashes and span-level `TransformationEdit`s.
- **Feasibility gate:** message count, role/name sequence, tool sequence, and tool schemas are
  byte-equivalent; every changed character belongs to a declared edit; applying the edit map to
  the source reproduces transformed content; provenance fields never appear in attack rows.
- **Failure fallback:** skip overlapping/unparseable spans and record them as unsupported instead
  of rewriting a whole message.
- **Paper evidence:** edit coverage and qualitative provenance examples.
- **Status:** [x] Smoke audit: 20 declared edits; roles, message/tool sequence, names, and schemas preserved; every edit replays from its source hash.

## D2 — Fidelity and realism audit

### D2.1 Structural and distribution audit

- **Objective:** quantify what reconstruction preserves and what it changes.
- **Input:** aligned source/transformed rows.
- **Output:** role/tool sequence preservation, message/tool counts, length ratio, edited-character
  ratio, handle density, context-growth distribution, categorical JS divergence, numeric KS
  statistics, and a structural two-sample classifier AUC.
- **Feasibility gate:** identity transformation yields zero divergence and AUC 0.5; smoke
  pseudonymization preserves all structural sequences and changes only declared spans.
- **Failure fallback:** label highly distinguishable transforms F0/stress and exclude them from
  realism claims.
- **Paper evidence:** fidelity audit table; distinguishability is reported, never hidden.
- **Status:** [x] Identity audit gives JS/KS 0 and AUC 0.5. Smoke pseudonymization preserves structure but AUC 0.861, so it is correctly retained as F0 controlled intervention.

## S0/S1/S2 — Scale validation

### S0.1 Deterministic 10K replay stress

- **Objective:** validate correctness and caps before expensive runs.
- **Input:** deterministic re-keyed/re-timestamped repetitions of public smoke traces; no model API.
- **Output:** runtime/counter JSON.
- **Feasibility gate:** 10K completes, candidate comparisons are bounded by
  `requests × max_candidates`, postings respect caps, and no shared-schema collapse occurs.
- **Failure fallback:** profile the dominant index, lower caps, and rerun 10K before proceeding.
- **Paper evidence:** engineering feasibility only, explicitly not prevalence evidence.
- **Status:** [x] 10K in 3.68 s (2,714 req/s); peak active states 1,801; peak postings 17,716; all caps pass.

### S1.1 100K regression

- **Objective:** test near-linear scaling of the one-pass implementation.
- **Input/output:** same generator and metrics as S0 at 100K.
- **Feasibility gate:** comparisons/request and estimated bytes/request remain bounded; runtime and
  retained-state growth are consistent with linear scaling from 10K within a documented tolerance.
- **Failure fallback:** stop at 10K and report the observed bottleneck; do not extrapolate a 1M claim.
- **Paper evidence:** scale table with scope limited to computation, not traffic realism.
- **Status:** [x] 100K in 38.99 s (2,565 req/s); active-state/posting peaks unchanged; RSS 120,784 KiB from linear label/output state.

### S2.1 Optional 500K/1M run

- **Objective:** extend, not manufacture, the scale result.
- **Gate to start:** S1 projected peak RSS and runtime fit the available environment with safety
  margin. The run itself must preserve all caps.
- **Failure fallback:** publish measured 10K/100K results and an analytical bound only.
- **Paper evidence:** optional artifact appendix row.
- **Status:** [x] 500K in 188.82 s (2,648 req/s); peak active states 1,801 and postings 17,716; RSS 445,444 KiB. A 1M rerun is not required for the same scaling claim.

## X0 — Comparative evaluation and promotion rule

### X0.1 Baselines and ablations

- **Objective:** resolve whether the new algorithm is a contribution or merely a measurement tool.
- **Required comparisons:** frozen CARP; typed-handle only; replay only; replay + tools; full model;
  full model without conflicts; and, where dependencies/data permit, a generic entity-resolution
  or embedding retrieval baseline under the same candidate/memory accounting.
- **Feasibility gate:** commands generate reproducible CSV/Markdown tables on both an Open-SWE
  corpus and a tau-bench corpus.
- **Failure fallback:** position the method explicitly as an interpretable reference attack and
  narrow the contribution claim.
- **Paper evidence:** main comparison and transfer table.
- **Status:** [x] Frozen CARP, a bounded generic hashed-text nearest-neighbor baseline, and replay/tool-resource/typed-handle/conflict ablations completed on Open-SWE and tau-bench with one shared Agent-native configuration. A deep learned ER model remains an optional strengthening experiment, not a feasibility blocker.

### X0.2 Main-paper promotion rule

The Agent-native method may replace or join CARP in the main result only if it:

1. keeps bundled smoke workflow F1 at 1.0 with no cross-workflow merge;
2. improves selective precision, false-merge amplification, or coverage at matched precision;
3. satisfies all configured memory/candidate caps;
4. transfers across at least Open-SWE and tau-bench without dataset-specific threshold tuning;
5. has deterministic commands, tests, tables, and a limitations statement.

Otherwise it remains a clearly labeled exploratory extension in the supplement. This is a valid
research outcome and prevents method novelty from being claimed ahead of evidence.

## Execution log

| Date | Gate | Command/artifact | Result |
|---|---|---|---|
| 2026-07-17 | P0 baseline | bundled tool-agent smoke + frozen `hybrid` | session F1 1.0; higher levels abstain/split |
| 2026-07-17 | P1–P5 smoke | `pytest tests/test_agent_state_linkage.py` | bounded state, conflicts, expiry, and workflow F1 1.0 pass |
| 2026-07-17 | E0 | `pytest tests/test_selective_metrics.py` | exact selective and false-merge fixtures pass |
| 2026-07-17 | D0–D2 | `pytest tests/test_trace_fidelity.py` | structural preservation passes; distinguishable transform remains F0 |
| 2026-07-17 | X0 Open-SWE | `results/agent_native/open_swe_sample100.json` | precision 1.0, F1 0.394, coverage 0.390, zero contamination |
| 2026-07-17 | X0 tau | `results/agent_native/tau_historical_sample200.json` | precision 1.0, F1 0.164, coverage 0.374, zero contamination |
| 2026-07-17 | X0 ablations | `docs/tables/agent_native_ablations.*` | Open-SWE depends on tool/resource continuity; tau combines replay and handles |
| 2026-07-17 | X0 generic text | `docs/tables/generic_text_linkage_baseline.*` | Agent-native improves F1, contamination, and comparisons/request on both corpora |
| 2026-07-17 | S0/S1/S2 | 10K/100K/500K controlled replay | 2.5–2.7K req/s; active work set fixed; output state linear |
