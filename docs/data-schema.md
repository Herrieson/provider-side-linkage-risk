# Data Schema

## Attack View

Each line in `attack_view.jsonl` is a JSON object:

```json
{
  "request_id": "req_000001",
  "timestamp": "2026-01-01T09:12:30Z",
  "model": "generic-agent-model",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    {"role": "tool", "name": "shell", "content": "..."}
  ],
  "tool_schemas": [
    {"name": "shell", "parameters": ["cmd", "cwd"]}
  ],
  "token_count": 1200,
  "cache_bucket": "medium",
  "provider_metadata": {
    "api_surface": "chat_completions",
    "brokered": true,
    "stream": false
  }
}
```

`attack_view.jsonl` is intended to approximate what a model API provider can observe in
inference logs after an anonymous broker removes explicit identity. It may include request
timing, model name, plaintext messages, provider-side tool schema representation, token counts,
cache buckets when available, and coarse provider metadata.

It must not include:

- `org_id`, `user_id`, `project_id`, `workflow_id`, `turn_id`
- `profile_truth`
- source dataset names, provenance rows, repair metadata, or synthetic labels
- experiment labels such as `defense`, `ablation`, or `repair_mode`

Some fields are controlled approximations:

- `timestamp` is provider-visible in real logs, but is repaired/synthetic for Open-SWE and
  SWE-bench-derived datasets when the source lacks provider-log timestamps.
- `tool_schemas` approximate the schema/shape a provider would see for tool-capable API calls.
- `cache_bucket` is optional and should be `null` when not modeled.

## Ground Truth

Each line in `ground_truth.jsonl` is keyed by `request_id`:

```json
{
  "request_id": "req_000001",
  "org_id": "org_003",
  "user_id": "user_003_02",
  "project_id": "proj_003_01",
  "workflow_id": "wf_003_02_014",
  "turn_id": 4,
  "task_type": "test_failure_diagnosis",
  "profile_truth": {
    "industry": ["finance"],
    "languages": ["python"],
    "frameworks": ["fastapi"],
    "databases": ["postgresql"],
    "cloud_providers": ["aws"],
    "ci_cd_systems": ["github_actions"],
    "auth_systems": ["oauth2"],
    "repo_names": ["risk-engine"],
    "service_names": ["fraud-score"],
    "internal_domains": ["risk.internal"]
  }
}
```

## Profile Fields

The MVP evaluates only fields that can be justified with evidence:

- `industries`
- `languages`
- `frameworks`
- `databases`
- `cloud_providers`
- `ci_cd_systems`
- `auth_systems`
- `repo_names`
- `service_names`
- `internal_domains`
- `security_clues`

Every predicted profile value should include at least one `request_id` as evidence.

## Time Snapshots

Longitudinal experiments can create cumulative provider-view snapshots from any dataset:

```bash
uv run python -m agent_privacy.data.time_snapshots \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000 \
  --output-dir artifacts/datasets/open_swe_traces_raw_1000_snapshots \
  --request-counts 1000 3000 6000 12000
```

Each snapshot directory contains the same provider-view `attack_view.jsonl` schema plus
evaluation-only `ground_truth.jsonl` and optional `request_provenance.jsonl`.

## Trace-Grounded User Overlay

Open-SWE-derived datasets do not contain reliable real `user_id` labels. When user-level
evaluation is needed, use a separate trace-grounded semi-synthetic overlay dataset rather than
claiming real Open-SWE user identities.

The overlay keeps Open-SWE agent traces as the content substrate and injects synthetic
provider-visible user/environment/time signals. The evaluation labels are synthetic and live
only in `ground_truth.jsonl`, `profiles.json`, and `request_provenance.jsonl`.

The attack view rules do not change:

- no `user_id`, `org_id`, `project_id`, `workflow_id`, `turn_id`, source ids, or overlay labels
  in `attack_view.jsonl`;
- source Open-SWE ids are provenance-only;
- injected user signals must appear only through provider-visible surfaces such as message/tool
  content, tool schema shape, timestamp, token count, cache bucket, or allowed provider metadata.

The current injection design is specified in
`docs/open-swe-user-overlay-injection-plan.md`. Initial configuration drafts are:

- `configs/open_swe_user_overlay_u3.json`
- `configs/open_swe_user_overlay_u4_hard_shared.json`
