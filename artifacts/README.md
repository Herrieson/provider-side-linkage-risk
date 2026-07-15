# Dataset Storage

`artifacts/` is the local data root used by the experiment commands. Dataset payloads are ignored by
Git because the current working set is roughly 16 GB and several JSONL files exceed GitHub's 100 MB
per-file limit.

The GitHub repository contains:

- the dataset catalog in `dataset-manifest.json`;
- dataset cards and schemas under `docs/`;
- importers and deterministic overlay generators under `src/agent_privacy/data/`;
- generation configs under `configs/`;
- a six-request, fully synthetic example under `examples/tool_agent_smoke/`.

The GitHub repository does **not** contain raw Open-SWE, tau-bench, or SWE-bench prompt content.
Rebuild those adapted views from their upstream sources and follow each upstream license. The U3/U4
and T3 overlays retain their upstream trace substrate, so they are not automatically redistributable
just because their entity labels are synthetic.

## Expected Local Layout

Extract an approved release asset at the repository root, or run the commands in
`docs/reproduction.md`, so datasets appear under:

```text
artifacts/
└── datasets/
    ├── open_swe_traces_raw_1000/
    ├── open_swe_traces_raw_1000_turn_delta_3_6_9_12/
    ├── open_swe_user_overlay_u3_mixed_1000/
    ├── open_swe_user_overlay_u4_hard_shared_1000/
    ├── tau_bench_historical_adapted/
    ├── tau_bench_historical_sample200/
    ├── tau_bench_overlay_t3/
    ├── tau_bench_overlay_t3_snapshots/
    └── synthetic_mvp/
```

The full local tree may contain additional scaffold, reservoir, snapshot, and archived runs. Those
are intentionally omitted from the concise public catalog unless they support a paper-facing table.

## Distribution Classes

| Class | Meaning |
| --- | --- |
| `bundled-example` | Small synthetic fixture committed to Git. |
| `regenerate` | Generated entirely by this repository and eligible for a release asset. |
| `regenerate-from-upstream` | Must be rebuilt after obtaining an upstream dataset. |
| `upstream-derived-not-bundled` | Local adapted content; redistribute only after license review. |

To build a ZIP containing the fully generated Synthetic Dataset A:

```bash
uv run python scripts/build_release_bundles.py --bundle synthetic-a --output-dir dist
```

`dist/` is ignored by Git. Upload the ZIP and `SHA256SUMS` as GitHub Release assets, not as normal
repository blobs.
