# Submission Readiness Report

Pre-review migration validated on 2026-07-15. The current review-driven readability,
external-validity, positioning, and impossibility revisions require a fresh Overleaf build before
this report can be treated as final.

## Scope

- The paper centers the provider-side attack, threat model, sparse reconstruction, longitudinal
  tracking, and partial technical profiling.
- Defense is limited to mitigation implications. There is no defense research question,
  contribution, main table, or real task-utility claim.
- Open-SWE owner labels, overlay evidence, tau-bench historical status, and profiling limits follow
  the boundaries in `submission-scope.md` and `claim-audit.md`.

## Reproduction Gate

| Check | Result |
| --- | --- |
| `uv sync --locked` | passed; 87 packages audited |
| `uv run ruff check .` | passed |
| `uv run pytest` | passed; 80 tests |
| Artifact manifest JSON | valid; release check passes with current references |
| Manifest path existence | passed; no missing artifact/dataset/result paths |
| Cross-workflow entity validity | passed; held-out project/owner F1 0.994/0.981 on 900 workflows |
| Direct exposure audit | passed; canonical project/owner labels recoverable from every held-out Open-SWE request |
| Provider-specific method contract | passed; measurement-framework figure, attack-view/truth separation, cold-start/no-target assumptions, multi-level streaming constraints, ambiguity rejection, and applicability table included |
| Deployment applicability evidence | passed; official Cloudflare, OpenAI, and Microsoft documents distinguish prompt logging, retention, modified monitoring, and zero-retention configurations |
| Workflow-continuity controls | passed; exact nesting F1 1.000, CARP/Hybrid turn-delta F1 0.117, strict-removal turn-delta F1 0.016 |
| Paired CARP-Hybrid comparison | passed; session-F1 difference -0.016 with paired CI [-0.039,-0.002] |
| Candidate-stage diagnostic | passed; CARP candidate recall/precision 1.000/0.172; bottom-k shingle-sketch candidate recall/precision 0.990/0.116 and final F1 0.858 |
| Historical tau-bench evidence closure | passed; 40-workflow calibration, 160-workflow held-out baselines, domain breakdown, 200 workflow-bootstrap CIs, and precision-constrained operating point |
| Cross-domain stable-handle audit | passed; Open-SWE namespace and natural tau identity/process/resource families reported separately; shared tau resources have 0.498 cross-user ambiguity and are candidate-only |
| Natural tau stable-handle linkage | passed; held-out user precision/recall/F1 1.000/0.400/0.571 [0.515,0.623], cross-workflow F1 0.561, and no-handle F1 0 |
| tau-bench temporal stress | passed; temporal F1 falls from 0.736 to 0.125/0.035 at peak concurrency 10/41; time-independent CARP-Content F1 is 0.960 and 0.843 under intent rephrasing |
| Strict-removal semantic project linkage | passed; project-disjoint CARP-Content precision/recall/F1 0.795/0.597/0.682 on 479 unseen projects |
| Cross-scaffold semantic project linkage | passed; SWE-agent direct anchors zero, CARP-Content precision/recall/F1 0.942/0.286/0.439 on 280 unseen projects |
| Zero-target-label cross-scaffold transfer | passed; source-calibrated mutual linkage reaches precision/F1 0.909/0.318 OpenHands-to-SWE-agent and 0.978/0.179 in reverse |
| Held-out threshold sensitivity | passed; candidate recall remains 1.000 for budgets 100--800; containment is the principal sensitive context parameter |
| Controlled 100K scale | passed; 11.0--11.2 comparisons/request, 1.000 candidate recall, stable collision F1 0.938, and 0.664 GB peak RSS at 100K |
| Observation-equivalence analysis | passed; analytic entity/pairwise bounds plus deterministic exchangeable-view runs for 1/2/4/8/16 entities per class |
| Pair imbalance and asymmetric costs | passed; exact TP/FP/FN/TN counts, false links per million negative pairs, and FP/FN cost-ratio sensitivity on held-out Open-SWE |
| Natural historical user watchlist | passed; later-user-ID removal F1 0.984 [0.959,1.000], name--zip-only F1 0.624 [0.505,0.729]; identity-masked/base-task-disjoint semantic rows are retained only as diagnostics |
| HNSW ANN comparison | passed; efSearch=200 candidate recall/final F1 0.993/0.956 versus exact dense F1 0.960 |
| Turn-order reconstruction | passed; held-out pairwise accuracy 0.833 on 860 pure clusters |
| Extension bootstrap regeneration | passed; 13 rows at 500 iterations; T3 cold-start F1 0.771/0.686/0.777 and watchlist F1 0.702/0.830/0.876 |
| T3 anchor robustness | passed; anchor statistics plus retention, later-alias rotation, and shared-collision sweeps |
| Reader navigation | passed; operational terminology and overall controlled-takeaway tables appear before the detailed method/results they organize |
| Figure inventory | passed at source level; framework/CARP, four-panel trend, and T3 result figures are included, with one supplementary evidence-layer figure retained in the artifact package |
| Overleaf-source migration build | pre-review build passed; current `api.tex` and new `supplement.tex` pending fresh Overleaf pdfLaTeX build |
| Bibliography and citations | pre-review build passed; current revision pending compile recheck |
| Layout | pre-review build had no overfull boxes; current revision pending recheck |
| Final PDF fonts | recheck the pdfLaTeX PDF exported by Overleaf; the local Tectonic smoke build uses XeTeX-compatible fallbacks |

## Repository Boundary

`artifacts/`, `results/`, `.venv/`, LaTeX intermediates, and the generated submission PDF remain
outside Git. Code, configs, tests, curated tables, manuscript sources, official style files, and
paper figures remain trackable.

## Non-Blocking Extensions

Full original Open-SWE longitudinal bootstrap intervals and a full-source SWE-agent reservoir are
optional robustness extensions. They are not required by the current scoped claims. Author
identities and submission-system metadata remain intentionally unset for
anonymous review.
