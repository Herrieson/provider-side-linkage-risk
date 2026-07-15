# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_1000_requests`
- Requests: 1000
- Truth rows: 1000
- Provenance rows: 1000
- Workflows: 86
- Projects: 83
- Orgs: 82
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 1000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 1000)]`
- Non-provider attack-view fields: `[]`
- Non-provider provider_metadata fields: `[]`

## Shape

- Roles: `[('tool', 28008), ('assistant', 7919), ('system', 1000), ('user', 1000)]`
- Messages/request: `{'min': 3.0, 'p50': 34.0, 'p90': 74.0, 'max': 178.0, 'mean': 37.927}`
- Tokens/request: `{'min': 1703.0, 'p50': 7945.0, 'p90': 14525.0, 'max': 27756.0, 'mean': 8434.582}`
- Turns/workflow: `{'min': 2.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 11.627906976744185}`

## Top Orgs

- `primefaces`: 24
- `kubernetes-sigs`: 24
- `amaranth-lang`: 24
- `getmoto`: 22
- `altair-viz`: 12
- `python-attrs`: 12
- `open-telemetry`: 12
- `apache`: 12
- `ant-design`: 12
- `nats-io`: 12
- `alibaba`: 12
- `CuyZ`: 12
- `crossplane-contrib`: 12
- `open-feature`: 12
- `DesignLiquido`: 12
- `pravega`: 12
- `vaskoz`: 12
- `symfony`: 12
- `mapbox`: 12
- `crossbeam-rs`: 12

## Top Projects

- `primefaces/primefaces`: 24
- `amaranth-lang/amaranth`: 24
- `getmoto/moto`: 22
- `altair-viz/altair`: 12
- `python-attrs/attrs`: 12
- `open-telemetry/opentelemetry-go-contrib`: 12
- `apache/dubbo-go-hessian2`: 12
- `ant-design/ant-design-mobile`: 12
- `nats-io/nats.go`: 12
- `alibaba/fescar`: 12
- `CuyZ/Valinor`: 12
- `crossplane-contrib/provider-gitlab`: 12
- `open-feature/java-sdk`: 12
- `DesignLiquido/delegua`: 12
- `pravega/zookeeper-operator`: 12
- `vaskoz/dailycodingproblem-go`: 12
- `symfony/ux`: 12
- `mapbox/mapbox-sdk-py`: 12
- `crossbeam-rs/crossbeam`: 12
- `AfterShip/clickhouse-sql-parser`: 12
