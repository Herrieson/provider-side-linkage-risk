# Dataset Audit

- Dataset: `artifacts/datasets/tau_bench_smoke_adapted`
- Requests: 6
- Truth rows: 6
- Provenance rows: 6
- Workflows: 3
- Projects: 3
- Orgs: 2
- Users with ground truth: 3

## Repair

- Repair modes: `[('unknown', 6)]`
- Repair fields: `[]`
- Leakage markers: `[]`
- Non-provider attack-view fields: `[]`
- Non-provider provider_metadata fields: `[]`

## Shape

- Roles: `[('system', 6), ('user', 6), ('tool', 4), ('assistant', 3)]`
- Messages/request: `{'min': 2.0, 'p50': 2.0, 'p90': 4.0, 'max': 5.0, 'mean': 3.1666666666666665}`
- Tokens/request: `{'min': 25.0, 'p50': 30.0, 'p90': 35.0, 'max': 39.0, 'mean': 31.833333333333332}`
- Turns/workflow: `{'min': 2.0, 'p50': 2.0, 'p90': 2.0, 'max': 2.0, 'mean': 2.0}`

## Top Orgs

- `retail`: 4
- `airline`: 2

## Top Projects

- `retail:customer_alpha001`: 2
- `retail:customer_beta002`: 2
- `airline:account_gamma003`: 2
