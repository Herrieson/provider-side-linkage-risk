# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_user_overlay_u3_mixed_1000`
- Requests: 12000
- Truth rows: 12000
- Provenance rows: 12000
- Workflows: 1000
- Projects: 112
- Orgs: 40
- Users with ground truth: 175

## Repair

- Repair modes: `[('unknown', 12000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 12000), ('repository_field', 15)]`
- Non-provider attack-view fields: `[]`
- Non-provider provider_metadata fields: `[]`

## Shape

- Roles: `[('tool', 362100), ('assistant', 93290), ('system', 12000), ('user', 12000)]`
- Messages/request: `{'min': 3.0, 'p50': 35.0, 'p90': 78.0, 'max': 238.0, 'mean': 39.94916666666666}`
- Tokens/request: `{'min': 1677.0, 'p50': 7949.0, 'p90': 14387.0, 'max': 39929.0, 'mean': 8486.277333333333}`
- Turns/workflow: `{'min': 12.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 12.0}`

## Top Orgs

- `overlay_org_011`: 300
- `overlay_org_009`: 300
- `overlay_org_006`: 300
- `overlay_org_022`: 300
- `overlay_org_023`: 300
- `overlay_org_039`: 300
- `overlay_org_030`: 300
- `overlay_org_027`: 300
- `overlay_org_026`: 300
- `overlay_org_007`: 300
- `overlay_org_031`: 300
- `overlay_org_025`: 300
- `overlay_org_014`: 300
- `overlay_org_040`: 300
- `overlay_org_013`: 300
- `overlay_org_002`: 300
- `overlay_org_029`: 300
- `overlay_org_001`: 300
- `overlay_org_035`: 300
- `overlay_org_016`: 300

## Top Projects

- `overlay_proj_015_001`: 204
- `overlay_proj_003_002`: 192
- `overlay_proj_014_002`: 192
- `overlay_proj_012_002`: 180
- `overlay_proj_039_002`: 168
- `overlay_proj_037_001`: 168
- `overlay_proj_018_001`: 168
- `overlay_proj_032_001`: 168
- `overlay_proj_040_001`: 168
- `overlay_proj_038_002`: 168
- `overlay_proj_025_001`: 168
- `overlay_proj_023_002`: 156
- `overlay_proj_026_001`: 156
- `overlay_proj_016_002`: 156
- `overlay_proj_005_001`: 156
- `overlay_proj_019_002`: 156
- `overlay_proj_007_001`: 156
- `overlay_proj_028_002`: 156
- `overlay_proj_020_002`: 156
- `overlay_proj_008_001`: 156
