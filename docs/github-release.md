# GitHub Release Guide

This repository uses a small Git history plus optional GitHub Release assets. Do not upload the
entire local workspace: it contains roughly 16 GB of datasets, 3.2 GB of raw results, and a 5.2 GB
virtual environment.

## 1. Public Git Contents

Normal Git commits should contain:

- `src/agent_privacy/`, `tests/`, `configs/`, and `scripts/`;
- the synthetic `examples/tool_agent_smoke/` fixture;
- dataset/result catalogs and dataset cards;
- aggregate `docs/tables/` CSV/Markdown outputs;
- paper source, bibliography, style files, and vector/PNG figures;
- `.github/workflows/ci.yml`, `pyproject.toml`, and `uv.lock`.

Normal Git commits should not contain:

- `.venv/`, model caches, `.pytest_cache/`, or `.ruff_cache/`;
- dataset payloads under `artifacts/datasets/`;
- raw run payloads under `results/`;
- `dist/` bundles;
- generated Overleaf archives such as `docs/overleaf/*.zip`;
- LaTeX build intermediates or the generated submission PDF.

Run the boundary check before every public push:

```bash
uv run python scripts/release_check.py
```

The check rejects Git candidates above 95 MiB, raw dataset/result payloads, common credential
formats, workspace-specific absolute paths, invalid JSON catalogs, and missing table references.

## 2. License Scope

Original project code and documentation are released under MIT; see `LICENSE`. `THIRD_PARTY.md`
records the boundary around upstream data, publication templates, and dependencies. The MIT License
does not grant permission to redistribute upstream data. Review the current upstream terms for:

- `nvidia/Open-SWE-Traces`;
- `sierra-research/tau-bench` historical trajectories;
- `princeton-nlp/SWE-bench_Lite` and the underlying repositories.

Until that review is complete, publish importer/generator code, configs, aggregate metrics, redacted
examples, and manifests rather than adapted raw prompt/tool text. U3/U4 and T3 overlays still contain
their real upstream trace substrate and therefore remain upstream-derived.

## 3. Validate A Clean Clone

```bash
uv sync --locked --group dev
uv run ruff check .
uv run pytest -q
uv run python scripts/release_check.py
```

Run the bundled example using the command in `examples/tool_agent_smoke/README.md` and compare both
stable outputs. This check requires no paper dataset and no network model download.

Optional dependencies are separated to keep the default install small:

```bash
uv sync --extra data       # upstream dataset import
uv sync --extra paper      # figure generation
uv sync --extra semantic   # MiniLM and HNSW
```

## 4. Build GitHub Release Assets

From the complete local workspace:

```bash
uv run python scripts/build_release_bundles.py --bundle all --output-dir dist
```

This produces:

| Asset | Contents |
| --- | --- |
| `agent-privacy-paper-results.zip` | Whitelisted metrics, run summaries, calibration files, cluster assignments, and referenced paper tables. |
| `agent-privacy-synthetic-a.zip` | Fully generated Synthetic Dataset A, its config, schema, card, and catalog. |
| `SHA256SUMS` | SHA-256 digest for each asset. |

The builder uses fixed ZIP timestamps, sorted paths, normalized permissions, and a fixed compression
level, so unchanged inputs produce byte-identical assets. It excludes raw upstream-derived request
content and evaluation/provenance copies from the result bundle.

Verify the assets:

```bash
cd dist
sha256sum -c SHA256SUMS
```

## 5. First Commit And Push

This workspace began with an empty Git index. Review the candidate set before the first commit:

```bash
git status --short
git add .
git status --short
git diff --cached --stat
uv run python scripts/release_check.py
```

After filling any public author/citation metadata:

```bash
git commit -m "Release provider-side linkage measurement artifact"
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

Create a release with the external assets using either the GitHub UI or GitHub CLI:

```bash
gh release create v0.1.0 \
  dist/agent-privacy-paper-results.zip \
  dist/agent-privacy-synthetic-a.zip \
  dist/SHA256SUMS \
  --title "Artifact v0.1.0" \
  --notes "Code, aggregate tables, curated raw predictions, and generated Synthetic Dataset A."
```

Do not use `git add -f artifacts/` or `git add -f results/`. Once a large blob enters Git history,
deleting it in a later commit does not reduce clone size.

## 6. Release Page Notes

The release description should state:

- which commit and paper version the assets correspond to;
- that Open-SWE and tau-bench adapted prompt payloads are not bundled;
- that T3 and Dataset B are trace-grounded controlled overlays, not production identities;
- that `docs/tables/` is the canonical aggregate result interface;
- that the result ZIP contains request IDs and predicted cluster assignments but no prompt text;
- the Python version and optional extras used for semantic/figure runs.
