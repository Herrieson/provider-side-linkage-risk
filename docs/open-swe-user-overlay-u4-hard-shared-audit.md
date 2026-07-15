# Dataset Audit

- Dataset: `artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000`
- Requests: 12000
- Truth rows: 12000
- Provenance rows: 12000
- Workflows: 1000
- Projects: 78
- Orgs: 30
- Users with ground truth: 182

## Repair

- Repair modes: `[('unknown', 12000)]`
- Repair fields: `[]`
- Leakage markers: `[('workspace_path', 12000), ('repository_field', 15)]`
- Non-provider attack-view fields: `[]`
- Non-provider provider_metadata fields: `[]`

## Shape

- Roles: `[('tool', 352534), ('assistant', 93290), ('system', 12000), ('user', 12000)]`
- Messages/request: `{'min': 3.0, 'p50': 34.0, 'p90': 77.0, 'max': 236.0, 'mean': 39.152}`
- Tokens/request: `{'min': 1664.0, 'p50': 7945.0, 'p90': 14381.0, 'max': 39922.0, 'mean': 8481.075583333333}`
- Turns/workflow: `{'min': 12.0, 'p50': 12.0, 'p90': 12.0, 'max': 12.0, 'mean': 12.0}`

## Top Orgs

- `overlay_org_009`: 408
- `overlay_org_004`: 408
- `overlay_org_002`: 408
- `overlay_org_006`: 408
- `overlay_org_001`: 408
- `overlay_org_003`: 408
- `overlay_org_005`: 408
- `overlay_org_008`: 408
- `overlay_org_010`: 408
- `overlay_org_007`: 408
- `overlay_org_025`: 396
- `overlay_org_015`: 396
- `overlay_org_018`: 396
- `overlay_org_017`: 396
- `overlay_org_024`: 396
- `overlay_org_020`: 396
- `overlay_org_011`: 396
- `overlay_org_030`: 396
- `overlay_org_029`: 396
- `overlay_org_022`: 396

## Top Projects

- `overlay_proj_006_001`: 264
- `overlay_proj_003_001`: 264
- `overlay_proj_028_001`: 264
- `overlay_proj_013_001`: 252
- `overlay_proj_021_002`: 228
- `overlay_proj_014_002`: 228
- `overlay_proj_024_001`: 216
- `overlay_proj_002_002`: 216
- `overlay_proj_026_001`: 216
- `overlay_proj_008_001`: 216
- `overlay_proj_015_001`: 204
- `overlay_proj_027_002`: 204
- `overlay_proj_025_002`: 204
- `overlay_proj_018_001`: 204
- `overlay_proj_025_001`: 192
- `overlay_proj_018_002`: 192
- `overlay_proj_015_002`: 192
- `overlay_proj_008_002`: 192
- `overlay_proj_024_002`: 180
- `overlay_proj_029_001`: 180
