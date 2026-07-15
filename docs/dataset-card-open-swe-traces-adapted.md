# Dataset Card: Open-SWE-Traces adapted

## Source

Open-SWE-Traces real-repository agent trajectories adapted to provider-view JSONL.

## Intended Use

workflow, project/repo, and GitHub owner-like linkage; not enterprise identity or real user-level identity.

## Provider-View Fields

attack_view contains plaintext messages/tool observations, model/API metadata, tool schema shape, token count, timestamp, cache bucket when available, and provider_metadata. Truth/provenance/repair metadata are separate.

Allowed attack-view fields are `request_id`, `timestamp`, `model`, `messages`, `tool_schemas`, `token_count`, `cache_bucket`, and restricted `provider_metadata` keys.

## Ground Truth

workflow_id is trajectory_id, project_id is repository, org_id is GitHub owner. user_id is unavailable and should be reported as N/A.

## Audit Summary

- Dataset directory: `artifacts/datasets/open_swe_traces_raw_1000`
- Requests: 12000
- Truth rows: 12000
- Workflows: 1000
- Projects: 639
- Owner/org-like labels: 556
- Users with reliable labels: 0
- Non-provider attack-view fields: `[]`
- Non-provider provider_metadata fields: `[]`
- Repair modes: `[('none', 12000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 12000), ('repository_field', 15)]`

## License And Ethics

Follow the upstream Open-SWE-Traces license and redistribution terms; this project should publish derived metrics/cards rather than raw prompt text unless license review permits redistribution.

Raw prompt content can include code, logs, paths, usernames, repository names, and operational clues. Paper artifacts should prefer aggregate metrics, redacted snippets, and derived tables.

## Limitations

- Provider-view logs are approximations of what a model API provider can observe, not an exact commercial API schema.
- Timestamps may be repaired or synthetic when the upstream source lacks provider-log timing.
- Owner/org-like labels derived from repository owners must not be interpreted as enterprise organizations.
- User-level reconstruction is N/A when reliable user labels are unavailable.
