# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12`
- Requests: 4000
- Truth rows: 4000
- Provenance rows: 4000
- Workflows: 1000
- Projects: 639
- Orgs: 556
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 4000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 3999), ('repository_field', 2)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 54694), ('assistant', 17993), ('system', 1000), ('user', 1000)]`
- Messages/request: `{'min': 3.0, 'p50': 17.0, 'p90': 28.0, 'max': 64.0, 'mean': 18.67175}`
- Tokens/request: `{'min': 93.0, 'p50': 2704.0, 'p90': 6235.0, 'max': 20907.0, 'mean': 3265.76925}`
- Turns/workflow: `{'min': 4.0, 'p50': 4.0, 'p90': 4.0, 'max': 4.0, 'mean': 4.0}`

## Top Orgs

- `google`: 84
- `vaskoz`: 72
- `eslint`: 52
- `swc-project`: 52
- `getmoto`: 44
- `Qiskit`: 40
- `pandas-dev`: 36
- `kubernetes-sigs`: 32
- `JoshuaKGoldberg`: 32
- `pypa`: 32
- `sveltejs`: 32
- `nats-io`: 28
- `Sage`: 28
- `obsidian-tasks-group`: 28
- `typescript-eslint`: 28
- `rust-lang`: 28
- `getkin`: 24
- `sindresorhus`: 24
- `platers`: 24
- `elastic`: 24

## Top Projects

- `vaskoz/dailycodingproblem-go`: 72
- `swc-project/swc`: 52
- `getmoto/moto`: 44
- `eslint/eslint`: 44
- `pandas-dev/pandas`: 36
- `JoshuaKGoldberg/create-typescript-app`: 28
- `Sage/carbon`: 28
- `obsidian-tasks-group/obsidian-tasks`: 28
- `typescript-eslint/tslint-to-eslint-config`: 28
- `Qiskit/qiskit`: 24
- `getkin/kin-openapi`: 24
- `platers/obsidian-linter`: 24
- `python-attrs/attrs`: 20
- `primefaces/primefaces`: 20
- `amaranth-lang/amaranth`: 20
- `PennyLaneAI/pennylane`: 20
- `mpmath/mpmath`: 20
- `FHIR/sushi`: 20
- `knative/client`: 20
- `ProjectEvergreen/greenwood`: 16
