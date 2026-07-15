# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_500_seed7_hf`
- Requests: 6000
- Truth rows: 6000
- Provenance rows: 6000
- Workflows: 500
- Projects: 377
- Orgs: 348
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 6000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 6000), ('repository_field', 11)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 169839), ('assistant', 46080), ('system', 6000), ('user', 6000)]`
- Messages/request: `{'min': 3.0, 'p50': 33.0, 'p90': 74.0, 'max': 201.0, 'mean': 37.9865}`
- Tokens/request: `{'min': 1668.0, 'p50': 7981.0, 'p90': 14293.0, 'max': 30143.0, 'mean': 8513.5505}`
- Turns/workflow: `{'min': 12.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 12.0}`

## Top Orgs

- `google`: 108
- `vaskoz`: 108
- `eslint`: 96
- `pallets`: 96
- `getmoto`: 84
- `alteryx`: 72
- `kubernetes`: 60
- `platers`: 60
- `auth0`: 48
- `knative-sandbox`: 48
- `vuejs`: 48
- `pandas-dev`: 48
- `pypa`: 48
- `modin-project`: 48
- `googleapis`: 48
- `asyncapi`: 36
- `amaranth-lang`: 36
- `decorators-squad`: 36
- `PennyLaneAI`: 36
- `kyeotic`: 36

## Top Projects

- `vaskoz/dailycodingproblem-go`: 108
- `getmoto/moto`: 84
- `eslint/eslint`: 60
- `google/go-safeweb`: 60
- `alteryx/evalml`: 60
- `pallets/click`: 60
- `platers/obsidian-linter`: 60
- `pandas-dev/pandas`: 48
- `modin-project/modin`: 48
- `amaranth-lang/amaranth`: 36
- `decorators-squad/eo-yaml`: 36
- `PennyLaneAI/pennylane`: 36
- `kyeotic/raviger`: 36
- `vuejs/eslint-plugin-vue`: 36
- `FHIR/sushi`: 36
- `meltano/sdk`: 36
- `aeye-lab/pymovements`: 36
- `primefaces/primefaces`: 36
- `pallets/werkzeug`: 36
- `eslint/doctrine`: 36
