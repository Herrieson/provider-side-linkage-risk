# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_100_seed7_hf`
- Requests: 1200
- Truth rows: 1200
- Provenance rows: 1200
- Workflows: 100
- Projects: 90
- Orgs: 87
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 1200)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 1200), ('repository_field', 10)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 34054), ('assistant', 9307), ('system', 1200), ('user', 1200)]`
- Messages/request: `{'min': 3.0, 'p50': 34.0, 'p90': 72.0, 'max': 236.0, 'mean': 38.134166666666665}`
- Tokens/request: `{'min': 1700.0, 'p50': 8131.0, 'p90': 14458.0, 'max': 30756.0, 'mean': 8621.525833333333}`
- Turns/workflow: `{'min': 12.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 12.0}`

## Top Orgs

- `knative-sandbox`: 36
- `eslint`: 24
- `CS-SI`: 24
- `sindresorhus`: 24
- `platers`: 24
- `FormidableLabs`: 24
- `pandas-dev`: 24
- `nats-io`: 24
- `relekang`: 24
- `vaskoz`: 24
- `ProjectEvergreen`: 24
- `source-academy`: 24
- `JsonMapper`: 12
- `asyncapi`: 12
- `getmoto`: 12
- `zulip`: 12
- `swc-project`: 12
- `ProcessMaker`: 12
- `AfterShip`: 12
- `mgechev`: 12

## Top Projects

- `knative-sandbox/eventing-kafka-broker`: 24
- `eslint/eslint`: 24
- `CS-SI/eodag`: 24
- `sindresorhus/got`: 24
- `platers/obsidian-linter`: 24
- `FormidableLabs/urql`: 24
- `pandas-dev/pandas`: 24
- `relekang/python-semantic-release`: 24
- `vaskoz/dailycodingproblem-go`: 24
- `source-academy/js-slang`: 24
- `JsonMapper/JsonMapper`: 12
- `asyncapi/parser-js`: 12
- `getmoto/moto`: 12
- `zulip/zulip-terminal`: 12
- `swc-project/swc`: 12
- `ProcessMaker/nayra`: 12
- `AfterShip/clickhouse-sql-parser`: 12
- `mgechev/revive`: 12
- `apiflask/apiflask`: 12
- `prettier/prettier-eslint`: 12
