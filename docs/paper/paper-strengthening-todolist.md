# Paper Strengthening TODO

This checklist tracks the work needed to move the paper from a multi-signal attack study to a
stronger provider-side reconstruction paper with a memorable method, broader evidence, concrete
cost reporting, defenses, and ethics.

Status legend:

- `[x]` completed and indexed.
- `[~]` partially completed; usable but still improvable.
- `[ ]` pending.

## P0: Method Memory Point

- [x] Define the signature method as **CARP: Cache-Anchored Rarity Percolation**.
  - Goal: turn the current provider_lowcost feature pipeline into a named, cost-aware linkage
    algorithm rather than a list of known features.
  - Artifact: `docs/paper/carp-method.md`.
  - Acceptance: includes threat-model fit, algorithm stages, edge score, complexity, and how it
    maps to `provider_lowcost`.

- [x] Add CARP/cost terminology to the paper draft.
  - Goal: make the paper's method contribution memorable.
  - Artifact: `docs/paper/plain-paper-draft-zh.md`.
  - Acceptance: abstract, method, and experiment sections use CARP wording consistently.

## P0: Low-Cost Quantification

- [x] Generate a dedicated candidate-reduction and cost table.
  - Goal: replace vague "low cost" claims with numbers.
  - Artifact: `docs/tables/open_swe_provider_lowcost_cost_model.{csv,md}`.
  - Acceptance: reports requests, all-pairs count, candidate pairs, reduction factor,
    candidate pairs/request, measured seconds/request, extrapolated CPU-hours/1M requests, peak
    RSS, and main F1 values.

- [x] Add cost table to artifact index and paper draft.
  - Goal: make low-cost claims citeable.
  - Artifact: `docs/artifact-index.md`; `docs/paper/plain-paper-draft-zh.md`.
  - Acceptance: the cost section no longer relies only on qualitative language.

## P0: Warm-Start Longitudinal Attack

- [x] Implement a warm-start watchlist experiment.
  - Goal: evaluate the realistic setting where provider first cold-starts profiles, then uses
    watchlist tokens to relink later traffic.
  - Artifact: `src/agent_privacy/experiments/summarize_warm_start_watchlist.py`.
  - Acceptance: works on Dataset B U3/U4 snapshots without rerunning attacks.

- [x] Generate warm-start tables.
  - Goal: quantify profile/watchlist relinking across time.
  - Artifact: `docs/tables/open_swe_user_overlay_warm_start_watchlist.{csv,md}`.
  - Acceptance: includes train snapshot, test snapshot, truth level, profiles, watch tokens,
    matched requests, precision, recall, F1, and assignment coverage.

- [x] Add warm-start result to the paper draft.
  - Goal: support the "continuous provider profiling" narrative.
  - Artifact: `docs/paper/plain-paper-draft-zh.md`;
    `docs/tables/open_swe_user_overlay_warm_start_retrieval.md`.
  - Acceptance: the paper distinguishes cold-start discovery, assignment-style watchlists, and
    target-centric retrieval. The new retrieval diagnostic shows warm-start can retain useful
    candidates when anchors come from true early traffic or reasonably pure predicted clusters,
    while hard-shared user signals remain difficult.

## P1: Heterogeneous Dataset

- [x] Add a non-code Agent dataset plan.
  - Goal: address Open-SWE being software-engineering-heavy.
  - Artifact: `docs/paper/heterogeneous-agent-dataset-plan.md`.
  - Acceptance: compares tau-bench, WebArena/BrowserGym, and OSWorld; selects first target and
    defines provider-view fields and expected linkage signals.

- [x] Add importer scaffold for the selected heterogeneous dataset.
  - Goal: make the next experiment executable when data/network is available.
  - Artifact: `src/agent_privacy/data/tau_bench.py`;
    `tests/test_provider_view_and_snapshots.py`.
  - Acceptance: converts local JSON/JSONL or historical trajectory directories into the standard
    provider-view contract, with a provider-view audit test and smoke fixture.

- [x] Run at least one non-code Agent linkage table.
  - Goal: reduce external-validity criticism.
  - Artifact: `docs/tables/tau_bench_historical_sample200_provider_lowcost.md`;
    `docs/tables/tau_bench_historical_provider_view_audit.md`.
  - Acceptance: reports a real historical airline/retail sample with no-path/no-repo/no-tool-schema
    feature ablations. Current result supports non-code session reconstruction but not user/org
    reconstruction; this limitation is now stated in the paper draft.

- [x] Add a tau-bench three-layer overlay analogous to Dataset B.
  - Goal: make non-code org/user/project evaluation possible instead of relying on airline/retail
    domain labels and rough business-entity proxies.
  - Artifact: `src/agent_privacy/data/tau_bench_overlay.py`;
    `configs/tau_bench_overlay_t3.json`;
    `artifacts/datasets/tau_bench_overlay_t3`;
    `docs/tables/tau_bench_overlay_t3_first_2500_provider_lowcost.md`.
  - Acceptance: builds provider-view-only logs with synthetic tenant/customer/business-project
    labels on real tau-bench historical trajectories; first provider_lowcost result is summarized.

- [x] Add business-entity-aware CARP refinement for tau-bench T3.
  - Goal: use non-code anchors such as customer_ref, account_cache, queue, internal_domain,
    reservation/order/product IDs, and tenant aliases for user/project/org linkage.
  - Artifact: `src/agent_privacy/features/extract.py`;
    `src/agent_privacy/attacks/pipeline.py`;
    `docs/tables/tau_bench_overlay_t3_first_2500_provider_lowcost.md`.
  - Acceptance: improves T3 user/project linkage over the previous generic provider_lowcost
    baseline while preserving no-path/no-repo claim boundaries. The first-2,500 snapshot now shows
    high-precision low-recall T3 linkage: user F1 0.214, project F1 0.159, org F1 0.297, with
    user/project/org precision 0.954/1.000/1.000.

- [x] Improve tau-bench T3 recall without broad-field over-linking.
  - Goal: add customer/order/reservation/product/case-aware entity linking and longitudinal
    watchlists while keeping `loyalty_tier`, `region`, standalone `service_line`, and random
    `case_id` out of strong union anchors.
  - Artifact: `src/agent_privacy/attacks/pipeline.py`;
    `src/agent_privacy/experiments/summarize_tau_bench_watchlist.py`;
    `docs/tables/tau_bench_t3_entity_percolation.md`;
    `docs/tables/tau_bench_t3_entity_watchlist.md`.
  - Acceptance: increases T3 user/project/org recall over the first refinement without reducing
    user/project/org precision below the paper-defined safety threshold.

## P1: Profile Reconstruction

- [x] Add a structured-evidence profile reconstruction baseline.
  - Goal: move beyond flat keyword matching while keeping the experiment offline and reproducible.
  - Artifact: `src/agent_privacy/profiling/structured_profiler.py`;
    `src/agent_privacy/experiments/compare_profilers.py`;
    `docs/tables/open_swe_structured_profile_comparison.md`.
  - Acceptance: combines lexical, manifest, command, repository, service, and domain detectors;
    reports per-value evidence/confidence; compares predicted clusters with truth-cluster upper
    bound. Audited technical-profile micro F1 improves from 0.623 to 0.809, versus a 0.812
    truth-cluster upper bound.

- [x] Add a calibrated dense-semantic NLP profile baseline.
  - Goal: test whether second-stage semantic evidence retrieval adds value beyond structural
    detectors without using a generative LLM.
  - Artifact: `src/agent_privacy/profiling/semantic_profiler.py`;
    `src/agent_privacy/experiments/run_semantic_profile.py`;
    `docs/tables/open_swe_semantic_profile_comparison.md`;
    `docs/tables/open_swe_semantic_profile_novel_evidence.md`.
  - Acceptance: fixed ontology, message-level spans, MiniLM retrieval, contradiction filtering,
    multi-request aggregation, org-disjoint calibration/test split, runtime/RSS reporting, and
    request-level novel-evidence audit. The held-out result is intentionally reported as a
    negative incremental result: semantic F1 0.807 versus structured F1 0.807.

## P1: Mitigation Scope

- [x] Supersede the earlier defense-frontier framing with attack-surface implications.
  - Goal: keep defenses outside the paper's research questions and contributions.
  - Artifact: `docs/paper/content-linkage-defense-frontier.md`.
  - Acceptance: derives bounded mitigation implications from strict-removal and turn-delta controls
    without claiming task utility or deployment validation.

- [x] Add scope-limited mitigation framing to paper draft.
  - Goal: make mitigation analysis feel intentional and complete for the current scope.
  - Artifact: `docs/paper/plain-paper-draft-zh.md`.
  - Acceptance: the main paper contains only mitigation implications, does not introduce a
    defense RQ or contribution, and moves detailed proxy tables to appendix/artifact material.

## P1: Ethics and Compliance

- [x] Add ethics and governance discussion.
  - Goal: address provider-as-attacker sensitivity.
  - Artifact: `docs/paper/ethics-and-governance.md`.
  - Acceptance: covers non-identification, synthetic user overlays, redacted examples, provider
    governance, retention, purpose limitation, and artifact release boundaries.

- [~] Add ethics wording to abstract/introduction.
  - Goal: make responsible-use framing visible.
  - Artifact: `docs/paper/plain-paper-draft-zh.md`.
  - Acceptance: abstract and final discussion mention ethics/governance implications.

## P2: Final Paper Packaging

- [x] Replace the AAAI template stub with the paper and migrate it into the supplied Overleaf project.
  - Goal: produce a submission-shaped LaTeX source after the Chinese draft stabilizes.
  - Artifact: `docs/overleaf/api.tex`.
  - Acceptance: contains paper title, abstract, sections, tables/figures placeholders, and no
    AAAI template instruction body.

- [ ] Add a figure plan.
  - Goal: define 2-3 memorable visuals.
  - Artifact: `docs/paper/figure-plan.md`.
  - Acceptance: includes CARP pipeline, evidence layering, and privacy/utility frontier figures.

## Running Checks

After each implementation batch:

```bash
uv run ruff check .
uv run python -m unittest discover -s tests -q
uv run python -m json.tool docs/artifact-manifest.json
```
