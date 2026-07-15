# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_sweagent_minimax_raw_500_turn_delta_3_6_9_12`
- Requests: 2000
- Truth rows: 2000
- Provenance rows: 2000
- Workflows: 500
- Projects: 374
- Orgs: 347
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 2000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 10), ('repository_field', 2)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 34342), ('assistant', 10222), ('system', 500), ('user', 500)]`
- Messages/request: `{'min': 4.0, 'p50': 21.0, 'p90': 37.0, 'max': 65.0, 'mean': 22.782}`
- Tokens/request: `{'min': 152.0, 'p50': 2660.0, 'p90': 6812.0, 'max': 31825.0, 'mean': 3460.173}`
- Turns/workflow: `{'min': 4.0, 'p50': 4.0, 'p90': 4.0, 'max': 4.0, 'mean': 4.0}`

## Top Orgs

- `getmoto`: 40
- `platers`: 36
- `eslint`: 28
- `Qiskit`: 24
- `pandas-dev`: 24
- `googleapis`: 24
- `vuejs`: 24
- `helm`: 20
- `swc-project`: 20
- `JoshuaKGoldberg`: 20
- `FHIR`: 20
- `microsoft`: 16
- `PyCQA`: 16
- `mpmath`: 16
- `pybamm-team`: 16
- `vaskoz`: 12
- `rust-lang`: 12
- `sindresorhus`: 12
- `yannickcr`: 12
- `ProjectEvergreen`: 12

## Top Projects

- `getmoto/moto`: 40
- `platers/obsidian-linter`: 36
- `eslint/eslint`: 28
- `pandas-dev/pandas`: 24
- `helm/helm`: 20
- `swc-project/swc`: 20
- `JoshuaKGoldberg/create-typescript-app`: 20
- `FHIR/sushi`: 20
- `vuejs/eslint-plugin-vue`: 16
- `mpmath/mpmath`: 16
- `pybamm-team/PyBaMM`: 16
- `vaskoz/dailycodingproblem-go`: 12
- `rust-lang/rustfmt`: 12
- `Qiskit/qiskit`: 12
- `yannickcr/eslint-plugin-react`: 12
- `stoplightio/spectral`: 12
- `jlongster/prettier`: 12
- `brazilian-utils/brutils-python`: 12
- `solid/community-server`: 12
- `googleapis/python-api-core`: 12
