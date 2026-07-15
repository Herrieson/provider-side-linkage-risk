# Synthetic Tool-Agent Smoke Example

This tiny, fully synthetic fixture exercises the provider-view schema and the budgeted CARP
reference attack without downloading an upstream dataset. It is a software sanity check, not a
paper result.

## Contents

| Path | Purpose |
| --- | --- |
| `source/trajectories.jsonl` | Three synthetic retail/airline-style tool trajectories. |
| `dataset/attack_view.jsonl` | Six provider-visible cumulative requests. |
| `dataset/ground_truth.jsonl` | Evaluation-only session/user/project/org labels. |
| `dataset/request_provenance.jsonl` | Conversion provenance, never read by the attack. |
| `dataset/source_manifest.json` | Converter settings and row counts. |
| `expected/` | Deterministic cluster assignments and metrics for the command below. |

All identifiers and business objects in this fixture are invented. The fixture is shaped like a
tool-agent trajectory export but does not contain rows copied from tau-bench or a production log.

## Run

From the repository root:

```bash
uv sync --group dev
uv run agent-privacy-run \
  --dataset-dir examples/tool_agent_smoke/dataset \
  --output /tmp/agent-privacy-smoke \
  --defenses M0 \
  --levels session user project org \
  --methods provider_lowcost \
  --ablations none \
  --feature-ablations none \
  --skip-profile \
  --skip-ordering \
  --stream-provider-lowcost
```

Compare the stable outputs:

```bash
diff -u \
  examples/tool_agent_smoke/expected/clustering_metrics_all.csv \
  /tmp/agent-privacy-smoke/clustering_metrics_all.csv

diff -u \
  examples/tool_agent_smoke/expected/predictions.json \
  /tmp/agent-privacy-smoke/M0/predictions.json
```

The expected pairwise F1 is `1.0` for session, user, and project on this deliberately tiny fixture.
Organization linkage remains `0.0`; the example is not intended as an accuracy benchmark.

## Rebuild The Adapted View

```bash
uv run python -m agent_privacy.data.tau_bench \
  --input-path examples/tool_agent_smoke/source \
  --output-dir /tmp/agent-privacy-smoke-dataset \
  --limit 10
```
