# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_sweagent_qwen35_raw_500`
- Requests: 6000
- Truth rows: 6000
- Provenance rows: 6000
- Workflows: 500
- Projects: 404
- Orgs: 366
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 6000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 53), ('repository_field', 11)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 364375), ('assistant', 268797), ('system', 6000), ('user', 6000)]`
- Messages/request: `{'min': 3.0, 'p50': 101.0, 'p90': 207.0, 'max': 338.0, 'mean': 107.52866666666667}`
- Tokens/request: `{'min': 237.0, 'p50': 11297.0, 'p90': 21533.0, 'max': 60258.0, 'mean': 11936.4165}`
- Turns/workflow: `{'min': 12.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 12.0}`

## Top Orgs

- `vaskoz`: 120
- `yannickcr`: 72
- `getmoto`: 72
- `platers`: 60
- `apache`: 60
- `pallets`: 60
- `eslint`: 48
- `Qiskit`: 48
- `swc-project`: 48
- `googleapis`: 48
- `FHIR`: 48
- `webpack-contrib`: 48
- `elastic`: 48
- `google`: 48
- `nats-io`: 36
- `JoshuaKGoldberg`: 36
- `open-telemetry`: 36
- `PennyLaneAI`: 36
- `boardgameio`: 36
- `Unleash`: 36

## Top Projects

- `vaskoz/dailycodingproblem-go`: 120
- `yannickcr/eslint-plugin-react`: 72
- `getmoto/moto`: 72
- `platers/obsidian-linter`: 60
- `swc-project/swc`: 48
- `FHIR/sushi`: 48
- `elastic/synthetics`: 48
- `PennyLaneAI/pennylane`: 36
- `boardgameio/boardgame.io`: 36
- `eslint/eslint`: 36
- `Qiskit/qiskit-terra`: 36
- `kestra-io/kestra`: 36
- `lingui/js-lingui`: 36
- `pandas-dev/pandas`: 36
- `kayak/pypika`: 36
- `capricorn86/happy-dom`: 36
- `JsonMapper/JsonMapper`: 36
- `reduxjs/redux-toolkit`: 24
- `argoproj/argo`: 24
- `solid/community-server`: 24
