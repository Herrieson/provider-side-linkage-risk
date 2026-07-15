# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_250_seed7_local`
- Requests: 3000
- Truth rows: 3000
- Provenance rows: 3000
- Workflows: 250
- Projects: 211
- Orgs: 194
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 3000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 3000), ('repository_field', 4)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 86036), ('assistant', 22483), ('system', 3000), ('user', 3000)]`
- Messages/request: `{'min': 3.0, 'p50': 34.0, 'p90': 75.0, 'max': 196.0, 'mean': 38.173}`
- Tokens/request: `{'min': 1658.0, 'p50': 7991.0, 'p90': 14417.0, 'max': 33455.0, 'mean': 8508.706}`
- Turns/workflow: `{'min': 12.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 12.0}`

## Top Orgs

- `vaskoz`: 84
- `google`: 84
- `Sage`: 48
- `getmoto`: 36
- `JoshuaKGoldberg`: 36
- `sindresorhus`: 36
- `zeromicro`: 36
- `nats-io`: 36
- `rust-lang`: 36
- `docker`: 24
- `decorators-squad`: 24
- `typescript-eslint`: 24
- `goccy`: 24
- `eslint`: 24
- `swc-project`: 24
- `pulumi`: 24
- `apiflask`: 24
- `import-js`: 24
- `vgteam`: 24
- `mpmath`: 24

## Top Projects

- `vaskoz/dailycodingproblem-go`: 84
- `Sage/carbon`: 48
- `getmoto/moto`: 36
- `JoshuaKGoldberg/create-typescript-app`: 36
- `zeromicro/go-zero`: 36
- `decorators-squad/eo-yaml`: 24
- `typescript-eslint/tslint-to-eslint-config`: 24
- `eslint/eslint`: 24
- `swc-project/swc`: 24
- `apiflask/apiflask`: 24
- `import-js/eslint-plugin-import`: 24
- `vgteam/sequenceTubeMap`: 24
- `mpmath/mpmath`: 24
- `pybamm-team/PyBaMM`: 24
- `Qiskit/qiskit-terra`: 24
- `KaTeX/KaTeX`: 24
- `stoplightio/spectral`: 24
- `stfc/PSyclone`: 24
- `pinojs/pino`: 24
- `TobikoData/sqlmesh`: 24
