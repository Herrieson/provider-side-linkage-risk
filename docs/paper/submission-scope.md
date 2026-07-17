# Submission Scope Freeze

## Central Claim

Protocol-level identifier stripping is weaker than content de-identification. Plaintext LLM Agent
traffic can retain three distinct risks: direct content-anchor exposure, repeated-request workflow
continuity, and stability-dependent longitudinal propagation. Across code and tool traffic, the
root mechanisms are persistent content handles and context replay. The measured harm is unauthorized
aggregation into commercially and security-sensitive pseudonymous longitudinal views, not civil
identity recovery. Brokered stripping is an optional added privacy layer rather than a prevalence
claim; direct agent-to-provider deployments omit this step and may expose additional protocol
identifiers, while the paper measures residual linkage in the more protective brokered case.

## Main Contributions

1. Provider-side protocol-stripping threat model that identifies persistent content handles and
   context replay as cross-domain root mechanisms.
2. A three-surface measurement protocol with strict attack-view/truth separation, paired controls,
   cross-domain handle parsing, shared-resource ambiguity rejection, and natural non-code evidence.
3. CARP for bounded sparse discovery and ASL for selective Agent-state linkage using replay,
   tool/resource continuity, typed handles, conflict evidence, and abstention.
4. Concurrency/rephrasing, zero-label cross-scaffold, threshold, 500K scale, anchor-stability, and
   observation-equivalence tests; natural and controlled watchlists, partial profiling, cost, and
   uncertainty.

## Main-Paper Artifacts

- Figure 1: measurement contract and CARP/ASL paths,
  `docs/overleaf/figures/carp_pipeline.pdf`
- Figure 2: four-panel channels, concurrency, Agent-state gain, and indistinguishability summary,
  `docs/overleaf/figures/results_overview.pdf`
- Figure 3: hierarchical propagation and later-traffic watchlist,
  `docs/overleaf/figures/t3_longitudinal.pdf`
- Supplementary evidence-layer figure: `docs/overleaf/figures/evidence_layers.pdf`
- Open-SWE session baselines, bootstrap CIs, and ordering:
  `docs/tables/open_swe_main_session_evidence.md`
- Open-SWE direct exposure, strict removal, and candidate diagnostics:
  `docs/tables/open_swe_direct_exposure_audit.md`;
  `docs/tables/open_swe_strict_signal_removal.md`;
  `docs/tables/open_swe_candidate_diagnostics.md`
- Strict-removal second-stage project linkage:
  `docs/tables/open_swe_strict_semantic_project_linkage.md`;
  `docs/tables/open_swe_sweagent_strict_semantic_project_linkage.md`
- Zero-target-label transfer, held-out sensitivity, and controlled scale:
  `docs/tables/open_swe_cross_scaffold_zero_tuning.md`;
  `docs/tables/open_swe_heldout_threshold_robustness.md`;
  `docs/tables/carp_synthetic_scale.md`
- Held-out historical tau-bench baselines, domain breakdown, and calibrated operating point:
  `docs/tables/tau_bench_historical_evidence.md`
- Cross-domain handle audit and natural stable-handle user linkage:
  `docs/tables/cross_domain_stable_handle_audit.md`;
  `docs/tables/tau_bench_stable_user_linkage.md`
- tau-bench temporal/rephrasing stress and CARP-Content ablation:
  `docs/tables/tau_bench_temporal_stress.md`;
  `docs/tables/tau_bench_content_linkage_ablation.md`
- Natural tau watchlist and standard ANN comparison:
  `docs/tables/tau_bench_natural_user_watchlist.md`;
  `docs/tables/tau_bench_hnsw_ann_baseline.md`
- Open-SWE CARP and cross-workflow validity table:
  `docs/tables/open_swe_cross_workflow_entity_validity.md`
- T3 improvement and CI: `docs/tables/tau_bench_t3_entity_percolation.md`;
  `docs/tables/paper_extension_bootstrap_ci.md`
- T3 anchor statistics and stability stress:
  `docs/tables/tau_bench_t3_anchor_statistics.md`;
  `docs/tables/tau_bench_t3_anchor_robustness.md`
- Profile comparison: `docs/tables/open_swe_structured_profile_comparison.md`;
  `docs/tables/open_swe_semantic_profile_comparison.md`
- Cost model: `docs/tables/open_swe_provider_lowcost_cost_model.md`
- Observation-equivalence bound: `docs/tables/observation_indistinguishability.md`
- Pair imbalance and asymmetric error-cost audit: `docs/tables/open_swe_pairwise_cost_audit.md`

## Appendix-Only Material

- Full 2x2 scaffold/split matrix and reservoir sweeps.
- Evidence-layer figure, Synthetic A, and repaired SWE-bench validation.
- Dataset B U3/U4 detailed longitudinal tables and profile fields.
- Full threshold sweeps, controls, ablations, runtime rows, and bootstrap samples.
- Semantic-only novel evidence examples.
- Provider-view audits, dataset cards, and generation configs.
- Exploratory mitigation artifacts excluded from the submission claim set.

## Explicitly Out of Scope

- A new defense algorithm or task-utility defense evaluation.
- Active prompt injection or malicious model behavior.
- Recovery of real Open-SWE or tau-bench natural-person identities.
- Claims about enterprise organization recovery from GitHub-owner labels.
- Production cache telemetry or production provider-log measurements.
- A generative-LLM profiler upper bound.

## Defense Treatment

Defense is limited to a short mitigation-implications paragraph. The paper may state that persistent
namespace/business-object handles and cumulative context must be considered by privacy gateways and
provider log governance. It must not list defense as a contribution, introduce a defense RQ, or
claim task utility, deployment validation, or that the current attack-surface controls solve the
privacy problem.

## Seven-Page Priority

1. Threat model and provider-view boundary.
2. Direct exposure versus workflow-continuity distinction.
3. CARP sparse discovery and ASL Agent-state linkage, including the generic-text comparison.
4. Historical non-code evidence and controlled hierarchy-overlay stability.
5. Profile and semantic negative result.
6. Ethics, scope, and limitations.

When space is tight, move detailed baselines and secondary numeric results to the supplement before
shortening the threat model, Agent-native method, or main causal findings.
