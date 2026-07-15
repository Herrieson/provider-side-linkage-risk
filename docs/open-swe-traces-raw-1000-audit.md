# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_raw_1000`
- Requests: 12000
- Truth rows: 12000
- Provenance rows: 12000
- Workflows: 1000
- Projects: 639
- Orgs: 556
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 12000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 12000), ('repository_field', 15)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 347197), ('assistant', 93290), ('system', 12000), ('user', 12000)]`
- Messages/request: `{'min': 3.0, 'p50': 34.0, 'p90': 76.0, 'max': 236.0, 'mean': 38.70725}`
- Tokens/request: `{'min': 1658.0, 'p50': 7945.0, 'p90': 14381.0, 'max': 39922.0, 'mean': 8478.203666666666}`
- Turns/workflow: `{'min': 12.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 12.0}`

## Top Orgs

- `google`: 252
- `vaskoz`: 216
- `eslint`: 156
- `swc-project`: 156
- `getmoto`: 132
- `Qiskit`: 120
- `pandas-dev`: 108
- `kubernetes-sigs`: 96
- `JoshuaKGoldberg`: 96
- `pypa`: 96
- `sveltejs`: 96
- `nats-io`: 84
- `Sage`: 84
- `obsidian-tasks-group`: 84
- `typescript-eslint`: 84
- `rust-lang`: 84
- `getkin`: 72
- `sindresorhus`: 72
- `platers`: 72
- `elastic`: 72

## Top Projects

- `vaskoz/dailycodingproblem-go`: 216
- `swc-project/swc`: 156
- `getmoto/moto`: 132
- `eslint/eslint`: 132
- `pandas-dev/pandas`: 108
- `JoshuaKGoldberg/create-typescript-app`: 84
- `Sage/carbon`: 84
- `obsidian-tasks-group/obsidian-tasks`: 84
- `typescript-eslint/tslint-to-eslint-config`: 84
- `Qiskit/qiskit`: 72
- `getkin/kin-openapi`: 72
- `platers/obsidian-linter`: 72
- `python-attrs/attrs`: 60
- `primefaces/primefaces`: 60
- `amaranth-lang/amaranth`: 60
- `PennyLaneAI/pennylane`: 60
- `mpmath/mpmath`: 60
- `FHIR/sushi`: 60
- `knative/client`: 60
- `ProjectEvergreen/greenwood`: 48
