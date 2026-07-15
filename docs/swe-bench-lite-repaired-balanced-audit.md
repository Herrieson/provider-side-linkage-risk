# Dataset Audit

- Dataset: `artifacts/datasets/swe_bench_lite_repaired_balanced_sample`
- Requests: 228
- Truth rows: 228
- Provenance rows: 228
- Workflows: 57
- Projects: 12
- Orgs: 12
- Users with ground truth: 0

## Repair

- Repair modes: `[('unknown', 228)]`
- Repair fields: `[]`
- Leakage markers: `[('repository_field', 228), ('repair_context_marker', 228)]`
- Non-provider attack-view fields: `[]`

## Shape

- Roles: `[('assistant', 342), ('tool', 342), ('system', 228), ('user', 228)]`
- Messages/request: `{'min': 2.0, 'p50': 6.0, 'p90': 8.0, 'max': 8.0, 'mean': 5.0}`
- Tokens/request: `{'min': 52.0, 'p50': 339.0, 'p90': 817.0, 'max': 2373.0, 'mean': 443.2675438596491}`
- Turns/workflow: `{'min': 4.0, 'p50': 4.0, 'p90': 4.0, 'max': 4.0, 'mean': 4.0}`

## Top Orgs

- `astropy`: 20
- `django`: 20
- `matplotlib`: 20
- `psf`: 20
- `pydata`: 20
- `pylint-dev`: 20
- `pytest-dev`: 20
- `scikit-learn`: 20
- `sphinx-doc`: 20
- `sympy`: 20
- `mwaskom`: 16
- `pallets`: 12

## Top Projects

- `astropy/astropy`: 20
- `django/django`: 20
- `matplotlib/matplotlib`: 20
- `psf/requests`: 20
- `pydata/xarray`: 20
- `pylint-dev/pylint`: 20
- `pytest-dev/pytest`: 20
- `scikit-learn/scikit-learn`: 20
- `sphinx-doc/sphinx`: 20
- `sympy/sympy`: 20
- `mwaskom/seaborn`: 16
- `pallets/flask`: 12
