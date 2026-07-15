# Artifact Release Checklist

## Versioned in Git

- `src/`, `tests/`, `configs/`, `scripts/`, `examples/`, `.github/`, `README.md`,
  `pyproject.toml`, and `uv.lock`.
- Narrative documentation, dataset cards, reproduction commands, and curated `docs/tables/`.
- Paper source, bibliography, and PDF/PNG figures.
- Artifact, dataset, and result manifests plus the claim audit.
- MIT `LICENSE` and `THIRD_PARTY.md` scope notice.

## Kept Out of Git

- Dataset payloads under `artifacts/` (about 16 GB); only its README/catalog are versioned.
- Raw outputs under `results/` (about 3.2 GB); only its README/catalog are versioned.
- `.venv/` and local Hugging Face/model caches.
- LaTeX build products and generated submission PDF.

## External Release Decision Required

- Keep MIT code licensing separate from upstream dataset and author-kit terms.
- Review upstream licenses before redistributing adapted Open-SWE, SWE-bench, or tau-bench text.
- Prefer scripts, manifests, derived metrics, and redacted examples over raw prompt/tool content.
- Do not release provider-view rows containing sensitive-looking source fragments without manual
  inspection and license approval.
- Keep source/provenance identifiers out of any public attack-view sample.

## Clean Reproduction Gate

1. Create a fresh environment from `uv.lock`.
2. Run `uv run ruff check .`.
3. Run `uv run pytest -q`.
4. Run `uv run python scripts/release_check.py`.
5. Validate all three JSON catalogs/manifests.
6. Run and diff the bundled synthetic smoke example.
7. Build release ZIPs and verify `dist/SHA256SUMS`.
8. Regenerate the three paper figures.
9. Regenerate the main baseline/ordering, cross-workflow validity, bootstrap, T3, zero-label
   transfer, held-out sensitivity, controlled scale, and profile summary tables.
10. Compile `docs/overleaf/api.tex` with pdfLaTeX in the supplied AAAI Overleaf project.
11. Confirm figure fonts are embedded and the main text fits the venue page limit.
