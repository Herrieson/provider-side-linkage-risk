# Dataset Audit

- Dataset: `artifacts/datasets/tau_bench_historical_adapted`
- Requests: 7099
- Truth rows: 7099
- Provenance rows: 7099
- Workflows: 660
- Projects: 5
- Orgs: 2
- Users with ground truth: 87

## Repair

- Repair modes: `[('unknown', 7099)]`
- Repair fields: `[]`
- Leakage markers: `[]`
- Non-provider attack-view fields: `[]`
- Non-provider provider_metadata fields: `[]`

## Shape

- Roles: `[('assistant', 36114), ('user', 25383), ('tool', 17830), ('system', 14198)]`
- Messages/request: `{'min': 3.0, 'p50': 13.0, 'p90': 23.0, 'max': 25.0, 'mean': 13.174390759261868}`
- Tokens/request: `{'min': 1033.0, 'p50': 1283.0, 'p90': 1736.0, 'max': 2911.0, 'mean': 1353.0190167629244}`
- Turns/workflow: `{'min': 2.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 10.756060606060606}`

## Top Orgs

- `retail`: 5177
- `airline`: 1922

## Top Projects

- `retail:item_ids`: 4636
- `airline:flight_number`: 1839
- `retail:user_cost`: 530
- `airline:user_cost`: 83
- `retail:ordering`: 11
