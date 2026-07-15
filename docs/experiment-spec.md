# LLM Agent API Privacy MVP Experiment Spec

## Scope

The MVP tests one claim:

> In `D1 + A0 + cold-start`, explicit identity is hidden by an anonymous broker, but plaintext LLM Agent contexts remain linkable enough to reconstruct session, user, and organization-level workflows and recover organization profiles.

## Primary Threat Model

- `D1`: users call the model provider through an anonymous broker.
- `A0`: the provider is honest-but-curious and only performs passive offline log analysis.
- `Cold-start`: the attacker has no seed organization, user, project, domain, or historical request.
- The attacker does not modify model outputs, does not induce extra tool calls, and does not attack user machines.

## Attacker-Visible Fields

The attack may use:

- `request_id`
- `timestamp`
- `model`
- `messages`
- `tool_schemas`
- `token_count`
- `cache_bucket` when present
- defense-transformed content
- coarse `provider_metadata` fields such as API surface and brokered/stream flags

The attack must not use:

- `org_id`
- `user_id`
- `project_id`
- `workflow_id`
- `turn_id`
- `profile_truth`
- generator-only organization profile fields
- source dataset/provenance fields
- repair metadata or experiment labels in `attack_view.jsonl`

## Data Files

`attack_view.jsonl` contains one anonymous request per line.

`ground_truth.jsonl` contains labels and profile truth keyed by `request_id`.

Both files must be shuffled by timestamp and request id rather than grouped by organization.

## Provider-View Fidelity

The `attack_view.jsonl` schema is a provider-observable approximation, not a claim that every
commercial model API logs the exact same JSON shape. The intended invariant is:

> Every field in `attack_view.jsonl` must be observable or derivable by a model API provider
> during inference, after explicit identity fields are removed by the broker.

Current provider-visible fields are:

- plaintext message content, including agent tool observations when the API request includes
  prior tool results;
- model name/API surface;
- tool schema shape;
- request timestamp;
- token count or a provider-side length proxy;
- optional cache bucket or cache-side proxy;
- coarse provider metadata such as `stream` or `brokered`.

Dataset provenance, source row ids, repair fields, dataset names, and ground-truth labels must
remain outside `attack_view.jsonl`. For real-repository imports, timestamps are repaired when
the source lacks true provider-log timing; papers and tables must label those timestamps as
repair fields.

## Longitudinal Snapshots

The provider can observe traffic over time, so experiments should include cumulative snapshots
with different data volumes. A snapshot is a prefix of provider-visible requests sorted by
timestamp:

```bash
uv run python -m agent_privacy.data.time_snapshots \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000 \
  --output-dir artifacts/datasets/open_swe_traces_raw_1000_snapshots \
  --request-counts 1000 3000 6000 12000
```

Recommended reporting:

- `T1`: early traffic, low request volume;
- `T2`: medium traffic;
- `T3`: high traffic;
- optional `T4`: full observed window.

Each snapshot should be evaluated with the same attack and profile pipeline to show how
session/project/org reconstruction and profile completeness change as the provider accumulates
more logs.

## Tasks

### Session Reconstruction

Group requests from the same `workflow_id` and recover approximate turn order.

Primary signals:

- context carryover
- prefix or shingle overlap
- repeated tool outputs
- error/test/patch continuity
- short-range timestamp proximity
- token length growth

### User Linking

Group workflows from the same `user_id`.

For original Open-SWE and SWE-bench adapted datasets, reliable real `user_id` is unavailable
and user-level metrics must be reported as `N/A`. User-linking experiments should use either
the fully synthetic Dataset A or the trace-grounded Open-SWE User Overlay described in
`docs/open-swe-user-overlay-injection-plan.md`.

Primary signals:

- local workspace paths
- repeated personal task style
- recurring project selection
- user-specific shell habits
- active-hour patterns

### Organization Linking

Group users and workflows from the same `org_id`.

Primary signals:

- shared repositories
- internal domains
- service naming conventions
- CI/CD and deployment conventions
- business terminology
- shared trace/log formats

## Baselines

- `temporal`: bucket nearby requests.
- `rare`: link requests through rare extracted identifiers.
- `prefix`: link requests through text shingle overlap.
- `tool`: link requests through system prompt and tool schema fingerprints.
- `hybrid`: weighted graph using rare, prefix, tool, temporal, and length signals.

## Defenses

- `M0`: raw contexts.
- `M1`: secret filtering.
- `M2`: entity redaction.
- `M3`: context minimization.
- `M4`: broker mixing.
- `M6`: combined `M1 + M2 + M3 + M4`.

## Metrics

For session, user, and organization clustering:

- pairwise precision, recall, F1
- cluster purity
- split rate
- merge rate

For turn ordering:

- adjacent pair accuracy within predicted sessions

For profile reconstruction:

- field precision, recall, F1
- unsupported prediction count when evidence is missing

## MVP Success Criteria

The MVP supports the paper direction if:

- `hybrid` is clearly stronger than `temporal` and `tool` baselines.
- profile reconstruction recovers L2-L4 attributes without relying on secrets.
- `M1` has limited effect on organization profile recovery.
- `M2`, `M3`, or `M6` significantly reduce clustering or profile recovery.
