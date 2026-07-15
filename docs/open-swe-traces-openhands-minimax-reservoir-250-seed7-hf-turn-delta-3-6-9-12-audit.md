# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_250_seed7_hf_turn_delta_3_6_9_12`
- Requests: 1000
- Truth rows: 1000
- Provenance rows: 1000
- Workflows: 250
- Projects: 218
- Orgs: 197
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 1000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 1000)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 13342), ('assistant', 4475), ('system', 250), ('user', 250)]`
- Messages/request: `{'min': 4.0, 'p50': 17.0, 'p90': 28.0, 'max': 48.0, 'mean': 18.317}`
- Tokens/request: `{'min': 116.0, 'p50': 2624.0, 'p90': 6272.0, 'max': 12821.0, 'mean': 3215.634}`
- Turns/workflow: `{'min': 4.0, 'p50': 4.0, 'p90': 4.0, 'max': 4.0, 'mean': 4.0}`

## Top Orgs

- `getmoto`: 32
- `pandas-dev`: 20
- `kubernetes-sigs`: 16
- `sveltejs`: 16
- `auth0`: 12
- `google`: 12
- `vaskoz`: 12
- `Sage`: 12
- `pallets`: 12
- `knative`: 12
- `elastic`: 12
- `rust-lang`: 12
- `knative-sandbox`: 8
- `onflow`: 8
- `pingcap`: 8
- `sindresorhus`: 8
- `eslint`: 8
- `marpple`: 8
- `nats-io`: 8
- `pypa`: 8

## Top Projects

- `getmoto/moto`: 32
- `pandas-dev/pandas`: 20
- `vaskoz/dailycodingproblem-go`: 12
- `Sage/carbon`: 12
- `elastic/synthetics`: 12
- `knative-sandbox/eventing-kafka-broker`: 8
- `auth0/auth0-spa-js`: 8
- `onflow/flow-cli`: 8
- `marpple/FxTS`: 8
- `swc-project/swc`: 8
- `ManiacalLabs/BiblioPixel`: 8
- `sveltejs/prettier-plugin-svelte`: 8
- `sveltejs/kit`: 8
- `obsidian-tasks-group/obsidian-tasks`: 8
- `knative/client`: 8
- `reactiflux/discord-irc`: 8
- `SpikeInterface/spikeinterface`: 8
- `hibernate/hibernate-reactive`: 8
- `pallets/click`: 8
- `nightwatchjs/nightwatch`: 8
