# MVP Results Summary

Status: synthetic MVP complete. This result is useful for controlled debugging and initial
claim validation, but it should not be the only paper evidence. The paper should lead with
real-repository agent trajectory experiments after the Open-SWE-Traces evidence is scaled and
audited.

Historical note: the early MVP output directory is archived under
`results/_archive/legacy_mvp_smoke/mvp`. Current paper-facing synthetic evidence is the
Dataset A matrix summarized in `docs/tables/synthetic_matrix_summary.md`.

## Run

Command:

```bash
uv run python -m agent_privacy.experiments.run_mvp --config configs/mvp.json --output results/_archive/legacy_mvp_smoke/mvp
```

Dataset:

- 20 organizations
- 100 users
- 60 projects
- 16,000 non-noise Agent requests
- 2,400 outlier/noise requests
- 18,400 total requests
- 6 defense settings: `M0`, `M1`, `M2`, `M3`, `M4`, `M6`

## Clustering Results

Pairwise F1 for the main `hybrid` attack:

| Defense | Session F1 | User F1 | Org F1 |
| --- | ---: | ---: | ---: |
| M0 Raw | 0.855 | 1.000 | 0.769 |
| M1 Secret filtering | 0.855 | 1.000 | 0.769 |
| M2 Entity redaction | 0.000 | 0.000 | 0.000 |
| M3 Context minimization | 0.645 | 1.000 | 0.000 |
| M4 Broker mixing | 0.831 | 1.000 | 0.769 |
| M6 Combined | 0.000 | 0.000 | 0.000 |

Key baselines under `M0`:

| Method | Session F1 | User F1 | Org F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.058 | 0.036 | 0.054 |
| Rare features | 0.782 | 1.000 | 0.095 |
| Prefix overlap | 0.001 | 0.022 | 0.105 |
| Tool/schema | 0.001 | 0.019 | 0.086 |
| Hybrid | 0.855 | 1.000 | 0.769 |

Interpretation:

- Raw anonymous Agent logs are strongly linkable in this MVP setting.
- Secret filtering does not reduce workflow reconstruction because the attack does not depend on secrets.
- Broker timing mixing mostly weakens temporal signals, but content-side signals still dominate.
- Entity redaction and combined defense break the current content-linking attack.
- Context minimization weakens organization linking but still leaves session/user signals through local path and user-level artifacts in this generator.

## Profile Results

Micro profile reconstruction over hybrid organization clusters:

| Defense | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| M0 Raw | 0.774 | 0.772 | 0.773 |
| M1 Secret filtering | 0.774 | 0.772 | 0.773 |
| M2 Entity redaction | 0.000 | 0.000 | 0.000 |
| M3 Context minimization | 0.000 | 0.000 | 0.000 |
| M4 Broker mixing | 0.774 | 0.772 | 0.773 |
| M6 Combined | 0.000 | 0.000 | 0.000 |

Interpretation:

- When organization clusters are recovered, a simple evidence-based rule profiler recovers many technical and risk fields.
- Secret filtering does not affect L2-L4 profile recovery.
- In this MVP implementation, profile reconstruction is evaluated on predicted hybrid org clusters. When a defense breaks org clustering into singleton clusters, the profiler does not attempt organization profiles and the resulting recovery is zero.

## Current Limitations

- The data is synthetic. It includes hard negatives, shared templates, shared service names, mixed timing, and noise, but it is still generator-driven.
- User-level F1 is currently too high because local usernames in paths are strong quasi-identifiers. This is realistic for raw Agent logs but should be ablated.
- M2 uses stable redaction and is intentionally strong. Future experiments should split stable versus unstable redaction because stable placeholders may preserve linkability.
- The attack is heuristic and interpretable. A stronger version should add threshold sweeps, candidate recall measurement, and optional embedding baselines.
- The profile evaluator uses majority-org assignment for predicted clusters. Future evaluation should separately report profile quality on ground-truth clusters and predicted clusters.
- `pytest` was not available in the environment; `ruff` and end-to-end smoke/MVP runs were used for validation.

## Next Experiments

The complete paper-scale task list is maintained in `docs/paper-experiment-todolist.md`.

1. Add feature ablations for hybrid:
   - no trace/context identifiers
   - no username/path
   - no domain
   - no service/repo identifiers
   - no timing

2. Add redaction variants:
   - stable entity redaction
   - per-session redaction
   - per-request redaction
   - type-only redaction

3. Add profile upper bound:
   - profile recovery on ground-truth org clusters
   - profile recovery on predicted org clusters

4. Add scale/difficulty sweep:
   - shared template rate
   - shared repo/service rate
   - context carryover rate
   - noise rate
   - time mixing window

5. Build Dataset B from open-source projects to test whether the result generalizes beyond generator templates.
