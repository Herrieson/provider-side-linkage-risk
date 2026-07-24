# AAAI-27 Overleaf Source

This directory is the authoritative Overleaf source for the anonymous AAAI-27 submission. Set
`api.tex` as the main document and select the **pdfLaTeX** compiler. The source uses the unmodified
official `aaai2027.sty` and `aaai2027.bst` files from the AAAI-27 Author Kit (template version
2027.1).

## Documents

- `api.tex`: anonymous main paper.
- `supplement.tex`: separate supplementary document containing implementation details, calibration,
  robustness, mitigation tradeoffs, and additional analyses.
- `references.bib`: bibliography used by the main paper.
- `aaai2027.sty`, `aaai2027.bst`: official AAAI-27 style and bibliography files; do not modify them.
- `figures/carp_pipeline.pdf`, `figures/results_overview.pdf`, and
  `figures/t3_longitudinal.pdf`: figures used by the main paper.
- `figures/evidence_layers.pdf`: figure used only by the supplementary document.

The anonymous artifact is listed through the official `links` environment immediately after the
abstract. It is printed as a copyable text URL rather than an embedded PDF hyperlink because
AAAI-27 prohibits `hyperref` and embedded links. A source comment marks it for replacement with the
canonical repository URL in the camera-ready version. The `submission` option suppresses author
identities and replaces the camera-ready copyright notice with AAAI's anonymous-review notice; do
not add `\nocopyright`. For an accepted version, remove the `submission` option and restore the
authors and affiliations according to the camera-ready instructions.

## AAAI-27 Submission Checks

The main submission must satisfy all of the following:

- US Letter, AAAI two-column format, compiled with pdfLaTeX;
- at most seven pages of non-reference content and at most nine pages total, with pages 8--9 used
  exclusively for references;
- no author or affiliation information and no acknowledgments in the review version;
- no `hyperref`, embedded links/bookmarks, page numbers, headers, or custom layout/spacing changes;
- PDF version 1.5 or later, with every font embedded and no Type 3 font, including inside figures;
- figure labels at least 9 pt at their final printed size;
- figures in PDF/PNG/JPEG form, with no LaTeX `trim` or `clip` operations;
- a separately uploaded completed AAAI-27 reproducibility checklist;
- any Code and Data Supplement and Supplementary Document uploaded in their designated OpenReview
  fields rather than appended after the main paper's references.

At initial review submission, AAAI-27 requires PDF files rather than the source archive. If source is
later requested, upload only the `.tex`, `.bib`, official style files, and graphics actually used by
the relevant document. Do not include editable figure sources or obsolete template files in the
submission archive.

## Overleaf Build Procedure

1. Select `api.tex` as the main document and compile with pdfLaTeX.
2. Confirm that the references start no earlier than page 8 if the paper uses all seven content
   pages, and that no non-reference content appears on pages 8--9.
3. Temporarily select `supplement.tex` and compile the supplementary PDF separately.
4. Download both PDFs and inspect page size, page count, font embedding, PDF version, anonymity,
   unresolved citations/references, and overfull boxes before uploading them to OpenReview.

The repository's current vector figures contain no Type 3 fonts, but Matplotlib embeds their
DejaVu Sans text through CID/Identity-H font objects. The Author Kit requires CID/Identity-H figure
fonts to be converted to outlines or removed. Some labels are also smaller than the stated 9 pt
minimum at final printed size. Before submission, regenerate or simplify the figures so all labels
remain at least 9 pt after LaTeX scaling and export them either with outlined Latin text or as
genuinely high-resolution bitmaps at the final print dimensions. Do not merely enlarge the PDFs'
page boxes to hide either issue.

Official sources used for this setup (checked 2026-07-24):

- AAAI-27 submission instructions: <https://aaai.org/conference/aaai/aaai-27/submission-instructions/>
- AAAI-27 Author Kit: <https://aaai.org/authorkit27/>
