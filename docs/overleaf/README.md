# Overleaf Submission Source

Set `api.tex` as the Overleaf main document and use the pdfLaTeX compiler. The directory is
self-contained for the main paper and supplementary material:

- `api.tex`: anonymous manuscript in the supplied AAAI template;
- `supplement.tex`: parameter tables, calibration details, metric/cost analysis,
  mitigation tradeoffs, external-validity boundaries, learned-representation comparisons, and the
  observation-equivalence analysis;
- `references.bib`: the 32 cited references;
- `aaai.sty` and `aaai.bst`: supplied template styles;
- `figures/carp_pipeline.pdf`: measurement contract with the complementary CARP and ASL paths.
- `figures/results_overview.pdf`: four-panel summary of linkage channels, concurrency, Agent-state
  gains, and the indistinguishability limit.
- `figures/t3_longitudinal.pdf`: hierarchical propagation and later-traffic watchlist results.
- `figures/evidence_layers.pdf`: supplementary map from trace substrates and truth to supported
  research questions.

`fixbib.sty` is retained from the supplied template but is not used by the manuscript and does not
need to be included in a minimal submission archive.

The anonymous source uses `Anonymous Submission` and disables the camera-ready copyright notice.
Replace the author block and remove `\nocopyright` only when preparing the accepted camera-ready
version under the venue instructions.

## Build Check

The pre-review migration was checked with a multi-pass Tectonic/BibTeX build at seven body pages and
eight pages including references. The current review revision adds a separate supplement and changes
the main text, so recompile both `api.tex` and `supplement.tex` in Overleaf before submission and
recheck body-page count, citations, cross-references, overfull boxes, and font embedding. A LaTeX
compiler is not bundled with the repository's default Python environment.

The research notes, evidence audits, and the pre-migration AAAI-2026 working copy remain under
`docs/paper/`. Make submission-text edits in this directory to avoid diverging paper versions.
