# Result Storage

`results/` is the local root for raw experiment outputs. The complete working tree is roughly
3.2 GB, including archived and diagnostic runs, so raw outputs are ignored by Git.

Use the repository in this order:

1. Read the paper-facing CSV/Markdown summaries in `docs/tables/`.
2. Use `result-manifest.json` to map each claim to its raw run directory.
3. Download the optional `agent-privacy-paper-results.zip` GitHub Release asset when request-level
   cluster assignments are needed for bootstrap or audit.
4. Regenerate a raw run with `docs/reproduction.md` when the release asset is unavailable.

The results release bundle intentionally excludes:

- copied or transformed `attack_view.jsonl` payloads;
- `ground_truth.jsonl` and request provenance copied inside result directories;
- reconstructed workflow dumps containing evaluation-only majority labels;
- large semantic profile prediction objects;
- archived, failed, exploratory, and debug runs.

It includes compact metrics, run summaries, calibration tables, and cluster assignment
`predictions.json` files for the curated linkage runs. The committed `docs/tables/` files remain the
canonical paper interface.

Build the optional result asset from a complete local workspace:

```bash
uv run python scripts/build_release_bundles.py --bundle results --output-dir dist
```

Upload `dist/agent-privacy-paper-results.zip` and `dist/SHA256SUMS` to GitHub Releases. Do not force
add the ignored local result directories to Git.
