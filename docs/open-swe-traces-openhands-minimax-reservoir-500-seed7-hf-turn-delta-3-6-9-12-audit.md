# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_500_seed7_hf_turn_delta_3_6_9_12`
- Requests: 2000
- Truth rows: 2000
- Provenance rows: 2000
- Workflows: 500
- Projects: 377
- Orgs: 348
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 2000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 2000), ('repository_field', 4)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 26757), ('assistant', 8873), ('system', 500), ('user', 500)]`
- Messages/request: `{'min': 7.0, 'p50': 17.0, 'p90': 28.0, 'max': 54.0, 'mean': 18.315}`
- Tokens/request: `{'min': 296.0, 'p50': 2680.0, 'p90': 6172.0, 'max': 15507.0, 'mean': 3272.662}`
- Turns/workflow: `{'min': 4.0, 'p50': 4.0, 'p90': 4.0, 'max': 4.0, 'mean': 4.0}`

## Top Orgs

- `google`: 36
- `vaskoz`: 36
- `eslint`: 32
- `pallets`: 32
- `getmoto`: 28
- `alteryx`: 24
- `kubernetes`: 20
- `platers`: 20
- `auth0`: 16
- `knative-sandbox`: 16
- `vuejs`: 16
- `pandas-dev`: 16
- `pypa`: 16
- `modin-project`: 16
- `googleapis`: 16
- `asyncapi`: 12
- `amaranth-lang`: 12
- `decorators-squad`: 12
- `PennyLaneAI`: 12
- `kyeotic`: 12

## Top Projects

- `vaskoz/dailycodingproblem-go`: 36
- `getmoto/moto`: 28
- `eslint/eslint`: 20
- `google/go-safeweb`: 20
- `alteryx/evalml`: 20
- `pallets/click`: 20
- `platers/obsidian-linter`: 20
- `pandas-dev/pandas`: 16
- `modin-project/modin`: 16
- `amaranth-lang/amaranth`: 12
- `decorators-squad/eo-yaml`: 12
- `PennyLaneAI/pennylane`: 12
- `kyeotic/raviger`: 12
- `vuejs/eslint-plugin-vue`: 12
- `FHIR/sushi`: 12
- `meltano/sdk`: 12
- `aeye-lab/pymovements`: 12
- `primefaces/primefaces`: 12
- `pallets/werkzeug`: 12
- `eslint/doctrine`: 12
