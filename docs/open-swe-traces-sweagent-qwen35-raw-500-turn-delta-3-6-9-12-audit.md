# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_sweagent_qwen35_raw_500_turn_delta_3_6_9_12`
- Requests: 2000
- Truth rows: 2000
- Provenance rows: 2000
- Workflows: 500
- Projects: 404
- Orgs: 366
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 2000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 6), ('repository_field', 3)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 59857), ('assistant', 45305), ('system', 500), ('user', 500)]`
- Messages/request: `{'min': 19.0, 'p50': 52.0, 'p90': 74.0, 'max': 92.0, 'mean': 53.081}`
- Tokens/request: `{'min': 846.0, 'p50': 4616.0, 'p90': 8665.0, 'max': 37760.0, 'mean': 5261.951}`
- Turns/workflow: `{'min': 4.0, 'p50': 4.0, 'p90': 4.0, 'max': 4.0, 'mean': 4.0}`

## Top Orgs

- `vaskoz`: 40
- `yannickcr`: 24
- `getmoto`: 24
- `platers`: 20
- `apache`: 20
- `pallets`: 20
- `eslint`: 16
- `Qiskit`: 16
- `swc-project`: 16
- `googleapis`: 16
- `FHIR`: 16
- `webpack-contrib`: 16
- `elastic`: 16
- `google`: 16
- `nats-io`: 12
- `JoshuaKGoldberg`: 12
- `open-telemetry`: 12
- `PennyLaneAI`: 12
- `boardgameio`: 12
- `Unleash`: 12

## Top Projects

- `vaskoz/dailycodingproblem-go`: 40
- `yannickcr/eslint-plugin-react`: 24
- `getmoto/moto`: 24
- `platers/obsidian-linter`: 20
- `swc-project/swc`: 16
- `FHIR/sushi`: 16
- `elastic/synthetics`: 16
- `PennyLaneAI/pennylane`: 12
- `boardgameio/boardgame.io`: 12
- `eslint/eslint`: 12
- `Qiskit/qiskit-terra`: 12
- `kestra-io/kestra`: 12
- `lingui/js-lingui`: 12
- `pandas-dev/pandas`: 12
- `kayak/pypika`: 12
- `capricorn86/happy-dom`: 12
- `JsonMapper/JsonMapper`: 12
- `reduxjs/redux-toolkit`: 8
- `argoproj/argo`: 8
- `allegro/marathon-consul`: 8
