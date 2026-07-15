# Dataset Audit

- Dataset: `artifacts/datasets/_archive/legacy_samples/open_swe_traces_raw_sample`
- Requests: 1200
- Truth rows: 1200
- Provenance rows: 1200
- Workflows: 100
- Projects: 96
- Orgs: 94
- Users with ground truth: 0

## Repair

- Repair modes: `[('none', 1200)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 1200)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('tool', 33173), ('assistant', 9439), ('system', 1200), ('user', 1200)]`
- Messages/request: `{'min': 3.0, 'p50': 32.0, 'p90': 74.0, 'max': 179.0, 'mean': 37.51}`
- Tokens/request: `{'min': 1703.0, 'p50': 7833.0, 'p90': 14312.0, 'max': 27756.0, 'mean': 8314.806666666667}`
- Turns/workflow: `{'min': 12.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 12.0}`

## Top Orgs

- `primefaces`: 24
- `kubernetes-sigs`: 24
- `JoshuaKGoldberg`: 24
- `amaranth-lang`: 24
- `pypa`: 24
- `getmoto`: 24
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

## Top Projects

- `primefaces/primefaces`: 24
- `JoshuaKGoldberg/create-typescript-app`: 24
- `amaranth-lang/amaranth`: 24
- `getmoto/moto`: 24
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
