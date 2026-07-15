# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_100_seed7_hf_turn_delta_3_6_9_12`
- Requests: 400
- Truth rows: 400
- Provenance rows: 400
- Workflows: 100
- Projects: 90
- Orgs: 87
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 400)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 400), ('repository_field', 3)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 5367), ('assistant', 1787), ('system', 100), ('user', 100)]`
- Messages/request: `{'min': 8.0, 'p50': 17.0, 'p90': 27.0, 'max': 64.0, 'mean': 18.385}`
- Tokens/request: `{'min': 537.0, 'p50': 2718.0, 'p90': 6460.0, 'max': 13877.0, 'mean': 3308.73}`
- Turns/workflow: `{'min': 4.0, 'p50': 4.0, 'p90': 4.0, 'max': 4.0, 'mean': 4.0}`

## Top Orgs

- `knative-sandbox`: 12
- `eslint`: 8
- `CS-SI`: 8
- `sindresorhus`: 8
- `platers`: 8
- `FormidableLabs`: 8
- `pandas-dev`: 8
- `nats-io`: 8
- `relekang`: 8
- `vaskoz`: 8
- `ProjectEvergreen`: 8
- `source-academy`: 8
- `JsonMapper`: 4
- `asyncapi`: 4
- `getmoto`: 4
- `zulip`: 4
- `swc-project`: 4
- `ProcessMaker`: 4
- `AfterShip`: 4
- `mgechev`: 4

## Top Projects

- `knative-sandbox/eventing-kafka-broker`: 8
- `eslint/eslint`: 8
- `CS-SI/eodag`: 8
- `sindresorhus/got`: 8
- `platers/obsidian-linter`: 8
- `FormidableLabs/urql`: 8
- `pandas-dev/pandas`: 8
- `relekang/python-semantic-release`: 8
- `vaskoz/dailycodingproblem-go`: 8
- `source-academy/js-slang`: 8
- `JsonMapper/JsonMapper`: 4
- `asyncapi/parser-js`: 4
- `getmoto/moto`: 4
- `zulip/zulip-terminal`: 4
- `swc-project/swc`: 4
- `ProcessMaker/nayra`: 4
- `AfterShip/clickhouse-sql-parser`: 4
- `mgechev/revive`: 4
- `apiflask/apiflask`: 4
- `prettier/prettier-eslint`: 4
