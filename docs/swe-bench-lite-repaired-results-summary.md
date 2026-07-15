# SWE-bench Lite Repaired Workflow Results Summary

Status: schema-flexible importer, balanced sampling, audit, M0 attack probe, and
`no_repository_fields` ablation have been run.

This dataset is an independent real-repository validation set, not raw Agent API evidence.
It builds agent-like request sequences from real SWE-bench Lite issue, patch, and test rows.

## Import

Balanced repaired sample:

```bash
uv run python -m agent_privacy.data.swe_workflows \
  --use-hf \
  --hf-dataset princeton-nlp/SWE-bench_Lite \
  --hf-config default \
  --hf-split test \
  --output-dir artifacts/datasets/swe_bench_lite_repaired_balanced_sample \
  --limit 100 \
  --max-per-repo 5
```

Audit:

```bash
uv run python -m agent_privacy.data.audit \
  --dataset-dir artifacts/datasets/swe_bench_lite_repaired_balanced_sample \
  --output docs/swe-bench-lite-repaired-balanced-audit.md
```

## Dataset

- Source: `princeton-nlp/SWE-bench_Lite`
- Config: `default`
- Split: `test`
- Source rows seen: 300
- Workflows used: 57
- Requests: 228
- Projects/repos: 12
- Owners/org-like labels: 12
- User-level ground truth: unavailable
- Attack-view markers: repaired `repository=` context appears in all 228 requests

The earlier unbalanced limit-100 sample had only two repositories, so its project/owner
results should not be used as evidence beyond importer smoke testing.

## Results

M0 repaired sample:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/swe_bench_lite_repaired_balanced_sample \
  --output results/swe_bench_lite_repaired_balanced_m0 \
  --defenses M0 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations none \
  --skip-profile \
  --open-swe-fast-features
```

| Method | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.237 | 0.327 | 0.327 |
| Rare | 0.000 | 1.000 | 0.175 |
| Tool/schema | 0.026 | 0.149 | 0.149 |
| Hybrid | 0.329 | 1.000 | 1.000 |

No-repository-fields ablation:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/swe_bench_lite_repaired_balanced_sample \
  --output results/swe_bench_lite_repaired_balanced_no_repository_m0 \
  --defenses M0 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations no_repository_fields \
  --skip-profile \
  --open-swe-fast-features
```

| Method | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.237 | 0.327 | 0.327 |
| Rare | 0.000 | 0.000 | 0.174 |
| Tool/schema | 0.026 | 0.149 | 0.149 |
| Hybrid | 0.254 | 0.000 | 0.000 |

## Interpretation

- The balanced sample is suitable as a repaired-workflow sanity check because it spans 12
  repositories instead of two.
- Project/repo and owner/org recovery in this repaired dataset is driven by the explicit
  `repository=<owner>/<repo>` context inserted by the importer.
- Removing the repaired repository field collapses hybrid project and owner/org F1 to zero.
- Session recovery is weak-to-moderate and should not be used as the main paper evidence.
- This supports the paper's risk-control rule: repaired workflow results are validation and
  boundary evidence, while Open-SWE raw/no-repair remains the primary evidence line.

## Natural Repair Policy

An alternate repair policy was added to avoid injecting explicit `repository=` or workspace
context into the attack view:

```bash
uv run python -m agent_privacy.data.swe_workflows \
  --use-hf \
  --hf-dataset princeton-nlp/SWE-bench_Lite \
  --hf-config default \
  --hf-split test \
  --output-dir artifacts/datasets/swe_bench_lite_natural_balanced_sample \
  --limit 100 \
  --max-per-repo 5 \
  --repair-context-mode natural
```

Audit:

- `docs/swe-bench-lite-natural-balanced-audit.md`
- 57 workflows, 228 requests, 12 repos/owners
- no `repository_field` leakage marker
- no `[repair_context]` marker
- no non-provider fields in `attack_view.jsonl`

M0 natural-policy result:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/swe_bench_lite_natural_balanced_sample \
  --output results/swe_bench_lite_natural_balanced_m0 \
  --defenses M0 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations none \
  --skip-profile \
  --open-swe-fast-features
```

| Method | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.237 | 0.327 | 0.327 |
| Rare | 0.000 | 0.000 | 0.174 |
| Tool/schema | 0.026 | 0.149 | 0.149 |
| Hybrid | 0.260 | 0.000 | 0.000 |

No-path natural-policy result:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/swe_bench_lite_natural_balanced_sample \
  --output results/swe_bench_lite_natural_balanced_no_paths_m0 \
  --defenses M0 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations no_paths \
  --skip-profile \
  --open-swe-fast-features
```

| Method | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.237 | 0.327 | 0.327 |
| Rare | 0.000 | 0.000 | 0.182 |
| Tool/schema | 0.026 | 0.149 | 0.149 |
| Hybrid | 0.205 | 0.000 | 0.000 |

Interpretation:

- Without explicit repaired repository context, the SWE-bench Lite repaired workflow sample
  does not support project/repo or owner/org recovery under the current low-cost attacks.
- The remaining session signal is weak and partly path/artifact dependent.
- This is useful negative evidence: real issue/patch artifacts alone are not enough in this
  repaired workflow scaffold to reproduce the Open-SWE workspace-artifact result.
