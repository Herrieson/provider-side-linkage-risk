# Attack Feasibility Data Stance

## Current Priority

The current priority is not defense evaluation. It is to make the attack-feasibility dataset
and scenario defensible:

```text
No toy-only data.
No adding labels into the attack view and then proving labels are recoverable.
No treating repaired context as raw evidence.
No claiming enterprise production logs when using open-source agent trajectories.
```

## Primary Evidence

The primary evidence should come from:

```text
Open-SWE-Traces raw sample
repair_mode = none
```

This means:

- no added `repository=` field;
- no added repair workspace path;
- no synthetic secret;
- no source/provenance/repair fields inside `attack_view.jsonl`;
- timestamps are still repaired because the source rows do not provide provider-log timing;
- user-level scoring is skipped because reliable user identity is unavailable.

`attack_view.jsonl` is now constrained to provider-visible fields:

- `request_id`
- `timestamp`
- `model`
- `messages`
- `tool_schemas`
- `token_count`
- `cache_bucket`
- `provider_metadata`

Conversion metadata is stored separately in `request_provenance.jsonl` and must not be used
by attacks.

The current 100-trajectory raw sample still contains workspace paths in the original
OpenHands trajectory content. This is not a repair added by our importer. It is a realistic
agent-environment artifact and should be audited explicitly.

## First Raw Sample Result

Dataset:

- Open-SWE-Traces
- config: `openhands`
- split: `minimax_m25`
- trajectories: 100
- converted requests: 1,200
- workflows: 100
- projects/repos: 96
- owners/orgs: 94

M0 attack-only result:

| Method | Session F1 | Project/Repo F1 | Org/Owner F1 |
| --- | ---: | ---: | ---: |
| Temporal | 0.116 | 0.036 | 0.037 |
| Rare | 0.000 | 1.000 | 0.021 |
| Tool/schema | 0.018 | 0.020 | 0.021 |
| Hybrid | 0.998 | 1.000 | 1.000 |

Interpretation:

- Project/repo linking is easy because raw agent trajectories expose repository/workspace
  artifacts.
- Session reconstruction is not solved by rare features alone; it needs hybrid context overlap.
- Owner/org recovery in this sample follows from project/repo recovery because several owners
  have repeated trajectories.

## Weak Points To Address Before Making Strong Claims

1. Workspace/path ablation:
   - remove `/workspace/...` paths from attack view;
   - keep natural code/tool text;
   - test whether sessions remain recoverable.

2. Project versus organization:
   - report project/repo-level separately from owner/org-level;
   - avoid presenting owner-level recovery as enterprise identity recovery.

3. Sample scale:
   - repeat on 1,000 trajectories;
   - report owner/project repetition distribution;
   - avoid cherry-picking splits.

4. Source diversity:
   - run `openhands/minimax_m25`, `openhands/qwen35_122b`, `sweagent/minimax_m25`,
     and `sweagent/qwen35_122b`;
   - check whether linkability is scaffold-specific.

5. Candidate-edge audit:
   - log which features created session/project/org edges;
   - show examples without exposing excessive source text;
   - quantify path/repo/context contribution.

6. No-repair reporting:
   - every result table must say the repair mode;
   - raw results must be reported before repaired variants.

7. Provider-view audit:
   - every dataset used for attack feasibility must report non-provider fields in
     `attack_view.jsonl`;
   - the expected value for raw attack experiments is an empty list.

## Role Of Repaired Data

Repaired data is allowed only as a separate variant:

- `repository`: adds explicit `repository=<owner>/<repo>`.
- `workspace`: adds explicit `/workspace/<owner>__<repo>`.
- `repository_workspace`: adds both.

These are realistic for many Agent environments, but they are not raw evidence. They should
be described as upper-bound or deployment-variant experiments.
