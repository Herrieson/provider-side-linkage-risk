# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_openhands_qwen35_raw_500`
- Requests: 6000
- Truth rows: 6000
- Provenance rows: 6000
- Workflows: 500
- Projects: 395
- Orgs: 371
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 6000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 6000)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 270116), ('assistant', 178978), ('system', 6000), ('user', 6000)]`
- Messages/request: `{'min': 3.0, 'p50': 73.0, 'p90': 145.0, 'max': 305.0, 'mean': 76.849}`
- Tokens/request: `{'min': 1626.0, 'p50': 9602.0, 'p90': 16244.0, 'max': 30905.0, 'mean': 9826.287166666667}`
- Turns/workflow: `{'min': 12.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 12.0}`

## Top Orgs

- `pandas-dev`: 144
- `vaskoz`: 108
- `google`: 72
- `swc-project`: 72
- `nats-io`: 60
- `googleapis`: 60
- `pyccel`: 60
- `FHIR`: 48
- `istio`: 36
- `argoproj`: 36
- `yannickcr`: 36
- `kubernetes-sigs`: 36
- `open-telemetry`: 36
- `getmoto`: 36
- `sindresorhus`: 36
- `eslint`: 36
- `keras-team`: 36
- `Kozea`: 36
- `ross-rotordynamics`: 36
- `platers`: 36

## Top Projects

- `pandas-dev/pandas`: 144
- `vaskoz/dailycodingproblem-go`: 108
- `swc-project/swc`: 72
- `pyccel/pyccel`: 60
- `FHIR/sushi`: 48
- `googleapis/java-storage`: 36
- `argoproj/argo`: 36
- `nats-io/nsc`: 36
- `yannickcr/eslint-plugin-react`: 36
- `getmoto/moto`: 36
- `Kozea/WeasyPrint`: 36
- `ross-rotordynamics/ross`: 36
- `platers/obsidian-linter`: 36
- `fxamacker/cbor`: 24
- `nats-io/nats-server`: 24
- `ResearchObject/ro-crate-py`: 24
- `meltano/sdk`: 24
- `GoogleChrome/lighthouse`: 24
- `ecmwf/earthkit-data`: 24
- `decorators-squad/eo-yaml`: 24
