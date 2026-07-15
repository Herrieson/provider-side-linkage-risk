# Real-Data Dataset Plan

## Position

The synthetic Dataset A is useful for controlled debugging, but it should not be the main
paper dataset. The main benchmark should use real open-source artifacts as the substrate
and only add the minimum missing information needed to model LLM Agent API traffic.

The target design is:

```text
real repositories / issues / PRs / trajectories
+ controlled anonymization and traffic mixing
+ limited environment-context repair
= realistic anonymous Agent API logs with reproducible ground truth
```

## Candidate Sources

### B1: Open-SWE-Traces

Primary candidate.

Why:

- Already contains agent trajectories, not just static issues.
- Uses real-world PR/task sources.
- Contains `repo`, `language`, `license`, `trajectory_id`, `trajectory`, `model_patch`,
  `resolved`, and `metadata`.
- Covers OpenHands and SWE-agent style agent logs.
- Large enough for scale experiments.

Use:

- Convert each trajectory message list into `attack_view.jsonl`.
- Use `trajectory_id` or `instance_id + trajectory_id` as `session_id`.
- Use `repo` as organization/project-level ground truth.
- Use `language`, `license`, metadata, patch paths, and tool observations as profile truth.
- Add controlled timestamps, broker mixing, and optional redaction variants.

Caveat:

- The trajectories are generated/synthesized by models, even though the tasks and repos are
  real. We should describe it as "real-repo agent trajectory data", not as human enterprise logs.

### B2: SWE-bench Family

Secondary candidate.

Why:

- Real GitHub issues and corresponding PRs.
- Well-known and citable.
- Provides reproducible repo/task metadata and ground truth patches.

Use:

- Treat each issue as a workflow seed.
- Construct multi-turn Agent contexts from real issue text, repository files, patch hunks,
  test names, and optional evaluation logs.
- Use repo as organization/project label.
- Use issue id as session label.

Caveat:

- SWE-bench does not directly provide full Agent API trajectories. We would still synthesize
  the interaction sequence, but the content substrate is real.

Current local importer:

```bash
uv run python -m agent_privacy.data.swe_workflows \
  --use-hf \
  --hf-dataset princeton-nlp/SWE-bench_Lite \
  --hf-config default \
  --hf-split test \
  --output-dir artifacts/datasets/swe_repaired_sample \
  --limit 1000
```

Balanced SWE-bench Lite sample:

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

Natural repaired SWE-bench Lite sample without explicit repository repair context:

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

For local JSON/JSONL rows:

```bash
uv run python -m agent_privacy.data.swe_workflows \
  --input-path /path/to/swe_style_rows.jsonl \
  --output-dir artifacts/datasets/swe_repaired_sample \
  --limit 1000
```

The importer is schema-flexible for Hugging Face or local rows with common fields such as
`repo`, `repository`, `instance_id`, `problem_statement`, `patch`, `test_patch`,
`FAIL_TO_PASS`, `PASS_TO_PASS`, and `language`. It constructs repaired agent-like workflows
and must be reported as a repaired workflow dataset, not as raw agent trajectories.

Smoke status:

- `princeton-nlp/SWE-bench_Lite`, config `default`, split `test`, limit 5 imports and runs
  end-to-end.
- The first 100 SWE-bench Lite rows are highly unbalanced, with most rows from only two
  repositories. Do not use that sample for project/owner claims.
- The balanced SWE-bench Lite repaired sample scans the full 300-row test split and uses
  `--max-per-repo 5`, yielding 57 workflows, 12 repositories/owners, and 228 requests.
- The balanced sample is still repaired workflow validation, not raw provider evidence.
  Removing repaired `repository=` fields collapses hybrid project/owner recovery to zero.
- The natural repair policy removes explicit `repository=` and `[repair_context]` markers.
  In the current balanced sample, it produces a useful negative result: hybrid project/owner
  recovery is zero under the current low-cost attacks.

### B3: DevGPT

Supplementary candidate.

Why:

- Contains real shared ChatGPT developer conversations linked to GitHub issues, PRs,
  commits, discussions, code files, and Hacker News.
- Useful for real prompt/response style and natural user phrasing.

Use:

- Convert shared conversations to request sequences.
- Link to repo metadata when available.
- Use as a dialogue-linkability supplement rather than the main Agent-tool dataset.

Caveat:

- Public but human-authored; avoid publishing raw usernames in derived ground truth.
- It is mostly chat, not tool-using Agent traces.

### B4: GH Archive

Auxiliary candidate.

Why:

- Public GitHub event timeline with issues, PRs, comments, pushes, and other events.
- Useful for realistic traffic timing and repository activity mixing.

Use:

- Sample real timestamps and burst patterns.
- Reconstruct repo/user activity windows.
- Add realistic interleaving/noise to B1/B2/B3.

Caveat:

- Not an Agent dataset and not a prompt dataset.
- Better as a traffic model source than a content source.

### B5: Claw-SWE-Bench

Useful compact real-issue benchmark.

Why:

- Public Hugging Face dataset with `lite` and `full` subsets.
- Small enough for fast importer development: 80 lite rows and 350 full rows.
- Contains real repositories, problem statements, patches, test patches, timestamps,
  language labels, and pass/fail test names.
- MIT licensed.

Use:

- Treat each row as one repaired workflow.
- Build turns from problem statement, failing tests, patch hunks, and test patch.
- Use repo owner as org id, repo as project id, instance id as session id.

Caveat:

- It is not a trajectory dataset. It needs workflow repair.
- Good validation set, not enough scale for the main benchmark.

### B6: WildChat / CodeChat

Useful real conversation supplement.

Why:

- WildChat is a large public chatbot conversation corpus with timestamps, model names,
  conversation ids, multi-turn conversation lists, language labels, and redaction flags.
- CodeChat is a developer-code subset derived from WildChat, according to its paper.

Use:

- Use as real user conversation style data.
- Filter for software/code conversations.
- Evaluate session-level linkability and technical profile extraction.

Caveat:

- Not repository-grounded by default.
- Usually lacks tool calls, repo labels, and organization labels.
- Better as a chat-style supplement than as the main Agent workflow benchmark.

### B7: TerminalTraj / Terminal-Bench Family

Watchlist candidate.

Why:

- TerminalTraj reports 50,733 verified terminal trajectories grounded in real-world GitHub
  repositories and Dockerized environments.
- Terminal-Bench tasks are realistic terminal environments.

Use:

- If data is actually available, convert command/observation traces into Agent API logs.
- Useful for non-code-editor terminal workflows such as sysadmin, ML, data, and security.

Caveat:

- As of 2026-06-23, the TerminalTraj GitHub page says the author will release the data later;
  do not depend on it for the first implementation.

### B8: AgentLens-Bench

Watchlist candidate.

Why:

- Paper reports 1,815 OpenHands trajectories with process-quality annotations.
- Potentially valuable for process-level labels and trajectory-quality analysis.

Use:

- If the dataset/repo becomes accessible, use it as a small annotated trajectory benchmark.

Caveat:

- The paper points to `github.com/microsoft/code-agent-state-trajectories`, but that URL
  returned 404 during the 2026-06-23 check. Treat as unavailable until verified.

## Recommended Dataset Stack

Use three tiers:

```text
Dataset A: Controlled synthetic
  Purpose: sanity checks, ablations, known knobs.

Dataset B1: Open-SWE-Traces adapted
  Purpose: main real-data agent trajectory benchmark.

Dataset B2: SWE-bench repaired workflows
  Purpose: independent real-repo validation with less dependence on synthetic trajectories.

Dataset C: DevGPT dialogue supplement
  Purpose: real developer-prompt style validation.

Dataset D: Claw-SWE-Bench repaired workflows
  Purpose: small, fast, real issue/code/patch validation.

Dataset E: WildChat/CodeChat supplement
  Purpose: real multi-turn chat style, not repository workflow.
```

The paper should lead with B1/B2/D and keep A as a controlled experiment.

## Repair Policy

Allowed repairs:

- Add timestamps when missing.
- Add broker-level mixing and anonymized request ids.
- Add stable or unstable pseudonyms for repo/user/project labels in ground truth.
- Add local path variants derived from real repo names, such as `/workspace/<repo>/...`.
- Add tool schema wrappers if the source only provides action text.
- Add synthetic secrets only for testing secret filtering.
- Add profile labels derived from real metadata: language, license, repo owner, path names,
  package files, CI files, dependency files.

Avoid:

- Inventing organization-specific business domains that are not supported by the repository.
- Adding internal domains that look like real private infrastructure unless clearly synthetic.
- Adding usernames to attack view unless they exist in the public source or are a controlled
  repair variable.
- Treating generated model trajectories as human activity.

## Ground Truth Levels

Because real open-source data does not always map cleanly to enterprise identities, the
ground truth should be explicit:

- `session_id`: trajectory id, issue id, or PR id.
- `project_id`: repository name or package/module.
- `org_id`: GitHub owner or repository owner.
- `user_id`: only if safely available and ethically appropriate; otherwise use
  `unknown` and skip user-level scoring for that dataset.

For B1, org/project/session are reliable; user may be unavailable.
For B2, org/project/session are reliable; user may require GitHub metadata.
For B3, user exists but should be hashed and used carefully.

## First Implementation Milestone

Build an importer for Open-SWE-Traces:

```text
input: parquet rows from nvidia/Open-SWE-Traces
output:
  artifacts/datasets/open_swe_traces/attack_view.jsonl
  artifacts/datasets/open_swe_traces/ground_truth.jsonl
  artifacts/datasets/open_swe_traces/source_manifest.json
```

Minimal fields:

- attack view:
  - request id
  - timestamp
  - model/source split
  - trajectory messages
  - token count
  - tool schema/source scaffold

- ground truth:
  - repo owner as org id
  - repo as project id
  - trajectory id as workflow/session id
  - turn id
  - language/license/category/resolved as profile truth

Then run the existing attack/evaluation pipeline with user-level scoring disabled or marked
N/A for this dataset.
