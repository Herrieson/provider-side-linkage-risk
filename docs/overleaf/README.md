# Overleaf Submission Source

Set `api.tex` as the Overleaf main document and use the pdfLaTeX compiler. The directory is
self-contained for the main paper:

- `api.tex`: anonymous manuscript in the supplied AAAI template;
- `references.bib`: the 32 cited references;
- `aaai.sty` and `aaai.bst`: supplied template styles;
- `figures/carp_pipeline.pdf` and `figures/t3_longitudinal.pdf`: the two figures used by the paper.

`fixbib.sty` is retained from the supplied template but is not used by the manuscript and does not
need to be included in a minimal submission archive.

The anonymous source uses `Anonymous Submission` and disables the camera-ready copyright notice.
Replace the author block and remove `\nocopyright` only when preparing the accepted camera-ready
version under the venue instructions.

## Build Check

The migration was checked with a multi-pass Tectonic/BibTeX build. It produces seven body pages
and eight pages including references, within the limits of seven body pages and nine total pages.
All 32 citations and all four cross-references resolve, both figures are present, and the log has no
overfull boxes. Tectonic uses an XeTeX-compatible font fallback for this older pdfLaTeX-oriented
style, so font embedding should be checked again on the PDF exported by Overleaf.

The research notes, evidence audits, and the pre-migration AAAI-2026 working copy remain under
`docs/paper/`. Make submission-text edits in this directory to avoid diverging paper versions.
