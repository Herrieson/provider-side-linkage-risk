# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_250_seed7_hf`
- Requests: 3000
- Truth rows: 3000
- Provenance rows: 3000
- Workflows: 250
- Projects: 218
- Orgs: 197
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 3000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 3000)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 84613), ('assistant', 23417), ('system', 3000), ('user', 3000)]`
- Messages/request: `{'min': 3.0, 'p50': 33.0, 'p90': 74.0, 'max': 179.0, 'mean': 38.01}`
- Tokens/request: `{'min': 1664.0, 'p50': 8011.0, 'p90': 13952.0, 'max': 25849.0, 'mean': 8398.8}`
- Turns/workflow: `{'min': 12.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 12.0}`

## Top Orgs

- `getmoto`: 96
- `pandas-dev`: 60
- `kubernetes-sigs`: 48
- `sveltejs`: 48
- `auth0`: 36
- `google`: 36
- `vaskoz`: 36
- `Sage`: 36
- `pallets`: 36
- `knative`: 36
- `elastic`: 36
- `rust-lang`: 36
- `knative-sandbox`: 24
- `onflow`: 24
- `pingcap`: 24
- `sindresorhus`: 24
- `eslint`: 24
- `marpple`: 24
- `nats-io`: 24
- `pypa`: 24

## Top Projects

- `getmoto/moto`: 96
- `pandas-dev/pandas`: 60
- `vaskoz/dailycodingproblem-go`: 36
- `Sage/carbon`: 36
- `elastic/synthetics`: 36
- `knative-sandbox/eventing-kafka-broker`: 24
- `auth0/auth0-spa-js`: 24
- `onflow/flow-cli`: 24
- `marpple/FxTS`: 24
- `swc-project/swc`: 24
- `ManiacalLabs/BiblioPixel`: 24
- `sveltejs/prettier-plugin-svelte`: 24
- `sveltejs/kit`: 24
- `obsidian-tasks-group/obsidian-tasks`: 24
- `knative/client`: 24
- `reactiflux/discord-irc`: 24
- `SpikeInterface/spikeinterface`: 24
- `hibernate/hibernate-reactive`: 24
- `pallets/click`: 24
- `nightwatchjs/nightwatch`: 24
