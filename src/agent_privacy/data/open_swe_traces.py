from __future__ import annotations

import argparse
import http.client
import json
import random
import time
import urllib.parse
import urllib.request
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from agent_privacy.io import write_json, write_jsonl


@dataclass(frozen=True)
class OpenSWEImportConfig:
    input_path: str | None = None
    output_dir: str = "artifacts/datasets/open_swe_traces_sample"
    hf_dataset: str = "nvidia/Open-SWE-Traces"
    hf_config: str = "default"
    hf_split: str = "train"
    use_hf: bool = False
    limit: int = 1000
    sample_mode: str = "first"
    max_source_rows: int | None = None
    seed: int = 7
    max_turns_per_trajectory: int = 12
    min_messages_per_trajectory: int = 2
    timestamp_start: str = "2026-01-05T09:00:00Z"
    timestamp_jitter_minutes: int = 120
    repair_mode: str = "none"
    synthetic_secret_rate: float = 0.0
    include_provenance_in_attack_view: bool = False


def import_open_swe_traces(config: OpenSWEImportConfig) -> dict[str, Any]:
    rng = random.Random(config.seed)
    output_dir = Path(config.output_dir)
    base_time = datetime.fromisoformat(config.timestamp_start.replace("Z", "+00:00"))

    attack_rows: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    source_rows = 0
    eligible_trajectories = 0
    selected: list[
        tuple[int, tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]]
    ] = []

    for row_idx, source_row in enumerate(_iter_rows(config)):
        if config.max_source_rows is not None and source_rows >= config.max_source_rows:
            break
        source_rows += 1
        if config.sample_mode == "first" and len(selected) >= config.limit:
            break
        converted = _convert_row(source_row, row_idx, config, rng, base_time)
        if converted is None:
            continue
        attack, truth, provenance = converted
        if len(attack) < config.min_messages_per_trajectory:
            continue
        eligible_trajectories += 1
        if config.sample_mode == "first":
            selected.append((row_idx, converted))
        elif config.sample_mode == "reservoir":
            _reservoir_add(selected, (row_idx, converted), eligible_trajectories, config.limit, rng)
        else:
            raise ValueError(f"unknown sample_mode: {config.sample_mode}")

    selected.sort(key=lambda item: item[0])
    used_trajectories = len(selected)
    for _, converted in selected:
        attack, truth, provenance = converted
        attack_rows.extend(attack)
        truth_rows.extend(truth)
        provenance_rows.extend(provenance)

    joined = list(zip(attack_rows, truth_rows, provenance_rows, strict=True))
    joined.sort(key=lambda pair: (pair[0]["timestamp"], pair[0]["request_id"]))
    attack_rows = [pair[0] for pair in joined]
    truth_rows = [pair[1] for pair in joined]
    provenance_rows = [pair[2] for pair in joined]

    write_jsonl(output_dir / "attack_view.jsonl", attack_rows)
    write_jsonl(output_dir / "ground_truth.jsonl", truth_rows)
    write_jsonl(output_dir / "request_provenance.jsonl", provenance_rows)
    write_json(
        output_dir / "source_manifest.json",
        {
            "source": "Open-SWE-Traces",
            "config": asdict(config),
            "source_rows_seen": source_rows,
            "eligible_trajectories": eligible_trajectories,
            "trajectories_used": used_trajectories,
            "sample_mode": config.sample_mode,
            "max_source_rows": config.max_source_rows,
            "requests": len(attack_rows),
            "truth": len(truth_rows),
            "provenance": len(provenance_rows),
            "notes": [
                "This is an adapted real-repository agent trajectory dataset.",
                "Timestamps are repair fields.",
                "Content repair is controlled by repair_mode.",
                "attack_view.jsonl defaults to provider-visible fields only.",
                "request_provenance.jsonl stores conversion metadata that attacks must not use.",
                "User-level ground truth is unavailable and should be skipped.",
            ],
        },
    )
    return {
        "source_rows_seen": source_rows,
        "eligible_trajectories": eligible_trajectories,
        "trajectories_used": used_trajectories,
        "requests": len(attack_rows),
        "truth": len(truth_rows),
        "output_dir": str(output_dir),
    }


def _reservoir_add(
    reservoir: list[
        tuple[int, tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]]
    ],
    item: tuple[int, tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]],
    seen: int,
    limit: int,
    rng: random.Random,
) -> None:
    if limit <= 0:
        return
    if len(reservoir) < limit:
        reservoir.append(item)
        return
    replace_idx = rng.randint(0, seen - 1)
    if replace_idx < limit:
        reservoir[replace_idx] = item


def _iter_rows(config: OpenSWEImportConfig) -> Iterator[dict[str, Any]]:
    if config.input_path:
        yield from _iter_local(Path(config.input_path))
        return
    if config.use_hf:
        yield from _iter_huggingface(config)
        return
    raise ValueError("Provide --input-path or pass --use-hf.")


def _iter_local(path: Path) -> Iterator[dict[str, Any]]:
    if path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.suffix.lower() in {".jsonl", ".json", ".parquet"}:
                yield from _iter_local(child)
        return
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)
        return
    if suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            for item in raw:
                yield item
        elif isinstance(raw, dict) and "rows" in raw and isinstance(raw["rows"], list):
            for item in raw["rows"]:
                yield item
        elif isinstance(raw, dict):
            yield raw
        return
    if suffix == ".parquet":
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError(
                "Reading parquet requires pyarrow. Install it or export the sample as JSONL."
            ) from exc
        table = pq.read_table(path)
        for row in table.to_pylist():
            yield row
        return
    raise ValueError(f"Unsupported input file: {path}")


def _iter_huggingface(config: OpenSWEImportConfig) -> Iterator[dict[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        del exc
        yield from _iter_huggingface_rows_api(config)
        return
    if config.hf_config:
        dataset = load_dataset(config.hf_dataset, config.hf_config, split=config.hf_split, streaming=True)
    else:
        dataset = load_dataset(config.hf_dataset, split=config.hf_split, streaming=True)
    for row in dataset:
        yield dict(row)


def _iter_huggingface_rows_api(config: OpenSWEImportConfig) -> Iterator[dict[str, Any]]:
    offset = 0
    source_limit = config.max_source_rows or config.limit
    page_size = min(50, max(1, source_limit))
    yielded = 0
    while yielded < source_limit:
        params = urllib.parse.urlencode(
            {
                "dataset": config.hf_dataset,
                "config": config.hf_config,
                "split": config.hf_split,
                "offset": offset,
                "length": min(page_size, source_limit - yielded),
            }
        )
        url = f"https://datasets-server.huggingface.co/rows?{params}"
        payload = _read_huggingface_rows_page(url)
        rows = payload.get("rows", [])
        if not rows:
            break
        for wrapped in rows:
            row = wrapped.get("row", wrapped)
            if isinstance(row, dict):
                yielded += 1
                yield row
                if yielded >= source_limit:
                    break
        offset += len(rows)


def _read_huggingface_rows_page(url: str, retries: int = 3) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except (http.client.IncompleteRead, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 >= retries:
                break
            time.sleep(2**attempt)
    assert last_error is not None
    raise last_error


def _convert_row(
    row: dict[str, Any],
    row_idx: int,
    config: OpenSWEImportConfig,
    rng: random.Random,
    base_time: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]] | None:
    repo = _clean_scalar(row.get("repo") or row.get("repository") or row.get("repo_name"))
    if not repo:
        repo = _repo_from_instance(_clean_scalar(row.get("instance_id"))) or f"unknown/repo_{row_idx:06d}"
    org_id = repo.split("/", 1)[0] if "/" in repo else "unknown_owner"
    project_id = repo
    workflow_id = _clean_scalar(row.get("trajectory_id")) or _clean_scalar(row.get("instance_id"))
    if not workflow_id:
        workflow_id = f"openswe_traj_{row_idx:06d}"

    messages = _trajectory_to_messages(row.get("trajectory"))
    if not messages:
        messages = _fallback_messages(row)
    if not messages:
        return None

    messages, repair_fields = _apply_repair_context(messages, repo, config.repair_mode)
    if config.synthetic_secret_rate > 0 and rng.random() < config.synthetic_secret_rate:
        messages = _add_synthetic_secret(messages)
        repair_fields.append("synthetic_secret")

    turn_indices = _turn_indices(messages, config.max_turns_per_trajectory)
    if not turn_indices:
        return None

    attack_rows: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    start = base_time + timedelta(minutes=row_idx * 17 + rng.randint(0, config.timestamp_jitter_minutes))
    profile_truth = _profile_truth(row, repo)

    for turn_id, end_idx in enumerate(turn_indices, start=1):
        request_id = f"openswe_req_{row_idx:07d}_{turn_id:03d}"
        context_messages = messages[: end_idx + 1]
        timestamp = start + timedelta(minutes=turn_id * rng.randint(2, 11))
        attack_row = {
            "request_id": request_id,
            "timestamp": _iso(timestamp),
            "model": _model_name(row),
            "messages": context_messages,
            "tool_schemas": _tool_schema_from_messages(context_messages),
            "token_count": _token_count(context_messages),
            "cache_bucket": None,
            "provider_metadata": {
                "api_surface": "chat_completions",
                "brokered": True,
                "stream": False,
            },
        }
        if config.include_provenance_in_attack_view:
            attack_row.update(
                {
                    "source": "open_swe_traces",
                    "repair_mode": config.repair_mode,
                    "repair_fields": repair_fields,
                }
            )
        attack_rows.append(attack_row)
        truth_rows.append(
            {
                "request_id": request_id,
                "org_id": org_id,
                "user_id": None,
                "project_id": project_id,
                "workflow_id": workflow_id,
                "turn_id": turn_id,
                "task_type": _task_type(row),
                "profile_truth": profile_truth,
            }
        )
        provenance_rows.append(
            {
                "request_id": request_id,
                "source": "open_swe_traces",
                "source_row_idx": row_idx,
                "repo": repo,
                "org_id": org_id,
                "project_id": project_id,
                "workflow_id": workflow_id,
                "turn_id": turn_id,
                "repair_mode": config.repair_mode,
                "repair_fields": repair_fields,
            }
        )
    return attack_rows, truth_rows, provenance_rows


def _trajectory_to_messages(value: Any) -> list[dict[str, str]]:
    value = _maybe_json(value)
    if value is None:
        return []
    if isinstance(value, dict):
        for key in ("messages", "trajectory", "history", "conversation"):
            if key in value:
                return _trajectory_to_messages(value[key])
        return [_message("user", _json_text(value))]
    if isinstance(value, str):
        return [_message("user", value)]
    if not isinstance(value, list):
        return [_message("user", str(value))]

    messages: list[dict[str, str]] = []
    for item in value:
        item = _maybe_json(item)
        if isinstance(item, str):
            messages.append(_message("user", item))
        elif isinstance(item, dict):
            messages.extend(_dict_to_messages(item))
        else:
            messages.append(_message("user", _json_text(item)))
    return _dedupe_empty(messages)


def _dict_to_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    if "role" in item and ("content" in item or "message" in item):
        role = _normalize_role(str(item.get("role") or "user"))
        content = _clean_scalar(item.get("content") if "content" in item else item.get("message"))
        name = _clean_scalar(item.get("name") or item.get("tool_name"))
        return [_message(role, content, name=name)]

    out: list[dict[str, str]] = []
    for key in ("system", "instruction"):
        if key in item:
            out.append(_message("system", _clean_scalar(item[key])))
    for key in ("problem_statement", "task", "prompt", "user"):
        if key in item:
            out.append(_message("user", _clean_scalar(item[key])))
    for key in ("thought", "assistant", "response", "action"):
        if key in item:
            out.append(_message("assistant", _clean_scalar(item[key])))
    for key in ("observation", "tool", "tool_output", "result"):
        if key in item:
            out.append(_message("tool", _clean_scalar(item[key]), name=_clean_scalar(item.get("tool_name"))))
    if out:
        return out
    return [_message("user", _json_text(item))]


def _fallback_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for key in ("problem_statement", "issue", "prompt", "instruction"):
        if row.get(key):
            messages.append(_message("user", _clean_scalar(row[key])))
    for key in ("model_patch", "patch", "test_patch"):
        if row.get(key):
            messages.append(_message("tool", _clean_scalar(row[key]), name=key))
    return messages


def _turn_indices(messages: list[dict[str, str]], max_turns: int) -> list[int]:
    candidates = [
        idx
        for idx, message in enumerate(messages)
        if idx > 0 and message.get("role") in {"assistant", "tool"}
    ]
    if not candidates and len(messages) > 1:
        candidates = list(range(1, len(messages)))
    if not candidates:
        return []
    if len(candidates) <= max_turns:
        return candidates
    step = len(candidates) / max_turns
    selected = [candidates[min(len(candidates) - 1, int(i * step))] for i in range(max_turns)]
    return sorted(set(selected))


def _apply_repair_context(
    messages: list[dict[str, str]], repo: str, repair_mode: str
) -> tuple[list[dict[str, str]], list[str]]:
    if repair_mode == "none":
        return [dict(message) for message in messages], []
    if repair_mode not in {"repository", "workspace", "repository_workspace"}:
        raise ValueError(f"unknown repair mode: {repair_mode}")

    repo_slug = repo.replace("/", "__")
    repaired = [dict(message) for message in messages]
    parts = ["[repair_context]"]
    fields: list[str] = []
    if repair_mode in {"repository", "repository_workspace"}:
        parts.append(f"repository={repo}")
        fields.append("repository")
    if repair_mode in {"workspace", "repository_workspace"}:
        parts.append(f"workspace=/workspace/{repo_slug}")
        parts.append(f"repo_slug={repo_slug}")
        fields.extend(["workspace", "repo_slug"])
    hint = "\n\n" + "; ".join(parts)
    for message in repaired:
        if message.get("role") == "user":
            message["content"] = message.get("content", "") + hint
            return repaired, fields
    repaired.insert(0, _message("user", hint.strip()))
    return repaired, fields


def _add_synthetic_secret(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    repaired = [dict(message) for message in messages]
    repaired[-1]["content"] = (
        repaired[-1].get("content", "")
        + "\nsynthetic_token=sk-test-11111111111111111111111111111111"
    )
    return repaired


def _profile_truth(row: dict[str, Any], repo: str) -> dict[str, list[str]]:
    language = _clean_scalar(row.get("language"))
    _, repo_name = (repo.split("/", 1) if "/" in repo else ("unknown_owner", repo))
    truth: dict[str, list[str]] = {
        "repo_names": [repo_name],
        "service_names": [repo_name],
    }
    if language:
        truth["languages"] = [language.lower()]
    text = json.dumps(row, sort_keys=True).lower()
    _add_profile_clues(truth, text)
    return truth


def _add_profile_clues(truth: dict[str, list[str]], text: str) -> None:
    clues = {
        "languages": {
            "python": ["python", ".py", "pytest", "pyproject.toml", "requirements.txt"],
            "javascript": ["javascript", ".js", "package.json", "npm"],
            "typescript": ["typescript", ".ts", "tsconfig.json", "pnpm"],
            "java": ["java", "pom.xml", "maven", "gradle"],
            "go": ["golang", "go test", "go.mod", ".go"],
            "rust": ["rust", "cargo.toml", ".rs"],
        },
        "package_managers": {
            "pip": ["requirements.txt", "pip install"],
            "poetry": ["poetry.lock", "pyproject.toml"],
            "npm": ["npm install", "package.json"],
            "pnpm": ["pnpm-lock.yaml", "pnpm "],
            "yarn": ["yarn.lock", "yarn "],
            "maven": ["pom.xml", "mvn "],
            "gradle": ["build.gradle", "gradle "],
            "go mod": ["go.mod", "go mod"],
            "cargo": ["cargo.toml", "cargo "],
        },
        "frameworks": {
            "pytest": ["pytest"],
            "django": ["django"],
            "flask": ["flask"],
            "react": ["react"],
            "nextjs": ["next.js", "nextjs"],
            "spring": ["spring"],
            "rails": ["rails"],
        },
        "build_tools": {
            "pytest": ["pytest"],
            "tox": ["tox.ini", "tox "],
            "make": ["makefile", "make "],
            "maven": ["mvn ", "pom.xml"],
            "gradle": ["gradle ", "build.gradle"],
            "go test": ["go test"],
            "cargo": ["cargo test", "cargo build"],
        },
        "ci_cd_systems": {
            "github_actions": [".github/workflows", "github actions"],
            "gitlab_ci": [".gitlab-ci.yml", "gitlab ci"],
            "jenkins": ["jenkinsfile", "jenkins"],
            "circleci": [".circleci", "circleci"],
        },
    }
    for field, values in clues.items():
        for value, needles in values.items():
            if any(needle in text for needle in needles):
                truth.setdefault(field, [])
                if value not in truth[field]:
                    truth[field].append(value)


def _tool_schema_from_messages(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    names = sorted({message.get("name") or "tool" for message in messages if message.get("role") == "tool"})
    return [{"name": name, "parameters": ["input"]} for name in names]


def _model_name(row: dict[str, Any]) -> str:
    metadata = _maybe_json(row.get("metadata"))
    if isinstance(metadata, dict):
        for key in ("model", "agent", "scaffold", "source"):
            if metadata.get(key):
                return str(metadata[key])
    for key in ("model", "agent", "scaffold", "source"):
        if row.get(key):
            return str(row[key])
    return "open_swe_trace_agent"


def _task_type(row: dict[str, Any]) -> str:
    if row.get("resolved") is not None:
        return "software_issue_resolution"
    if row.get("problem_statement"):
        return "software_issue"
    return "agent_trajectory"


def _repo_from_instance(instance_id: str | None) -> str | None:
    if not instance_id:
        return None
    if "__" in instance_id:
        left, right, *_ = instance_id.split("__")
        if left and right:
            return f"{left}/{right}"
    return None


def _message(role: str, content: str | None, name: str | None = None) -> dict[str, str]:
    message = {"role": _normalize_role(role), "content": content or ""}
    if name:
        message["name"] = name
    return message


def _normalize_role(role: str) -> str:
    role = role.lower()
    if role in {"system", "user", "assistant", "tool"}:
        return role
    if role in {"observation", "environment", "function"}:
        return "tool"
    if role in {"agent", "model"}:
        return "assistant"
    return "user"


def _dedupe_empty(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    return [message for message in messages if message.get("content", "").strip()]


def _maybe_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def _clean_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return _json_text(value)


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _token_count(messages: list[dict[str, str]]) -> int:
    return sum(len(message.get("content", "").split()) for message in messages)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Open-SWE-Traces into attack-view JSONL.")
    parser.add_argument("--input-path", type=str)
    parser.add_argument("--output-dir", type=str, default="artifacts/datasets/open_swe_traces_sample")
    parser.add_argument("--use-hf", action="store_true")
    parser.add_argument("--hf-dataset", default="nvidia/Open-SWE-Traces")
    parser.add_argument("--hf-config", default="default")
    parser.add_argument("--hf-split", default="train")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--sample-mode", choices=["first", "reservoir"], default="first")
    parser.add_argument("--max-source-rows", type=int)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-turns-per-trajectory", type=int, default=12)
    parser.add_argument(
        "--repair-mode",
        choices=["none", "repository", "workspace", "repository_workspace"],
        default="none",
    )
    parser.add_argument("--no-repaired-workspace-path", action="store_true")
    parser.add_argument("--synthetic-secret-rate", type=float, default=0.0)
    parser.add_argument("--include-provenance-in-attack-view", action="store_true")
    args = parser.parse_args()

    summary = import_open_swe_traces(
        OpenSWEImportConfig(
            input_path=args.input_path,
            output_dir=args.output_dir,
            hf_dataset=args.hf_dataset,
            hf_config=args.hf_config,
            hf_split=args.hf_split,
            use_hf=args.use_hf,
            limit=args.limit,
            sample_mode=args.sample_mode,
            max_source_rows=args.max_source_rows,
            seed=args.seed,
            max_turns_per_trajectory=args.max_turns_per_trajectory,
            repair_mode="none" if args.no_repaired_workspace_path else args.repair_mode,
            synthetic_secret_rate=args.synthetic_secret_rate,
            include_provenance_in_attack_view=args.include_provenance_in_attack_view,
        )
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
