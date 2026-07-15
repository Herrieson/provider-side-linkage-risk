from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from agent_privacy.io import read_jsonl
from agent_privacy.profiling.rule_profiler import profile_clusters


PATH_RE = re.compile(r"/(?:home|srv|opt|workspace|tmp)/[A-Za-z0-9_./-]+")
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:internal|local|prod|corp)\b", re.IGNORECASE)
REPO_RE = re.compile(r"\brepository=([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)\b")
TRACE_RE = re.compile(r"\btrace-[a-z0-9-]+(?:-[a-z0-9-]+)+\b")
SECRET_RE = re.compile(r"\bsk-test-[A-Za-z0-9]{16,}\b")


def write_profile_examples(
    *,
    dataset_dir: Path,
    predictions_path: Path,
    output: Path,
    method: str = "hybrid",
    level: str = "org",
    limit: int = 3,
) -> list[dict[str, Any]]:
    rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    truth_by_request = {row["request_id"]: row for row in truth_rows}
    row_by_request = {row["request_id"]: row for row in rows}
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))
    labels = predictions[method][level]
    profiles = profile_clusters(rows, labels)
    ranked = sorted(
        profiles.items(),
        key=lambda item: (
            -sum(len(values) for values in item[1].get("fields", {}).values()),
            item[0],
        ),
    )
    examples = []
    for cluster_id, profile in ranked:
        request_ids = profile.get("request_ids", [])
        majority = _majority_label(request_ids, truth_by_request, "org_id")
        if not majority or str(majority).startswith("noise_"):
            continue
        examples.append(
            {
                "example_id": f"profile_example_{len(examples) + 1}",
                "cluster_id": cluster_id,
                "majority_owner_like_org": _redact_value(str(majority), "ORG"),
                "request_count": len(request_ids),
                "fields": _redacted_fields(profile.get("fields", {})),
                "evidence": _evidence(profile, row_by_request),
            }
        )
        if len(examples) >= limit:
            break
    _write_markdown(output, examples)
    output.with_suffix(".json").write_text(json.dumps(examples, indent=2, sort_keys=True), encoding="utf-8")
    return examples


def _majority_label(
    request_ids: list[str],
    truth_by_request: dict[str, dict[str, Any]],
    field: str,
) -> str | None:
    counts: dict[str, int] = {}
    for request_id in request_ids:
        if request_id not in truth_by_request:
            continue
        value = str(truth_by_request[request_id].get(field))
        counts[value] = counts.get(value, 0) + 1
    return max(counts, key=counts.get) if counts else None


def _redacted_fields(fields: dict[str, list[str]]) -> dict[str, list[str]]:
    keep = [
        "languages",
        "frameworks",
        "package_managers",
        "build_tools",
        "repo_names",
        "ci_cd_systems",
        "service_names",
        "internal_domains",
    ]
    out = {}
    for field in keep:
        values = fields.get(field, [])
        if not values:
            continue
        if field in {"repo_names", "service_names", "internal_domains"}:
            out[field] = [_redact_value(value, field.upper()) for value in values[:5]]
        else:
            out[field] = values[:5]
    return out


def _evidence(
    profile: dict[str, Any],
    row_by_request: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    evidence_rows = []
    evidence = profile.get("evidence", {})
    for field, values in sorted(evidence.items(), key=lambda item: _field_rank(item[0])):
        if field not in {"languages", "frameworks", "package_managers", "build_tools", "repo_names", "ci_cd_systems"}:
            continue
        for value, request_ids in values.items():
            evidence_item = _best_evidence_item(field, str(value), request_ids, row_by_request)
            if evidence_item:
                evidence_rows.append(evidence_item)
        if len(evidence_rows) >= 6:
            break
    return evidence_rows[:6]


def _field_rank(field: str) -> int:
    ranks = {
        "frameworks": 0,
        "package_managers": 1,
        "build_tools": 2,
        "ci_cd_systems": 3,
        "languages": 4,
        "repo_names": 5,
    }
    return ranks.get(field, 99)


def _best_evidence_item(
    field: str,
    value: str,
    request_ids: list[str],
    row_by_request: dict[str, dict[str, Any]],
) -> dict[str, str] | None:
    candidates = []
    for request_id in request_ids[:8]:
        row = row_by_request.get(request_id)
        if not row:
            continue
        snippet = _snippet(row, preferred_value=value)
        if not snippet:
            continue
        candidates.append(
            (
                _snippet_score(snippet, value),
                {
                    "field": field,
                    "value": (
                        _redact_value(value, field.upper())
                        if field in {"repo_names", "service_names"}
                        else value
                    ),
                    "request_id": _redact_value(request_id, "REQ"),
                    "snippet": snippet,
                },
            )
        )
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _snippet(row: dict[str, Any], preferred_value: str | None = None) -> str:
    messages = row.get("messages", [])
    preferred_roles = ["tool", "user", "assistant"]
    chunks = []
    for role in preferred_roles:
        for message in messages:
            if message.get("role") != role:
                continue
            content = str(message.get("content", ""))
            if not _usable_snippet_content(content):
                continue
            chunks.append(content)
            if preferred_value and preferred_value.lower() in content.lower():
                return _redact_text(content)
    text = "\n".join(chunks)
    if not text:
        text = "\n".join(
            str(message.get("content", ""))
            for message in messages
            if _usable_snippet_content(str(message.get("content", "")))
        )
    return _redact_text(text)


def _usable_snippet_content(text: str) -> bool:
    if not text.strip():
        return False
    banned = [
        "You are OpenHands agent",
        "We need modify",
        "You are an AI assistant",
        "<uploaded_files>",
    ]
    return not any(marker in text for marker in banned)


def _redact_text(text: str) -> str:
    text = SECRET_RE.sub("[SECRET]", text)
    text = TRACE_RE.sub("[TRACE]", text)
    text = REPO_RE.sub("repository=[OWNER]/[REPO]", text)
    text = PATH_RE.sub("[PATH]", text)
    text = DOMAIN_RE.sub("[DOMAIN]", text)
    compact = " ".join(text.split())
    return compact[:260]


def _snippet_score(snippet: str, value: str) -> int:
    score = 0
    lower = snippet.lower()
    if value.lower() in lower:
        score += 10
    for marker in ("package.json", "pyproject.toml", "requirements.txt", "pytest", "npm", "docker", "github"):
        if marker in lower:
            score += 1
    return score


def _redact_value(value: str, kind: str) -> str:
    if kind == "INTERNAL_DOMAINS":
        return "[DOMAIN]"
    if kind in {"REPO_NAMES", "SERVICE_NAMES", "ORG", "REQ"}:
        return f"[{kind}]"
    return value


def _write_markdown(path: Path, examples: list[dict[str, Any]]) -> None:
    lines = ["# Redacted Reconstructed Profile Examples", ""]
    for example in examples:
        lines.extend(
            [
                f"## {example['example_id']}",
                "",
                f"- Cluster: `{example['cluster_id']}`",
                f"- Majority owner-like label: `{example['majority_owner_like_org']}`",
                f"- Requests: {example['request_count']}",
                "",
                "### Fields",
                "",
            ]
        )
        for field, values in example["fields"].items():
            lines.append(f"- `{field}`: `{values}`")
        lines.extend(["", "### Evidence", ""])
        for evidence in example["evidence"]:
            lines.append(
                f"- `{evidence['field']}` = `{evidence['value']}` from `{evidence['request_id']}`: {evidence['snippet']}"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write redacted reconstructed profile examples.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("docs/redacted-profile-examples.md"))
    parser.add_argument("--method", default="hybrid")
    parser.add_argument("--level", default="org")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    examples = write_profile_examples(
        dataset_dir=args.dataset_dir,
        predictions_path=args.predictions,
        output=args.output,
        method=args.method,
        level=args.level,
        limit=args.limit,
    )
    print({"examples": len(examples), "output": str(args.output)})


if __name__ == "__main__":
    main()
