# Dataset Card: SWE-bench Lite repaired/natural

## Source

SWE-bench Lite issue/patch/test artifacts converted into agent-like multi-turn provider-view requests.

## Intended Use

repair-policy sensitivity and reproducible workflow benchmark; repaired repository fields are deployment variants/upper bounds, not raw provider evidence.

## Provider-View Fields

attack_view excludes ground truth and provenance. Some timestamps/context are constructed to support evaluation and must be labeled as repaired/synthetic.

Allowed attack-view fields are `request_id`, `timestamp`, `model`, `messages`, `tool_schemas`, `token_count`, `cache_bucket`, and restricted `provider_metadata` keys.

## Ground Truth

project_id derives from repository, org_id from repository owner, workflow_id from instance id. user_id is unavailable.

## Audit Summary

- Dataset directory: `artifacts/datasets/swe_bench_lite_natural_balanced_sample`
- Requests: 228
- Truth rows: 228
- Workflows: 57
- Projects: 12
- Owner/org-like labels: 12
- Users with reliable labels: 0
- Non-provider attack-view fields: `[]`
- Non-provider provider_metadata fields: `[]`
- Repair modes: `[('unknown', 228)]`
- Repair fields: `[]`
- Leakage markers: `[]`

## License And Ethics

Follow upstream SWE-bench and underlying repository licenses; publish derived metrics and importer code unless source redistribution is separately cleared.

Raw prompt content can include code, logs, paths, usernames, repository names, and operational clues. Paper artifacts should prefer aggregate metrics, redacted snippets, and derived tables.

## Limitations

- Provider-view logs are approximations of what a model API provider can observe, not an exact commercial API schema.
- Timestamps may be repaired or synthetic when the upstream source lacks provider-log timing.
- Owner/org-like labels derived from repository owners must not be interpreted as enterprise organizations.
- User-level reconstruction is N/A when reliable user labels are unavailable.
