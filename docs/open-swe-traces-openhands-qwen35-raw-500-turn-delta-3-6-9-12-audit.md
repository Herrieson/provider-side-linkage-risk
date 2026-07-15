# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_openhands_qwen35_raw_500_turn_delta_3_6_9_12`
- Requests: 2000
- Truth rows: 2000
- Provenance rows: 2000
- Workflows: 500
- Projects: 395
- Orgs: 371
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 2000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 2000)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 44080), ('assistant', 30394), ('system', 500), ('user', 500)]`
- Messages/request: `{'min': 15.0, 'p50': 36.0, 'p90': 50.0, 'max': 83.0, 'mean': 37.737}`
- Tokens/request: `{'min': 702.0, 'p50': 3373.0, 'p90': 6765.0, 'max': 12466.0, 'mean': 3893.9955}`
- Turns/workflow: `{'min': 4.0, 'p50': 4.0, 'p90': 4.0, 'max': 4.0, 'mean': 4.0}`

## Top Orgs

- `pandas-dev`: 48
- `vaskoz`: 36
- `google`: 24
- `swc-project`: 24
- `nats-io`: 20
- `googleapis`: 20
- `pyccel`: 20
- `FHIR`: 16
- `istio`: 12
- `argoproj`: 12
- `yannickcr`: 12
- `kubernetes-sigs`: 12
- `open-telemetry`: 12
- `getmoto`: 12
- `sindresorhus`: 12
- `eslint`: 12
- `keras-team`: 12
- `Kozea`: 12
- `ross-rotordynamics`: 12
- `platers`: 12

## Top Projects

- `pandas-dev/pandas`: 48
- `vaskoz/dailycodingproblem-go`: 36
- `swc-project/swc`: 24
- `pyccel/pyccel`: 20
- `FHIR/sushi`: 16
- `googleapis/java-storage`: 12
- `argoproj/argo`: 12
- `nats-io/nsc`: 12
- `yannickcr/eslint-plugin-react`: 12
- `getmoto/moto`: 12
- `Kozea/WeasyPrint`: 12
- `ross-rotordynamics/ross`: 12
- `platers/obsidian-linter`: 12
- `fxamacker/cbor`: 8
- `nats-io/nats-server`: 8
- `ResearchObject/ro-crate-py`: 8
- `meltano/sdk`: 8
- `GoogleChrome/lighthouse`: 8
- `ecmwf/earthkit-data`: 8
- `decorators-squad/eo-yaml`: 8
