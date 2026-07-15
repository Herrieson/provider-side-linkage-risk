# Open-SWE User Overlay Injection Plan

## Purpose

Open-SWE does not provide reliable real `user_id` ground truth. To evaluate user-level
linkage without pretending that Open-SWE contains real user identities, we define a
trace-grounded semi-synthetic dataset:

> **Dataset B: Open-SWE User Overlay**

Dataset B keeps the real Open-SWE agent traces, code context, tool observations, cumulative
conversation structure, and repository-derived complexity as the substrate. It overlays
synthetic users, organizations, projects, timestamps, and provider-visible user/environment
signals. This gives controlled `user_id` truth while preserving realistic agent-trace content.

The paper claim boundary is:

- Open-SWE original/adapted: real-repository trace evidence; user-level is `N/A`.
- Open-SWE User Overlay: trace-grounded semi-synthetic user-level mechanism evidence.
- Synthetic Dataset A: fully synthetic full-truth control.

Do not describe Dataset B as real user identities in Open-SWE.

## Scalability Path

Dataset B separates two attack roles:

- `hybrid` is the high-fidelity linkage baseline. It is useful for small/medium snapshots and
  upper-bound-style evidence, but it materializes rich request features and candidate edges; do
  not use it as the scalable provider method on full 12k cumulative overlays.
- `provider_lowcost` is the scalable provider method. Its large-run configuration uses explicit
  feature budgets and cache-bucket streaming:
  `--feature-window-chars 24000`, `--feature-max-shingles 1200`,
  `--feature-max-words 1500`, `--skip-ordering`, and `--stream-provider-lowcost`.

The recorded U3 12k streamed run preserves the same provider-lowcost clustering metrics as the
materialized budgeted run while lowering peak RSS from `3333.051 MB` to `1301.781 MB`. The
prototype implementation scans the JSONL once to enumerate cache buckets and once per cache
bucket to extract bounded features; a production provider could route requests into cache-bucket
queues in one pass.

## Provider-View Rule

The overlay must preserve the existing provider-view contract:

- `attack_view.jsonl` may contain only provider-observable or provider-derivable fields:
  `request_id`, `timestamp`, `model`, `messages`, `tool_schemas`, `token_count`,
  `cache_bucket`, and restricted `provider_metadata`.
- `attack_view.jsonl` must not contain `org_id`, `user_id`, `project_id`, `workflow_id`,
  `turn_id`, source dataset ids, provenance ids, overlay labels, or experiment labels.
- `ground_truth.jsonl` contains evaluation labels.
- `request_provenance.jsonl` contains source Open-SWE ids and overlay construction metadata.
- `profiles.json` contains overlay user/org/project truth and is evaluation-only.

Provider-visible overlay signals must be injected only through fields a model API provider
could see in inference logs: message/tool content, tool schema shape, timestamps, token/length
proxies, cache buckets, and model/API surface choices.

## Output Layout

Recommended output for the main U3 dataset:

```text
artifacts/datasets/open_swe_user_overlay_u3_mixed_1000/
  attack_view.jsonl
  ground_truth.jsonl
  request_provenance.jsonl
  profiles.json
  source_manifest.json

artifacts/datasets/open_swe_user_overlay_u3_mixed_1000_snapshots/
  first_1000_requests/
  first_4000_requests/
  first_8000_requests/
  first_12000_requests/
```

Recommended output for a hard setting:

```text
artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000/
```

## Label Overlay

The overlay uses synthetic labels as the evaluation target:

- `overlay_org_id`: synthetic organization label used as `org_id` in `ground_truth.jsonl`.
- `overlay_project_id`: synthetic project label used as `project_id`.
- `overlay_user_id`: synthetic user label used as `user_id`.
- `overlay_workflow_id`: synthetic workflow label used as `workflow_id`.

Source Open-SWE labels are retained only in `request_provenance.jsonl`:

- source workflow / trajectory id
- source GitHub owner-like label
- source repository/project label
- source request id
- source turn id

The generator should rewrite provider-visible repo/workspace artifacts to overlay aliases so
that the visible content and overlay truth are internally consistent. For example,
`/workspace/<source_owner>__<source_repo>` can become
`/workspace/<org_alias>__<project_alias>` in messages, while the source owner/repo remains
only in provenance.

## Cardinality Constraints

To avoid making user-level recovery a proxy for project or organization recovery:

- each overlay organization has at least 3 users;
- each overlay organization has at least 2 projects;
- each overlay project has workflows from at least 2 users;
- each overlay user touches at least 2 projects when enough source workflows are available;
- at least 30% of workflows should be in cross-user shared projects;
- at least 20% of users should work across multiple projects;
- source workflows are shuffled before assignment, then globally sorted by synthetic timestamp.

These constraints are more important than matching real Open-SWE owner frequencies.

## Overlay Difficulty Levels

| Level | Name | Injection | Purpose |
| --- | --- | --- | --- |
| U0 | no user overlay | Synthetic `user_id` labels and timestamps only; no user-specific visible signal. | Negative control; user recovery should be weak except via project/org confounds. |
| U1 | temporal only | User timezone, active-hour window, burstiness, and inter-turn delay. | Measures timing-only user linkage. |
| U2 | weak environment | U1 plus weak provider-visible environment artifacts with alias collisions. | Tests realistic low-strength user artifacts. |
| U3 | multi-signal user | U2 plus tool/schema preferences, cache bucket tendencies, command habits, and sparse shell/cache paths. | Main user-level mechanism setting. |
| U4 | hard shared org | U3 but users share org/project paths, services, tool schemas, and cache aliases more heavily. | Tests user recovery when org/project signals are deliberately confounded. |
| U5 | defended overlay | U3/U4 after path/workspace/context minimization transforms. | Defense evaluation setting. |

Main paper tables should use U3 and U4. U0-U2 are ablations or controls.

## Provider-Visible Signal Families

### 1. Time Behavior

Each synthetic user receives:

- timezone offset;
- weekday/weekend activity probability;
- active-hour center and spread;
- workflow start distribution;
- inter-turn delay distribution;
- burstiness parameter.

The generator must preserve turn order within each workflow. Across users and workflows, all
requests are globally mixed by timestamp.

### 2. Workspace and Runtime Artifacts

Injected artifacts must not reveal `overlay_user_id` directly. Use alias ids that are
plausible environment handles and allow collisions:

- home/cache aliases: `/home/dev-a13`, `/home/runner-k8`, `/Users/ci-42`;
- cache paths: `.cache/pip`, `.npm`, `.cargo`, `.m2`, `.pnpm-store`;
- temp/build paths: `/tmp/agent-build-a13`, `/var/tmp/tool-run-k8`;
- workspace aliases: `/workspace/<org_alias>__<project_alias>`.

Rules:

- user alias is stable within a time window but may rotate across snapshots;
- 10-20% of aliases collide across users in the same organization;
- 20-30% of requests do not contain user-specific path artifacts;
- project/org aliases are shared by users on the same overlay project/org.

### 3. Tool and Schema Preferences

Use provider-visible tool schema shape and tool observation text:

- schema parameter ordering variants;
- optional timeout/cwd parameter presence;
- shell tool names such as `bash`, `shell`, `terminal`;
- preferred command idioms: `rg`, `grep`, `pytest -q`, `npm test`, `pnpm test`,
  `go test ./...`, `mvn test`, `cargo test`;
- recurring tool error formatting or shell prompt style.

U4 should deliberately share more schema variants across users to reduce trivial user
fingerprints.

### 4. Cache and Length Proxies

Open-SWE has no real provider cache telemetry, so cache is modeled only as a controlled proxy:

- `cache_bucket` may be `low`, `medium`, or `high`;
- bucket assignment is based on org/project/user tendency plus noise;
- cache ablations must be reported as modeled cache proxy, not true Open-SWE telemetry.

### 5. Minimal Profile Hints

Do not rewrite the core task text heavily. Prefer lightweight provider-visible additions:

- tool observation headers;
- shell environment summaries;
- command outputs containing package manager/cache paths;
- CI/test command snippets;
- internal service aliases and domains for org/project profile truth.

The goal is to preserve real Open-SWE trace content while adding enough controlled user-level
truth to evaluate profile reconstruction.

## Attack-View Injection Surfaces

Allowed transformations:

- rewrite source workspace/repo paths in message text to overlay org/project aliases;
- append sparse synthetic tool observations containing runtime/cache/tool clues;
- modify `tool_schemas` shape using controlled schema variants;
- assign synthetic timestamps;
- assign modeled `cache_bucket`;
- adjust `model` among a small provider-visible model/API surface set if configured;
- recompute `token_count`.

Disallowed transformations:

- adding `user_id`, `org_id`, `project_id`, `workflow_id`, or `turn_id` to `attack_view`;
- adding source Open-SWE ids to `attack_view`;
- adding provider metadata keys outside the existing allowed set unless the provider-view audit
  policy is explicitly changed;
- adding secrets, real email addresses, real domains, real API keys, or real company names.

## Ground Truth and Profiles

`ground_truth.jsonl` should use overlay labels:

```json
{
  "request_id": "overlay_req_000001",
  "org_id": "overlay_org_003",
  "user_id": "overlay_user_003_007",
  "project_id": "overlay_proj_003_002",
  "workflow_id": "overlay_wf_003_007_0004",
  "turn_id": 6,
  "profile_truth": {
    "languages": ["python", "typescript"],
    "frameworks": ["pytest", "jest"],
    "package_managers": ["pip", "npm"],
    "build_tools": ["pytest", "npm test"],
    "ci_cd_systems": ["github_actions"],
    "service_names": ["[synthetic-service-alias]"],
    "internal_domains": ["[synthetic-domain-alias]"]
  }
}
```

`profiles.json` should include separate org, project, and user truth:

```json
{
  "users": {
    "overlay_user_003_007": {
      "org_id": "overlay_org_003",
      "timezone": "America/Los_Angeles",
      "active_hours": [9, 18],
      "runtime_aliases": ["dev-a13"],
      "tool_preferences": ["rg", "pytest -q", "pip"],
      "projects": ["overlay_proj_003_001", "overlay_proj_003_002"]
    }
  }
}
```

## Recommended Main Settings

### U3 Main

- source dataset: `artifacts/datasets/open_swe_traces_raw_1000`
- source workflows: up to 1,000
- overlay orgs: 40
- users per org: 3-6
- projects per org: 2-4
- time span: 21 days
- snapshots: 1,000 / 4,000 / 8,000 / 12,000 requests
- cross-user same-project rate: 0.45
- cross-project user rate: 0.25
- user alias collision rate: 0.15
- user signal dropout rate: 0.25
- cache noise rate: 0.30

### U4 Hard Shared

- same as U3, but:
- cross-user same-project rate: 0.70
- shared tool schema rate: 0.70
- shared environment alias prefix rate: 0.50
- user signal dropout rate: 0.40
- user alias collision rate: 0.30
- project/org signal strength remains high, user-specific signal is weaker.

## Evaluation Matrix

### Main Linkage Table

| Dataset | Overlay | Requests | Users | Projects | Orgs | Session F1 | User F1 | Project F1 | Org F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Open-SWE overlay | U1 temporal | 12k | ... | ... | ... | ... | ... | ... | ... |
| Open-SWE overlay | U2 weak env | 12k | ... | ... | ... | ... | ... | ... | ... |
| Open-SWE overlay | U3 multi-signal | 12k | ... | ... | ... | ... | ... | ... | ... |
| Open-SWE overlay | U4 hard shared | 12k | ... | ... | ... | ... | ... | ... | ... |

### User Signal Ablation Table

| Setting | Full | no_paths | no_time_length | no_tool_schema | no_shingles | no_cache |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| U3 User F1 | ... | ... | ... | ... | ... | ... |
| U4 User F1 | ... | ... | ... | ... | ... | ... |

### Provider Accumulation Table

| Snapshot | Requests | Users Seen | User F1 | Org F1 | Profile Micro F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| first 1k | 1,000 | ... | ... | ... | ... |
| first 4k | 4,000 | ... | ... | ... | ... |
| first 8k | 8,000 | ... | ... | ... | ... |
| first 12k | 12,000 | ... | ... | ... | ... |

## First Implementation Target

The first generator should implement only U0-U4 and snapshots. U5 can reuse existing defense
transforms after U3/U4 datasets exist.

Suggested command:

```bash
uv run python -m agent_privacy.data.open_swe_user_overlay \
  --config configs/open_swe_user_overlay_u3.json
```

Then evaluate:

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_user_overlay_u3_mixed_1000 \
  --output results/open_swe_user_overlay_u3_mixed_1000 \
  --levels session user project org \
  --methods temporal rare tool hybrid provider_lowcost \
  --defenses M0 \
  --ablations none \
  --feature-ablations none no_paths no_time_length no_tool_schema no_shingles no_cache \
  --open-swe-fast-features
```
