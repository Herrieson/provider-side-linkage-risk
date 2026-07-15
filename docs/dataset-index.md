# Dataset Index

Datasets use the same core contract:

- `attack_view.jsonl`: provider-visible approximation only.
- `ground_truth.jsonl`: labels for evaluation.
- `request_provenance.jsonl`: source/provenance/repair metadata, when available.
- `source_manifest.json` or `dataset_config.json`: source and generation metadata.

The current provider-view audit summary is in `docs/tables/provider_view_audit_summary.md`.

Dataset payloads are not normal Git files. `artifacts/dataset-manifest.json` records their upstream
source, local path, measured local size, redistribution class, config, and dataset card. A clean
clone includes only `examples/tool_agent_smoke/`; paper-facing payloads appear under
`artifacts/datasets/` after regeneration or extraction of an approved release asset. The complete
local workspace keeps historical samples under `artifacts/datasets/_archive/` without deletion.

## Primary Datasets

| Dataset | Path | Role | Ground Truth | Notes |
| --- | --- | --- | --- | --- |
| Open-SWE raw 1,000 workflows | `artifacts/datasets/open_swe_traces_raw_1000` | Main real-repo agent trajectory evidence. | `workflow_id`, `project_id`, GitHub owner-like `org_id`; no reliable `user_id`. | `repair_mode=none`; timestamps are repaired/synthetic provider-log approximations. |
| Open-SWE sample100 | `artifacts/datasets/open_swe_traces_raw_1000_sample100` | Fast provider-lowcost, controls, threshold sweeps, mitigation probes. | Same as Open-SWE raw. | Used with turns `3 6 9 12` for fixed-budget experiments. |
| Open-SWE turn-delta sample100 | `artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12_sample100` | Negative/control view without cumulative context. | Same as Open-SWE raw. | Used to isolate cumulative-context leakage. |
| Open-SWE longitudinal snapshots | `artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_*_requests` | Provider accumulation over time. | Same as Open-SWE raw. | Full snapshots at 1k/4k/8k/12k source requests. |
| Open-SWE OpenHands/minimax reservoirs | `artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_*_seed7_hf` | Sample-size sweep. | Same as Open-SWE raw. | Reservoir samples over 5,000 source rows. |
| Open-SWE SWE-agent/minimax local reservoirs | `artifacts/datasets/open_swe_traces_sweagent_minimax_reservoir_*_seed7_local` | Cross-scaffold sample-size robustness check. | Same as Open-SWE raw. | Local workflow-level reservoir samples from the already imported SWE-agent/minimax raw500 dataset; not a full-source HF reservoir. |
| Open-SWE 2x2 scaffold/split datasets | `artifacts/datasets/open_swe_traces_openhands_qwen35_raw_500`, `artifacts/datasets/open_swe_traces_sweagent_*_raw_500` | Cross-scaffold/split replication. | Same as Open-SWE raw. | OpenHands supports repo/owner leakage; SWE-agent currently does not under current low-cost attacks. |
| Open-SWE User Overlay Dataset B | `artifacts/datasets/open_swe_user_overlay_u3_mixed_1000`, `artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000` | Trace-grounded semi-synthetic user-level benchmark. | Synthetic `user_id`/org/project/workflow/profile truth over real Open-SWE trace substrate. | Injection plan in `docs/open-swe-user-overlay-injection-plan.md`; generated U3/U4 datasets include 12,000 requests and cumulative 1k/4k/8k/12k snapshots. Not real Open-SWE user identity evidence. |
| SWE-bench Lite natural adapted | `artifacts/datasets/swe_bench_lite_natural_balanced_sample` | Independent repaired real-repo workflow validation. | repo/project and repo owner labels; no reliable user labels. | Agent-like repaired workflow dataset, not raw agent logs. |
| SWE-bench Lite repaired variants | `artifacts/datasets/swe_bench_lite_repaired_*` | Repair-policy boundary experiments. | repo/project and repo owner labels. | Use only as repaired/deployment-variant evidence. |
| Synthetic Dataset A | `artifacts/datasets/synthetic_mvp` | Controlled full-truth benchmark. | full org/user/project/workflow/turn/profile truth. | Use for controlled sweeps and user-level/profile experiments, not as main real-data evidence. |

## Archived Historical / Debug Datasets

The following are useful for smoke checks and historical comparison but should not be cited as
main paper evidence unless explicitly regenerated and audited. They live under
`artifacts/datasets/_archive/legacy_samples/`; see `artifacts/datasets/_archive/README.md`.

- `artifacts/datasets/_archive/legacy_samples/open_swe_traces_sample`
- `artifacts/datasets/_archive/legacy_samples/open_swe_traces_raw_sample`
- `artifacts/datasets/_archive/legacy_samples/open_swe_traces_repo_workspace_sample`
- `artifacts/datasets/_archive/legacy_samples/swe_bench_lite_repaired_sample`
- `artifacts/datasets/_archive/legacy_samples/swe_bench_lite_repaired_workspace_sample`

## Provider-View Guardrails

- Do not put `org_id`, `user_id`, `workflow_id`, `project_id`, `turn_id`, provenance, source rows, repair metadata, or experiment labels in `attack_view.jsonl`.
- Keep source/repair information in `request_provenance.jsonl` and manifests.
- Open-SWE `org_id` is GitHub owner / owner-like label, not an enterprise organization.
- Open-SWE user-level reconstruction must be reported as N/A.
