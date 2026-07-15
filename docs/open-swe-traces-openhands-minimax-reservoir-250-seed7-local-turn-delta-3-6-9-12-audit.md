# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_250_seed7_local_turn_delta_3_6_9_12`
- Requests: 1000
- Truth rows: 1000
- Provenance rows: 1000
- Workflows: 250
- Projects: 211
- Orgs: 194
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 1000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 1000), ('repository_field', 1)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 13579), ('assistant', 4325), ('system', 250), ('user', 250)]`
- Messages/request: `{'min': 3.0, 'p50': 17.0, 'p90': 27.0, 'max': 53.0, 'mean': 18.404}`
- Tokens/request: `{'min': 93.0, 'p50': 2769.0, 'p90': 6186.0, 'max': 12865.0, 'mean': 3276.425}`
- Turns/workflow: `{'min': 4.0, 'p50': 4.0, 'p90': 4.0, 'max': 4.0, 'mean': 4.0}`

## Top Orgs

- `vaskoz`: 28
- `google`: 28
- `Sage`: 16
- `getmoto`: 12
- `JoshuaKGoldberg`: 12
- `sindresorhus`: 12
- `zeromicro`: 12
- `nats-io`: 12
- `rust-lang`: 12
- `docker`: 8
- `decorators-squad`: 8
- `typescript-eslint`: 8
- `goccy`: 8
- `eslint`: 8
- `swc-project`: 8
- `pulumi`: 8
- `apiflask`: 8
- `import-js`: 8
- `vgteam`: 8
- `mpmath`: 8

## Top Projects

- `vaskoz/dailycodingproblem-go`: 28
- `Sage/carbon`: 16
- `getmoto/moto`: 12
- `JoshuaKGoldberg/create-typescript-app`: 12
- `zeromicro/go-zero`: 12
- `decorators-squad/eo-yaml`: 8
- `typescript-eslint/tslint-to-eslint-config`: 8
- `eslint/eslint`: 8
- `swc-project/swc`: 8
- `apiflask/apiflask`: 8
- `import-js/eslint-plugin-import`: 8
- `vgteam/sequenceTubeMap`: 8
- `mpmath/mpmath`: 8
- `pybamm-team/PyBaMM`: 8
- `Qiskit/qiskit-terra`: 8
- `KaTeX/KaTeX`: 8
- `stoplightio/spectral`: 8
- `stfc/PSyclone`: 8
- `pinojs/pino`: 8
- `TobikoData/sqlmesh`: 8
