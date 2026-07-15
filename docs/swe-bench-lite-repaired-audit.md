# Dataset Audit

- Dataset: `artifacts/datasets/_archive/legacy_samples/swe_bench_lite_repaired_sample`
- Requests: 400
- Truth rows: 400
- Provenance rows: 400
- Workflows: 100
- Projects: 2
- Orgs: 2
- Users with ground truth: 0

## Repair

- Repair modes: `[('unknown', 400)]`
- Repair fields: `[]`
- Leakage markers: `[('repository_field', 400), ('repair_context_marker', 400)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('assistant', 600), ('tool', 600), ('system', 400), ('user', 400)]`
- Messages/request: `{'min': 2.0, 'p50': 6.0, 'p90': 8.0, 'max': 8.0, 'mean': 5.0}`
- Tokens/request: `{'min': 52.0, 'p50': 348.0, 'p90': 774.0, 'max': 2834.0, 'mean': 438.615}`
- Turns/workflow: `{'min': 4.0, 'p50': 4.0, 'p90': 4.0, 'max': 4.0, 'mean': 4.0}`

## Top Orgs

- `django`: 376
- `astropy`: 24

## Top Projects

- `django/django`: 376
- `astropy/astropy`: 24
