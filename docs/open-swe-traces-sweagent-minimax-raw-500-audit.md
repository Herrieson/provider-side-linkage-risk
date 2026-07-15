# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_sweagent_minimax_raw_500`
- Requests: 6000
- Truth rows: 6000
- Provenance rows: 6000
- Workflows: 500
- Projects: 374
- Orgs: 347
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 6000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 66), ('repository_field', 11)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 213359), ('assistant', 56187), ('system', 6000), ('user', 6000)]`
- Messages/request: `{'min': 3.0, 'p50': 40.0, 'p90': 94.0, 'max': 238.0, 'mean': 46.92433333333334}`
- Tokens/request: `{'min': 234.0, 'p50': 7557.0, 'p90': 16120.0, 'max': 45344.0, 'mean': 8540.092}`
- Turns/workflow: `{'min': 12.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 12.0}`

## Top Orgs

- `getmoto`: 120
- `platers`: 108
- `eslint`: 84
- `Qiskit`: 72
- `pandas-dev`: 72
- `googleapis`: 72
- `vuejs`: 72
- `helm`: 60
- `swc-project`: 60
- `JoshuaKGoldberg`: 60
- `FHIR`: 60
- `microsoft`: 48
- `PyCQA`: 48
- `mpmath`: 48
- `pybamm-team`: 48
- `vaskoz`: 36
- `rust-lang`: 36
- `sindresorhus`: 36
- `yannickcr`: 36
- `ProjectEvergreen`: 36

## Top Projects

- `getmoto/moto`: 120
- `platers/obsidian-linter`: 108
- `eslint/eslint`: 84
- `pandas-dev/pandas`: 72
- `helm/helm`: 60
- `swc-project/swc`: 60
- `JoshuaKGoldberg/create-typescript-app`: 60
- `FHIR/sushi`: 60
- `vuejs/eslint-plugin-vue`: 48
- `mpmath/mpmath`: 48
- `pybamm-team/PyBaMM`: 48
- `vaskoz/dailycodingproblem-go`: 36
- `rust-lang/rustfmt`: 36
- `Qiskit/qiskit`: 36
- `yannickcr/eslint-plugin-react`: 36
- `stoplightio/spectral`: 36
- `jlongster/prettier`: 36
- `brazilian-utils/brutils-python`: 36
- `solid/community-server`: 36
- `googleapis/python-api-core`: 36
