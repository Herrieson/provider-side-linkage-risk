# Open-SWE-Traces Results Summary

Historical note: this document records early Open-SWE import and attack development. Current
paper-facing paths are indexed in `docs/artifact-index.md`, `docs/dataset-index.md`, and
`docs/result-index.md`. Early sample datasets/results mentioned below are archived under
`artifacts/datasets/_archive/legacy_samples/` and `results/_archive/legacy_open_swe_samples/`.

Status: importer and dataset runner scaffold added. Raw and repaired Hugging Face samples have
been imported, audited, and evaluated for attack feasibility.

For the full paper experiment roadmap, see `docs/paper-experiment-todolist.md`.

## Import

Local JSONL/parquet sample:

```bash
uv run python -m agent_privacy.data.open_swe_traces \
  --input-path /path/to/open_swe_sample.jsonl \
  --output-dir artifacts/datasets/_archive/legacy_samples/open_swe_traces_sample \
  --limit 1000
```

Hugging Face streaming sample:

```bash
uv run python -m agent_privacy.data.open_swe_traces \
  --use-hf \
  --hf-config openhands \
  --hf-split minimax_m25 \
  --output-dir artifacts/datasets/_archive/legacy_samples/open_swe_traces_raw_sample \
  --limit 100 \
  --repair-mode none
```

If the `datasets` package is unavailable, the importer falls back to the Hugging Face
dataset-server rows API for small samples.

## Run

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/_archive/legacy_samples/open_swe_traces_raw_sample \
  --output results/_archive/legacy_open_swe_samples/open_swe_traces_raw_m0 \
  --levels session org \
  --methods temporal rare tool hybrid \
  --skip-profile
```

User-level scoring is intentionally skipped for the first Open-SWE-Traces import because the
dataset does not provide reliable user identity ground truth.

## First Raw Sample

Source:

- dataset: `nvidia/Open-SWE-Traces`
- config: `openhands`
- split: `minimax_m25`
- trajectories: 100
- requests: 1,200
- user-level ground truth: unavailable
- repair mode: `none`

Dataset audit:

- `docs/open-swe-traces-raw-audit.md`
- 100 workflows, 96 projects, 94 owners/orgs
- no added repair fields
- no non-provider fields in `attack_view.jsonl`
- conversion provenance is stored separately in `request_provenance.jsonl`
- original trajectory content already contains workspace paths in all 1,200 converted requests

M0 attack-only clustering:

| Method | Session F1 | Project/Repo F1 | Org/Owner F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.116 | 0.036 | 0.037 |
| Rare | 0.000 | 1.000 | 0.021 |
| Tool/schema | 0.018 | 0.020 | 0.021 |
| Hybrid | 0.998 | 1.000 | 1.000 |

Interpretation:

- The raw Open-SWE trajectory sample is already highly linkable.
- This result does not depend on added `repository=` repair fields.
- The main content signal appears to come from repeated trajectory context and real workspace
  paths/tool observations in the OpenHands traces.
- Rare repository/path features alone recover project/repo clusters, but not sessions.
- The hybrid attack recovers sessions because it combines repeated context, paths, and
  trajectory-local overlap.

## Repair Comparison

The repository/workspace repair sample used:

- `repair_mode=repository_workspace`
- explicit `repository=<owner>/<repo>`
- explicit `/workspace/<owner>__<repo>`
- audit: `docs/open-swe-traces-repo-workspace-audit.md`

M0 attack-only result:

| Dataset | Session F1 | Org/Owner F1 |
| --- | ---: | ---: |
| Raw, no repair | 0.998 | 1.000 |
| Repository/workspace repair | 0.998 | 1.000 |

The repair version does not improve this 100-trajectory sample because the raw OpenHands
trajectory already exposes sufficient workspace/tool context.

## Earlier Defense Probe

The earlier defense probe used the repaired sample and should not be treated as the current
priority. It is retained only as a rough indication:

| Defense | Session F1 | Org/Owner F1 |
| --- | ---: | ---: |
| M0 Raw | 0.998 | 1.000 |
| M1 Secret filtering | 0.998 | 1.000 |
| M2 Entity redaction | 0.660 | 0.651 |
| M3 Context minimization | 0.995 | 1.000 |
| M4 Broker mixing | 0.998 | 1.000 |
| M6 Combined | 0.616 | 0.651 |

M0 baselines:

| Method | Session F1 | Org/Owner F1 |
| --- | ---: | ---: |
| Temporal | 0.116 | 0.037 |
| Rare | 0.000 | 0.021 |
| Tool/schema | 0.018 | 0.021 |
| Hybrid | 0.998 | 1.000 |

## Immediate Next Step

The next work should stabilize the attack evidence, not defenses:

1. Scale raw sample from 100 to 1,000 trajectories.
2. Add a no-workspace-path ablation to test whether workflow reconstruction still works after
   removing path-like identifiers from the raw trajectory.
3. Add project-level scoring separately from owner/org scoring.
4. Add candidate-edge diagnostics so we can explain which raw features link workflows.
5. Only after the raw attack evidence is stable, revisit defenses and profile recovery.

## 1,000-Trajectory Raw Update

Dataset:

- Open-SWE-Traces
- config: `openhands`
- split: `minimax_m25`
- trajectories: 1,000
- converted requests: 12,000
- workflows: 1,000
- projects/repos: 639
- owners/orgs: 556
- repair mode: `none`
- user-level ground truth: unavailable

Audit:

- `docs/open-swe-traces-raw-1000-audit.md`
- no non-provider fields in `attack_view.jsonl`
- no repair fields
- all 12,000 converted requests contain workspace paths from the original trajectory content
- 15 requests contain `repository=` in the raw trajectory content
- median request has 34 messages and 7,945 tokens

The full 12,000-request cumulative-context attack is too expensive with the original
in-memory implementation because each request repeats prior trajectory context. The runner
now has a streaming feature path and supports turn filtering. The first scalable 1,000-row
probe uses final turns only:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000 \
  --output results/open_swe_traces_raw_1000_turn12_m0_fast \
  --defenses M0 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations none \
  --skip-profile \
  --turn-ids 12 \
  --open-swe-fast-features
```

Final-turn raw result:

| Method | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.000 | 0.004 | 0.006 |
| Rare | 0.000 | 0.995 | 0.005 |
| Tool/schema | 0.000 | 0.004 | 0.005 |
| Hybrid | 0.000 | 0.995 | 0.984 |

Session F1 is not meaningful in the final-turn-only probe because there is one request per
workflow after filtering. This probe is mainly for project/repo and owner/org linkability.

No-workspace-path final-turn ablation:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000 \
  --output results/open_swe_traces_raw_1000_turn12_no_workspace_fast \
  --defenses M0 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations no_workspace_paths \
  --skip-profile \
  --turn-ids 12 \
  --open-swe-fast-features
```

| Method | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.000 | 0.004 | 0.006 |
| Rare | 0.000 | 0.000 | 0.005 |
| Tool/schema | 0.000 | 0.004 | 0.005 |
| Hybrid | 0.000 | 0.000 | 0.000 |

Interpretation:

- In final-turn Open-SWE raw traces, project/repo and owner/org reconstruction are driven
  primarily by workspace path artifacts.
- Removing `/workspace/...` paths collapses project and owner/org recovery in this probe.
- This supports the Plan B1 concern in `docs/paper-experiment-todolist.md`: the first
  Open-SWE 1,000 evidence line is best framed as workspace/tool-environment leakage, not as
  proof that arbitrary semantic context alone is sufficient.
- The next probe should evaluate session reconstruction on a smaller turn sample, such as
  turns `3 6 9 12`, with the same streaming/fast-feature path.

## 1,000-Trajectory Turn-Sampled Session Probe

To evaluate session reconstruction without scanning all 12 cumulative turns, the next probe
uses turns `3 6 9 12` from each workflow. This gives 4,000 requests across 1,000 workflows.
The run excludes the expensive `prefix` baseline for now and uses the streaming fast-feature
path:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000 \
  --output results/open_swe_traces_raw_1000_turns_3_6_9_12_m0_fast \
  --defenses M0 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations none \
  --skip-profile \
  --turn-ids 3 6 9 12 \
  --open-swe-fast-features
```

Raw turn-sampled result:

| Method | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.092 | 0.021 | 0.022 |
| Rare | 0.000 | 0.996 | 0.007 |
| Tool/schema | 0.001 | 0.005 | 0.007 |
| Hybrid | 0.985 | 0.996 | 0.987 |

No-workspace-path turn-sampled ablation:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000 \
  --output results/open_swe_traces_raw_1000_turns_3_6_9_12_no_workspace_fast \
  --defenses M0 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations no_workspace_paths \
  --skip-profile \
  --turn-ids 3 6 9 12 \
  --open-swe-fast-features
```

| Method | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.092 | 0.021 | 0.022 |
| Rare | 0.000 | 0.000 | 0.007 |
| Tool/schema | 0.001 | 0.005 | 0.007 |
| Hybrid | 0.529 | 0.000 | 0.000 |

Interpretation:

- Raw turn-sampled Open-SWE traces are highly linkable at session, project, and owner/org
  levels under the hybrid attack.
- Workspace paths are the dominant project/repo and owner/org signal. Removing
  `/workspace/...` collapses project and owner/org recovery in this probe.
- Session reconstruction remains partially possible after workspace removal: hybrid session F1
  drops from `0.985` to `0.529`. This suggests there are residual within-trajectory signals,
  likely context overlap and repeated tool/task text.
- The next ablation should isolate those residual session signals by adding a no-context-overlap
  or turn-delta representation, plus candidate-edge diagnostics on a smaller sample.

## Turn-Delta Ablation

The cumulative Open-SWE request format repeats prior trajectory context. To test whether
session reconstruction is mostly caused by cumulative-context overlap, a turn-delta view was
constructed from turns `3 6 9 12`:

```bash
uv run python -m agent_privacy.data.turn_delta \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000 \
  --output-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --turn-ids 3 6 9 12
```

This view is an ablation dataset, not a raw provider log. It replaces each selected request's
message list with only the messages added since the previous selected turn in the same
workflow. The corresponding audit is
`docs/open-swe-traces-raw-1000-turn-delta-3-6-9-12-audit.md`.

Audit summary:

- requests: 4,000
- workflows: 1,000
- non-provider fields in `attack_view.jsonl`: none
- workspace paths: 3,999 requests
- `repository=` markers: 2 requests
- median request: 17 messages and 2,704 tokens
- dataset size: 143 MB, compared with 1.1 GB for the cumulative 12-turn view

Raw turn-delta result:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --output results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_m0_fast \
  --defenses M0 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations none \
  --skip-profile \
  --open-swe-fast-features
```

| Method | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.092 | 0.021 | 0.022 |
| Rare | 0.000 | 0.996 | 0.007 |
| Tool/schema | 0.001 | 0.005 | 0.007 |
| Hybrid | 0.116 | 0.996 | 0.987 |

No-workspace-path turn-delta result:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --output results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_no_workspace_fast \
  --defenses M0 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations no_workspace_paths \
  --skip-profile \
  --open-swe-fast-features
```

| Method | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.092 | 0.021 | 0.022 |
| Rare | 0.000 | 0.000 | 0.007 |
| Tool/schema | 0.001 | 0.005 | 0.007 |
| Hybrid | 0.023 | 0.000 | 0.000 |

Interpretation:

- The high cumulative-view session F1 (`0.985`) is mostly explained by repeated prior
  trajectory context. In the turn-delta view, hybrid session F1 falls to `0.116`.
- Removing workspace paths from the turn-delta view further reduces hybrid session F1 to
  `0.023`, close to weak baselines.
- Project/repo and owner/org recovery remain very high in raw turn-delta because workspace
  artifacts remain present in almost every delta request.
- Removing workspace paths collapses project/repo and owner/org recovery to zero, confirming
  that Open-SWE project/owner linkability is dominated by workspace artifacts.
- This strengthens the current paper framing: Open-SWE primarily supports an
  agent-environment artifact leakage claim, while broader semantic-linkability claims need
  additional datasets or a different ablation setup.

## Candidate-Edge Diagnostics

A 100-workflow sample was created for edge diagnostics:

```bash
uv run python -m agent_privacy.data.sample_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000 \
  --output-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --limit-workflows 100

uv run python -m agent_privacy.data.sample_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --output-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12_sample100 \
  --limit-workflows 100
```

Hybrid candidate edges were written with `--write-edge-diagnostics` and
`--edge-diagnostics-limit 2000`. The edge-reason summary is:

| View | Edges | Session Links | Project Links | Repo Full | Workspace Path | High Shingle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Cumulative raw | 670 | 606 | 664 | 664 | 658 | 636 |
| Cumulative no-workspace | 217 | 217 | 0 | 0 | 0 | 217 |
| Turn-delta raw | 679 | 49 | 664 | 664 | 664 | 52 |
| Turn-delta no-workspace | 6 | 6 | 0 | 0 | 0 | 6 |

Interpretation:

- Cumulative raw edges are dominated by workspace/repo features plus high shingle overlap.
- Removing workspace paths removes project edges and leaves only context-overlap-driven
  session edges in the cumulative view.
- In the turn-delta view, project edges are still dominated by workspace/repo artifacts, while
  session edges are sparse.
- In turn-delta no-workspace, only six diagnostic edges remain in the 100-workflow sample.
  This is consistent with the near-baseline session F1 in the 1,000-workflow turn-delta
  no-workspace result.

## Preliminary Defense/Utility Probe

A small defense probe was run on the 100-workflow sample, restricted to turns `3 6 9 12`,
with fast Open-SWE feature extraction:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --output results/open_swe_traces_raw_1000_sample100_turns_3_6_9_12_defense_probe_fast \
  --defenses M0 M1 M2 M3 M4 M6 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations none \
  --skip-profile \
  --turn-ids 3 6 9 12 \
  --open-swe-fast-features
```

Hybrid clustering results:

| Defense | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| M0 | 0.974 | 1.000 | 1.000 |
| M1 secret filtering | 0.974 | 1.000 | 1.000 |
| M2 entity/path redaction | 0.165 | 0.000 | 0.000 |
| M3 context minimization | 0.974 | 1.000 | 1.000 |
| M4 broker mixing | 0.962 | 1.000 | 1.000 |
| M6 combined | 0.030 | 0.000 | 0.000 |

Utility/cost proxy results:

| Defense | Token Retention | Tool Char Retention | Workspace Paths Removed |
| --- | ---: | ---: | ---: |
| M0 | 1.000 | 1.000 | 0 |
| M1 | 1.000 | 1.000 | 0 |
| M2 | 1.000 | 0.858 | 83,138 |
| M3 | 0.131 | 0.060 | 72,514 |
| M4 | 1.000 | 1.000 | 0 |
| M6 | 0.131 | 0.043 | 83,138 |

Interpretation:

- Secret filtering does not affect Open-SWE linkability because the dominant signal is not
  L5 secrets.
- Broker timestamp/length mixing alone does not address workspace/repo artifacts.
- Generic context minimization removes a large amount of context but still leaves enough
  workspace/path signal for perfect project/owner recovery in this sample.
- Entity/path redaction and the combined defense break project/owner recovery, but this is
  only a preliminary probe because utility is measured by retention proxies rather than task
  success.
- The next mitigation work should focus on selective workspace/path minimization and
  pseudonymization variants, not only broad context truncation.

## Selective Workspace/Path Mitigation Probe

Three targeted mitigation variants were added and evaluated on the same 100-workflow,
turn-sampled Open-SWE probe:

- `M7_WORKSPACE_STABLE`: replace `/workspace/<owner>__<repo>` slugs with stable global
  pseudonyms while preserving the rest of the path.
- `M8_WORKSPACE_SESSION`: replace workspace slugs with request-scoped pseudonyms.
- `M9_PATH_TYPE_ONLY`: replace full workspace paths with `[WORKSPACE_PATH]`.

Command:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --output results/open_swe_traces_raw_1000_sample100_turns_3_6_9_12_selective_mitigation_fast \
  --defenses M0 M7_WORKSPACE_STABLE M8_WORKSPACE_SESSION M9_PATH_TYPE_ONLY M2 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations none \
  --skip-profile \
  --turn-ids 3 6 9 12 \
  --open-swe-fast-features
```

Hybrid clustering results:

| Defense | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| M0 | 0.974 | 1.000 | 1.000 |
| M7 stable workspace pseudonym | 0.974 | 0.000 | 0.000 |
| M8 request-scoped workspace pseudonym | 0.593 | 0.000 | 0.000 |
| M9 workspace path type-only | 0.529 | 0.000 | 0.000 |
| M2 broad entity/path redaction | 0.165 | 0.000 | 0.000 |

Utility/cost proxy results:

| Defense | Token Retention | Tool Char Retention | Workspace Paths Removed |
| --- | ---: | ---: | ---: |
| M0 | 1.000 | 1.000 | 0 |
| M7 stable workspace pseudonym | 1.000 | 0.970 | 0 |
| M8 request-scoped workspace pseudonym | 1.000 | 0.995 | 0 |
| M9 workspace path type-only | 1.000 | 0.888 | 83,138 |
| M2 broad entity/path redaction | 1.000 | 0.858 | 83,138 |

Interpretation:

- Stable workspace pseudonymization is enough to break project/owner recovery in this probe,
  but it preserves session reconstruction because the same pseudonym remains a stable
  within-workflow signal.
- Request-scoped workspace pseudonymization and type-only workspace paths also break
  project/owner recovery and reduce session reconstruction.
- Broad M2 redaction reduces session reconstruction the most but removes more non-workspace
  content. This gives a concrete privacy/utility frontier for the mitigation section.

## Cross-Split Replication: OpenHands qwen35_122b

A second OpenHands split was imported as raw/no-repair evidence:

```bash
uv run python -m agent_privacy.data.open_swe_traces \
  --use-hf \
  --hf-config openhands \
  --hf-split qwen35_122b \
  --output-dir artifacts/datasets/open_swe_traces_openhands_qwen35_raw_500 \
  --limit 500 \
  --repair-mode none
```

Dataset:

- trajectories: 500
- requests: 6,000
- workflows: 500
- projects/repos: 395
- owners/orgs: 371
- repair mode: `none`
- audit: `docs/open-swe-traces-openhands-qwen35-raw-500-audit.md`
- non-provider fields in `attack_view.jsonl`: none
- workspace paths: all 6,000 requests
- median request: 73 messages and 9,602 tokens

Turn-sampled cumulative raw probe:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_openhands_qwen35_raw_500 \
  --output results/open_swe_traces_openhands_qwen35_raw_500_turns_3_6_9_12_m0_fast \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --defenses M0 \
  --ablations none \
  --skip-profile \
  --turn-ids 3 6 9 12 \
  --open-swe-fast-features
```

No-workspace cumulative probe:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_openhands_qwen35_raw_500 \
  --output results/open_swe_traces_openhands_qwen35_raw_500_turns_3_6_9_12_no_workspace_fast \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --defenses M0 \
  --ablations no_workspace_paths \
  --skip-profile \
  --turn-ids 3 6 9 12 \
  --open-swe-fast-features
```

Turn-delta dataset:

```bash
uv run python -m agent_privacy.data.turn_delta \
  --dataset-dir artifacts/datasets/open_swe_traces_openhands_qwen35_raw_500 \
  --output-dir artifacts/datasets/open_swe_traces_openhands_qwen35_raw_500_turn_delta_3_6_9_12 \
  --turn-ids 3 6 9 12
```

Hybrid results:

| View | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Cumulative raw | 0.974 | 1.000 | 1.000 |
| Cumulative no-workspace | 0.548 | 0.000 | 0.000 |
| Turn-delta raw | 0.038 | 0.996 | 0.997 |
| Turn-delta no-workspace | 0.009 | 0.000 | 0.000 |

Interpretation:

- The qwen35_122b split reproduces the main OpenHands/minimax trend.
- Cumulative-view session reconstruction is high, but it falls sharply in the turn-delta view,
  indicating that repeated prior context drives most session reconstruction.
- Project/repo and owner/org reconstruction remain near-perfect in raw turn-delta because
  workspace artifacts remain present in every delta request.
- Removing workspace paths collapses project/repo and owner/org reconstruction to zero.
- This strengthens the current framing: across two OpenHands splits, the robust signal is
  workspace/tool-environment artifact leakage, not broad semantic recovery.

## Cross-Scaffold Replication: SWE-agent minimax_m25

A SWE-agent split was imported to test whether the OpenHands workspace-artifact behavior is
scaffold-specific:

```bash
uv run python -m agent_privacy.data.open_swe_traces \
  --use-hf \
  --hf-config sweagent \
  --hf-split minimax_m25 \
  --output-dir artifacts/datasets/open_swe_traces_sweagent_minimax_raw_500 \
  --limit 500 \
  --repair-mode none
```

Dataset:

- trajectories: 500
- requests: 6,000
- workflows: 500
- projects/repos: 374
- owners/orgs: 347
- repair mode: `none`
- audit: `docs/open-swe-traces-sweagent-minimax-raw-500-audit.md`
- non-provider fields in `attack_view.jsonl`: none
- workspace paths: 66 of 6,000 requests
- raw `repository=` markers: 11 of 6,000 requests
- median request: 40 messages and 7,557 tokens

Turn-delta dataset:

```bash
uv run python -m agent_privacy.data.turn_delta \
  --dataset-dir artifacts/datasets/open_swe_traces_sweagent_minimax_raw_500 \
  --output-dir artifacts/datasets/open_swe_traces_sweagent_minimax_raw_500_turn_delta_3_6_9_12 \
  --turn-ids 3 6 9 12
```

Hybrid results:

| View | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Cumulative raw | 0.711 | 0.000 | 0.000 |
| Cumulative no-workspace | 0.711 | 0.000 | 0.000 |
| Turn-delta raw | 0.028 | 0.000 | 0.000 |
| Turn-delta no-workspace | 0.028 | 0.000 | 0.000 |

Interpretation:

- SWE-agent does not reproduce the OpenHands project/owner leakage pattern under the current
  low-cost attacks.
- The audit explains why: workspace paths appear in only 66 of 6,000 cumulative requests,
  compared with all requests in the OpenHands samples.
- Session reconstruction is still meaningful in cumulative SWE-agent traces, but turn-delta
  reduces session F1 from `0.711` to `0.028`, again showing that repeated prior context is the
  dominant session signal.
- No-workspace has no measurable effect because workspace paths are sparse in this scaffold.
- This supports the Plan B2 framing: agent scaffold conventions materially change linkability
  risk. OpenHands exposes stable workspace/repo artifacts; SWE-agent, at least on this split,
  does not expose enough of those artifacts for project/owner reconstruction.

## Cross-Scaffold Replication: SWE-agent qwen35_122b

The remaining Open-SWE scaffold/split cell was imported as raw/no-repair evidence:

```bash
uv run python -m agent_privacy.data.open_swe_traces \
  --use-hf \
  --hf-config sweagent \
  --hf-split qwen35_122b \
  --output-dir artifacts/datasets/open_swe_traces_sweagent_qwen35_raw_500 \
  --limit 500 \
  --repair-mode none
```

Dataset:

- trajectories: 500
- requests: 6,000
- workflows: 500
- projects/repos: 404
- owners/orgs: 366
- repair mode: `none`
- audit: `docs/open-swe-traces-sweagent-qwen35-raw-500-audit.md`
- non-provider fields in `attack_view.jsonl`: none
- workspace paths: 53 of 6,000 requests
- raw `repository=` markers: 11 of 6,000 requests
- median request: 101 messages and 11,297 tokens

Turn-delta dataset:

```bash
uv run python -m agent_privacy.data.turn_delta \
  --dataset-dir artifacts/datasets/open_swe_traces_sweagent_qwen35_raw_500 \
  --output-dir artifacts/datasets/open_swe_traces_sweagent_qwen35_raw_500_turn_delta_3_6_9_12 \
  --turn-ids 3 6 9 12
```

Hybrid results:

| View | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Cumulative raw | 0.700 | 0.000 | 0.000 |
| Cumulative no-workspace | 0.697 | 0.000 | 0.000 |
| Turn-delta raw | 0.003 | 0.000 | 0.000 |
| Turn-delta no-workspace | 0.003 | 0.000 | 0.000 |

Interpretation:

- SWE-agent/qwen35_122b reproduces the SWE-agent/minimax pattern.
- Project/repo and owner/org reconstruction remain zero under the current low-cost attacks.
- Session reconstruction exists in cumulative traces but disappears in the turn-delta view.
- No-workspace has no meaningful effect because workspace paths are sparse in this scaffold.
- With both SWE-agent splits complete, the scaffold-specific conclusion is stronger:
  OpenHands exposes stable workspace/repo artifacts that enable project/owner reconstruction;
  SWE-agent largely does not, while both scaffolds still show cumulative-context session risk.

## Generated 2x2 Tables

The current Open-SWE 2x2 matrix can be regenerated from existing result directories:

```bash
uv run python -m agent_privacy.experiments.summarize_open_swe --output-dir docs/tables
```

Outputs:

- `docs/tables/open_swe_2x2_dataset_matrix.csv`
- `docs/tables/open_swe_2x2_attack_matrix.csv`
- `docs/tables/open_swe_2x2_attack_matrix.md`
- `docs/tables/open_swe_openhands_minimax_sample_size_sweep.csv`
- `docs/tables/open_swe_openhands_minimax_sample_size_sweep.md`

The generated attack matrix currently summarizes 16 rows: four scaffold/split cells times
four views (`cumulative_raw`, `cumulative_no_workspace`, `turn_delta_raw`,
`turn_delta_no_workspace`). The dataset matrix records the current sample mode for each cell.
The sample-size sweep table summarizes the current OpenHands/minimax 100/250/500 HF streaming
reservoir runs and keeps the 1,000 first-N run as an anchor.

## Reservoir Sample-Size Sweep: OpenHands/minimax

The importer now supports Hugging Face `datasets` streaming with reservoir sampling. The
current sweep scans 5,000 source rows for each HF reservoir point and selects 100, 250, or 500
trajectories with seed 7. The 1,000 first-N result is retained as a fixed historical anchor,
not as another reservoir point.

```bash
uv run python -m agent_privacy.data.open_swe_traces \
  --use-hf \
  --hf-config openhands \
  --hf-split minimax_m25 \
  --output-dir artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_500_seed7_hf \
  --limit 500 \
  --sample-mode reservoir \
  --max-source-rows 5000 \
  --seed 7 \
  --repair-mode none
```

Generated table:

- `docs/tables/open_swe_openhands_minimax_sample_size_sweep.md`
- `docs/tables/open_swe_openhands_minimax_sample_size_sweep.csv`

Hybrid results:

| Sample | Mode | Source Rows | View | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| 100 | reservoir | 5,000 | Cumulative raw | 0.987 | 1.000 | 1.000 |
| 100 | reservoir | 5,000 | Cumulative no-workspace | 0.601 | 0.000 | 0.000 |
| 100 | reservoir | 5,000 | Turn-delta raw | 0.174 | 1.000 | 1.000 |
| 100 | reservoir | 5,000 | Turn-delta no-workspace | 0.033 | 0.000 | 0.000 |
| 250 | reservoir | 5,000 | Cumulative raw | 1.000 | 1.000 | 1.000 |
| 250 | reservoir | 5,000 | Cumulative no-workspace | 0.570 | 0.000 | 0.000 |
| 250 | reservoir | 5,000 | Turn-delta raw | 0.124 | 0.996 | 0.997 |
| 250 | reservoir | 5,000 | Turn-delta no-workspace | 0.026 | 0.000 | 0.000 |
| 500 | reservoir | 5,000 | Cumulative raw | 0.997 | 0.974 | 0.935 |
| 500 | reservoir | 5,000 | Cumulative no-workspace | 0.594 | 0.000 | 0.000 |
| 500 | reservoir | 5,000 | Turn-delta raw | 0.116 | 0.973 | 0.935 |
| 500 | reservoir | 5,000 | Turn-delta no-workspace | 0.021 | 0.000 | 0.000 |
| 1,000 | first-N | 1,000 | Cumulative raw | 0.985 | 0.996 | 0.987 |
| 1,000 | first-N | 1,000 | Cumulative no-workspace | 0.529 | 0.000 | 0.000 |
| 1,000 | first-N | 1,000 | Turn-delta raw | 0.116 | 0.996 | 0.987 |
| 1,000 | first-N | 1,000 | Turn-delta no-workspace | 0.023 | 0.000 | 0.000 |

Interpretation:

- The HF streaming reservoir samples reproduce the OpenHands/minimax first-N trend at 100,
  250, and 500 workflows.
- Project/owner reconstruction is consistently driven by workspace artifacts: every
  no-workspace view has project/repo and owner/org F1 `0.000`.
- Cumulative session reconstruction remains high after workspace removal (`0.570` to `0.601`
  for reservoir points), but the turn-delta no-workspace session F1 is low (`0.021` to
  `0.033`). This reinforces the claim that repeated prior context, not only workspace paths,
  explains cumulative session linkage.
- The 500-workflow reservoir point has lower project/owner F1 than the 100/250 points, but it
  preserves the qualitative conclusion and is still far above no-workspace. This is a reason
  to add bootstrap confidence intervals before claiming precise point estimates.
- The 1,000 row remains first-N, so the next robustness step is either a 1,000 HF reservoir run
  when compute/network are acceptable, or multiple seeds at 250/500.

For comparison, a local fallback workflow-level reservoir sample from the already imported
1,000-workflow OpenHands/minimax dataset was also run. This is useful when the Hugging Face
rows API is unstable, but should be described as a local derived sample rather than a
full-split reservoir sample.

```bash
uv run python -m agent_privacy.data.sample_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000 \
  --output-dir artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_250_seed7_local \
  --limit-workflows 250 \
  --sample-mode reservoir \
  --seed 7
```

Dataset:

- source dataset: `artifacts/datasets/open_swe_traces_raw_1000`
- source workflows: 1,000
- sampled workflows: 250
- requests: 3,000
- projects/repos: 211
- owners/orgs: 194
- audit: `docs/open-swe-traces-openhands-minimax-reservoir-250-seed7-local-audit.md`
- workspace paths: all 3,000 requests

Hybrid results:

| View | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | ---: | ---: | ---: |
| Cumulative raw | 0.989 | 1.000 | 1.000 |
| Cumulative no-workspace | 0.609 | 0.000 | 0.000 |
| Turn-delta raw | 0.118 | 1.000 | 1.000 |
| Turn-delta no-workspace | 0.020 | 0.000 | 0.000 |

The local fallback result also reproduces the same qualitative pattern.

## Gap-Closing Experiments

The follow-up gap-closing runs add feature-family ablations, turn-order metrics, and
technical profile reconstruction over the OpenHands/minimax sample. Summary tables are
generated by:

```bash
uv run python -m agent_privacy.experiments.summarize_gap_results --output-dir docs/tables
```

Generated tables:

- `docs/tables/open_swe_gap_feature_ablation.md`
- `docs/tables/open_swe_gap_ordering.md`
- `docs/tables/open_swe_gap_profile.md`

### Feature Ablation

Small-sample full-feature ablations were run on both cumulative and turn-delta views without
`--open-swe-fast-features`, so domain and trace features are actually enabled in the baseline.

| View | Ablation | Session F1 | Project/Repo F1 | Owner/Org F1 |
| --- | --- | ---: | ---: | ---: |
| Cumulative | none | 0.974 | 1.000 | 1.000 |
| Cumulative | no domains | 0.974 | 1.000 | 1.000 |
| Cumulative | no traces | 0.974 | 1.000 | 1.000 |
| Cumulative | no repo ids | 0.974 | 0.000 | 0.109 |
| Cumulative | no shingles/context overlap | 0.000 | 1.000 | 1.000 |
| Cumulative | no time/length | 0.789 | 1.000 | 1.000 |
| Turn-delta | none | 0.107 | 1.000 | 1.000 |
| Turn-delta | no domains | 0.107 | 1.000 | 1.000 |
| Turn-delta | no traces | 0.107 | 1.000 | 1.000 |
| Turn-delta | no repo ids | 0.107 | 0.000 | 0.037 |
| Turn-delta | no shingles/context overlap | 0.000 | 1.000 | 1.000 |
| Turn-delta | no time/length | 0.082 | 1.000 | 1.000 |

Interpretation:

- Project/repo reconstruction is driven by repo-derived identifiers. Removing repo IDs
  collapses project recovery to `0.000` in both cumulative and turn-delta views.
- Owner/org-like reconstruction is also mostly repo-artifact driven. Removing repo IDs leaves
  only weak owner/org signal.
- Session reconstruction is driven by text overlap / cumulative context. Removing shingles
  collapses session F1 to `0.000`, even though project and owner recovery remain perfect.
- Time and token length are auxiliary session signals. Removing them reduces cumulative
  session F1 from `0.974` to `0.789`, but does not affect project/owner recovery.
- Domains, traces, and tool/system fingerprints do not materially explain this Open-SWE
  result.

### Turn Ordering

The runner now reports both timestamp ordering and context-containment ordering inside pure
predicted session clusters. Current small-sample results are:

| View | Timestamp Pairwise Acc. | Context Pairwise Acc. | Evaluated Clusters |
| --- | ---: | ---: | ---: |
| Cumulative | 0.847 | 0.847 | 96 |
| Turn-delta | 0.750 | 0.750 | 28 |

The metric gap is now closed, but the current context-containment heuristic does not improve
over timestamp ordering on this sample. This should be reported as a baseline result, not as
evidence of strong turn-order reconstruction beyond timestamps.

### Technical Profile Reconstruction

Open-SWE technical profile truth was enriched with provider-visible clues such as build files,
package managers, frameworks, languages, CI clues, and repo names. The profiler was tightened
so `repo_names` are extracted only from explicit repository/workspace artifacts rather than
arbitrary identifiers such as test names.

| Field | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| build tools | 0.938 | 0.960 | 0.949 |
| package managers | 0.981 | 0.657 | 0.787 |
| frameworks | 0.637 | 0.683 | 0.659 |
| repo names | 0.837 | 0.516 | 0.638 |
| CI/CD systems | 0.764 | 0.494 | 0.600 |
| languages | 0.693 | 0.424 | 0.526 |
| service names | 0.021 | 0.002 | 0.003 |
| micro average | 0.676 | 0.499 | 0.574 |

Interpretation:

- Open-SWE now supports a limited but real technical profile claim: build tools, package
  managers, frameworks, repo names, CI clues, and languages can be recovered with measurable
  precision/recall from predicted owner/org-like clusters.
- `service_names` should not be used as an Open-SWE main result because the source lacks a
  stable service-name concept and the measured F1 is near zero.
- This still does not prove enterprise organization profiling. It supports technical profile
  clue reconstruction over real-repository agent traces.

## Provider-Lowcost Chain Experiment

To align the implementation with the two-stage attack narrative, a dedicated
`provider_lowcost` method was added. It models a cold-start provider-side pipeline:

1. group requests by provider-observable cache bucket when available;
2. build low-cost buckets over rare provider-visible artifacts such as traces, repo IDs,
   owner IDs, domains, and tool/system fingerprints;
3. use lightweight semantic signatures only as a strict auxiliary candidate signal;
4. refine session edges with context-overlap shingles and timing;
5. export ordered reconstructed workflows from predicted session clusters.

Open-SWE does not contain true provider cache-hit telemetry, so these rows fall back to
`cache_unavailable`. The cache stage is implemented and evaluated as unavailable for this
dataset rather than simulated into the raw attack view.

Command:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_sample100 \
  --output results/open_swe_provider_lowcost_cumulative_sample100_cluster \
  --defenses M0 \
  --levels session project org \
  --methods provider_lowcost \
  --ablations none \
  --feature-ablations none no_semantic no_shingles \
  --skip-profile \
  --turn-ids 3 6 9 12 \
  --write-reconstructed-workflows \
  --open-swe-fast-features
```

The corresponding turn-delta negative/control run uses
`artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12_sample100`.
Summary tables are generated by:

```bash
uv run python -m agent_privacy.experiments.summarize_provider_lowcost --output-dir docs/tables
```

Generated table:

- `docs/tables/open_swe_provider_lowcost.md`

Key results on 100 OpenHands/minimax workflows, turns `3 6 9 12`:

| View | Ablation | Session F1 | Project F1 | Owner/Org F1 | Reconstructed Workflows | Workflow Purity | Pairwise Order Acc. |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Cumulative | none | 0.882 | 1.000 | 1.000 | 91 | 0.954 | 0.859 |
| Cumulative | no semantic proxy | 0.882 | 1.000 | 1.000 | 91 | 0.954 | 0.859 |
| Cumulative | no shingles/context overlap | 0.000 | 1.000 | 1.000 | 400 | 1.000 | 0.000 |
| Turn-delta | none | 0.102 | 1.000 | 1.000 | 352 | 0.992 | 0.049 |
| Turn-delta | no semantic proxy | 0.102 | 1.000 | 1.000 | 352 | 0.992 | 0.049 |
| Turn-delta | no shingles/context overlap | 0.000 | 1.000 | 1.000 | 400 | 1.000 | 0.000 |

Interpretation:

- The provider-lowcost chain now implements the paper narrative as an explicit attack method
  rather than only as a loose description.
- On cumulative provider-view requests, it reconstructs session/workflow clusters with
  session F1 `0.882`, project/repo F1 `1.000`, and owner/org-like F1 `1.000`.
- Removing shingles/context-overlap collapses session reconstruction to `0.000`, while
  project and owner/org-like recovery stay perfect. This isolates the session signal as
  context carryover rather than repo identity.
- The turn-delta control removes cumulative context and drops session F1 to `0.102`, while
  project and owner/org-like recovery remain `1.000` because workspace/repo artifacts are
  still present.
- The semantic proxy ablation has no effect in this setting. It should be reported as a
  non-critical baseline: low-cost context overlap and rare environment artifacts are already
  sufficient for the main Open-SWE risk.
- The reconstructed workflow export gives an auditable stage-one-to-workflow artifact:
  cumulative workflows have mean purity `0.954` and pairwise order accuracy `0.859`.

Profile-derived watchlists were also implemented. They extract evidenced profile tokens from
predicted profiles and score how well those tokens retrieve matching future/same-snapshot
requests. Current same-snapshot Open-SWE watchlist scores are high recall but low precision,
so this component is an implemented mechanism, not yet strong real-data evidence for precise
long-term user tracking.

### Longitudinal Provider-View Snapshots

Cumulative provider-view snapshots were evaluated to test the "provider accumulates more
requests over time" part of the attack story. Two longitudinal tables are generated by:

```bash
uv run python -m agent_privacy.experiments.summarize_longitudinal --output-dir docs/tables
```

Generated tables:

- `docs/tables/open_swe_provider_lowcost_longitudinal.md`
- `docs/tables/open_swe_provider_lowcost_longitudinal_full_turns.md`

The first table is a fixed-budget sanity check: each snapshot is sampled to at most 100
workflows. It is useful for confirming that the provider-view schema and attack behavior are
stable across time snapshots, but after `first_4000` the sampled workflows are effectively the
same first-100 workflow slice, so it should not be used as the main data-volume scaling claim.

The stronger table uses full snapshots but evaluates fixed turns `3 6 9 12` for all workflows
available at that time point. This now runs through the 12,000-request snapshot after bounding
the provider-lowcost context-carryover candidate generation.

| Snapshot | Source Requests | Source Workflows | Evaluated Requests | Session F1 | Project F1 | Owner/Org F1 | Workflow Purity | Pairwise Order Acc. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| first 1,000 | 1,000 | 86 | 333 | 0.804 | 1.000 | 1.000 | 0.957 | 0.851 |
| first 4,000 | 4,000 | 334 | 1,334 | 0.965 | 1.000 | 1.000 | 0.989 | 0.841 |
| first 8,000 | 8,000 | 671 | 2,665 | 0.971 | 0.996 | 0.987 | 0.991 | 0.838 |
| first 12,000 | 12,000 | 1,000 | 4,000 | 0.970 | 0.996 | 0.987 | 0.990 | 0.836 |

For all completed points, `no_shingles/context-overlap` drops session F1 to `0.000` while project and
owner/org-like F1 remain high (`0.987` or better at the 8,000/12,000 points). This supports the
longitudinal version of the story: as the provider accumulates more Agent API requests and
workflows, context-overlap restores workflow/session chains, while repo/workspace artifacts
keep project and owner-like linkage stable.

The full all-turn 12,000-request view is still not evaluated end-to-end because the source
contains very large cumulative contexts. The completed longitudinal evidence is the full
snapshot, fixed-turn view, which evaluates 4,000 requests at the 12,000-request time point.

## Notes

- This dataset should be described as real-repository agent trajectory data, not enterprise
  production Agent logs.
- `attack_view.jsonl` is a provider-view approximation: plaintext messages, tool observations,
  model/API metadata, tool schema shape, token count, timestamp, and optional cache bucket are
  visible or derivable by a model API provider. Dataset provenance, source labels, repair
  metadata, and ground-truth labels are kept out of attack view.
- Timestamps are provider-visible in real logs, but Open-SWE timestamps are repair fields
  because the source trajectories do not contain true provider-log timing.
- `repo` owner is used as `org_id`; `repo` is used as `project_id`; `trajectory_id` is used
  as `workflow_id`.
- The current hybrid attack was adapted to extract `repo_owner`, `repo_name`, and `repo_full`
  features only from explicit `repository=` repair fields and `/workspace/<owner>__<repo>`
  paths. Raw OpenHands trajectories already contain workspace paths, so this extraction applies
  to raw data as well. It intentionally avoids treating arbitrary `a/b` text as a repository.
- Longitudinal provider-view snapshots have been generated under
  `artifacts/datasets/open_swe_traces_raw_1000_snapshots/` at 1,000, 4,000, 8,000, and 12,000
  requests. The `first_1000_requests` snapshot audit reports no non-provider attack-view
  fields and no non-provider `provider_metadata` fields.

## Paper-Readiness Gap Closure

Additional paper-control artifacts were added after the provider-lowcost and longitudinal
runs:

- `docs/tables/open_swe_controls_sample100.md` compares `provider_lowcost` against `random`
  and `oracle_size_random` controls on the Open-SWE sample100 fixed-turn setting. The
  provider-lowcost session F1 is `0.882`, while the random and oracle-size controls are
  approximately `0.016` and `0.012`.
- `docs/tables/open_swe_controls_sample100_bootstrap_ci.csv` reports workflow-level pairwise
  bootstrap confidence intervals for the same control comparison.
- `docs/tables/open_swe_lowcost_threshold_sweep.md` reports a context-overlap threshold sweep
  with feature time, attack time, candidate pairs, linked pairs, and session precision/recall/F1.
- `docs/tables/open_swe_profile_bounds.md` separates truth-cluster profile upper bounds from
  predicted-cluster profile recovery. The two are close, which indicates that the Open-SWE
  profile limitation is mostly a dataset/profile-truth limitation rather than a clustering-only
  limitation.
- `docs/tables/open_swe_profile_risk_levels.md` aggregates Open-SWE profile recovery into
  L1-L5 risk levels. The reliable Open-SWE claim is L1 technical and L2 project/repository
  clue recovery; L3/L4 are weak/noisy, and L5 secrets are excluded.
- `docs/tables/open_swe_2x2_bootstrap_ci.md` reports workflow-level bootstrap confidence
  intervals for the main Open-SWE 2x2 scaffold/split matrix.
- `docs/tables/open_swe_sweagent_minimax_local_reservoir_sweep.md` reports a SWE-agent/minimax
  100/250/500 local workflow-level reservoir sweep from the imported raw500 source. This is a
  robustness check against a single first-N SWE-agent row, not a full Hugging Face reservoir
  sample.
- `docs/tables/open_swe_defense_utility_frontier.md` summarizes preliminary privacy/utility
  frontier results for baseline redaction and selective workspace/path mitigation variants.
- `docs/tables/open_swe_runtime_cost.md` now includes a timed provider-lowcost sample100 rerun;
  older longitudinal rows still report `not_recorded` for wall-clock timings because those runs
  predate instrumentation.
- `docs/redacted-profile-examples.md` provides qualitative redacted reconstructed profile
  examples. These examples are illustrative; field-level profile tables remain the quantitative
  evidence.
- `docs/tables/provider_view_audit_summary.md` and `docs/dataset-card-*.md` document the
  provider-view fields, ground-truth levels, repair limitations, and user/org claim boundaries
  for Open-SWE, SWE-bench Lite adapted workflows, and Synthetic Dataset A.
- `docs/tables/paper_experiment_readiness.md` summarizes which paper requirements are now
  closed and which remain pending before submission.

Remaining paper gaps are now mainly large-scale repetition and stronger utility validation:
large longitudinal bootstrap CIs, optional full-source HF SWE-agent/minimax reservoir sampling,
full all-turn 12k provider-lowcost execution, and task-level utility/latency evaluation for
defenses. Open-SWE user-level reconstruction remains N/A because reliable real user labels are
not available; user-level mechanism evidence comes from the controlled synthetic benchmark.
