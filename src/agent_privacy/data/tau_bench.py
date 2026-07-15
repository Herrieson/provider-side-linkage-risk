from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from agent_privacy.io import write_json, write_jsonl


ENTITY_RE = re.compile(
    r"\b(?:user|customer|account|order|reservation|booking|flight|product|item|ticket)[_-]?"
    r"[A-Za-z0-9-]{3,}\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TauBenchImportConfig:
    input_path: str | None = None
    output_dir: str = "artifacts/datasets/tau_bench_adapted"
    hf_dataset: str = "sierra-research/tau-bench"
    hf_config: str | None = None
    hf_split: str = "train"
    use_hf: bool = False
    limit: int = 500
    seed: int = 7
    timestamp_start: str = "2026-02-01T09:00:00Z"
    inter_turn_seconds: int = 45
    workflow_spacing_minutes: int = 5
    max_turns_per_workflow: int | None = None


def import_tau_bench(config: TauBenchImportConfig) -> dict[str, Any]:
    rng = random.Random(config.seed)
    output_dir = Path(config.output_dir)
    base_time = datetime.fromisoformat(config.timestamp_start.replace("Z", "+00:00"))
    attack_rows: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    source_rows_seen = 0
    workflows_used = 0

    for row_idx, source_row in enumerate(_iter_rows(config), start=1):
        source_rows_seen += 1
        if workflows_used >= config.limit:
            break
        trajectory = _extract_trajectory(source_row)
        if not trajectory:
            continue
        domain = _domain(source_row, row_idx)
        task_id = _task_id(source_row, row_idx)
        user_id = _user_id(source_row, task_id)
        workflow_id = f"tau_{domain}_{task_id}"
        workflow_start = base_time + timedelta(minutes=config.workflow_spacing_minutes * workflows_used)
        converted = _convert_trajectory(
            trajectory=trajectory,
            source_row=source_row,
            workflow_id=workflow_id,
            task_id=task_id,
            domain=domain,
            user_id=user_id,
            workflow_index=workflows_used + 1,
            workflow_start=workflow_start,
            config=config,
            rng=rng,
        )
        if not converted:
            continue
        attacks, truth, provenance = converted
        attack_rows.extend(attacks)
        truth_rows.extend(truth)
        provenance_rows.extend(provenance)
        workflows_used += 1

    joined = list(zip(attack_rows, truth_rows, provenance_rows, strict=True))
    joined.sort(key=lambda item: (item[0]["timestamp"], item[0]["request_id"]))
    attack_rows = [item[0] for item in joined]
    truth_rows = [item[1] for item in joined]
    provenance_rows = [item[2] for item in joined]

    write_jsonl(output_dir / "attack_view.jsonl", attack_rows)
    write_jsonl(output_dir / "ground_truth.jsonl", truth_rows)
    write_jsonl(output_dir / "request_provenance.jsonl", provenance_rows)
    manifest = {
        "dataset": "tau-bench adapted",
        "dataset_type": "heterogeneous_non_code_tool_agent",
        "config": asdict(config),
        "source_rows_seen": source_rows_seen,
        "workflows_used": workflows_used,
        "requests": len(attack_rows),
        "truth": len(truth_rows),
        "provenance": len(provenance_rows),
        "domains": sorted({row["org_id"] for row in truth_rows}),
        "notes": [
            "Converts non-code tool-agent trajectories into the common provider-view schema.",
            "Each attack_view row represents the cumulative messages visible before an assistant/agent turn.",
            "Ground-truth task/session/domain/entity labels are stored only in ground_truth/provenance.",
            "Use a real tau-bench trajectory export or Hugging Face rows before reporting paper results.",
        ],
    }
    write_json(output_dir / "source_manifest.json", manifest)
    return {
        "source_rows_seen": source_rows_seen,
        "workflows_used": workflows_used,
        "requests": len(attack_rows),
        "truth": len(truth_rows),
        "output_dir": str(output_dir),
    }


def _iter_rows(config: TauBenchImportConfig) -> Iterator[dict[str, Any]]:
    if config.input_path:
        yield from _iter_local_rows(Path(config.input_path))
        return
    if config.use_hf:
        yield from _iter_huggingface(config)
        return
    raise ValueError("Provide --input-path or pass --use-hf.")


def _iter_local_rows(path: Path) -> Iterator[dict[str, Any]]:
    if path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.suffix.lower() in {".jsonl", ".json"}:
                for row in _iter_local_rows(child):
                    row.setdefault("_source_file", str(child))
                    yield row
        return
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    if isinstance(row, dict):
                        yield row
        return
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        yield from _rows_from_json_payload(payload)
        return
    raise ValueError(f"Unsupported input file: {path}")


def _rows_from_json_payload(payload: Any) -> Iterator[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return
    if not isinstance(payload, dict):
        return
    for key in ["rows", "data", "tasks", "trajectories", "examples"]:
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield item
            return
    yield payload


def _iter_huggingface(config: TauBenchImportConfig) -> Iterator[dict[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Install the datasets package or provide --input-path.") from exc
    kwargs: dict[str, Any] = {"split": config.hf_split, "streaming": True}
    if config.hf_config:
        dataset = load_dataset(config.hf_dataset, config.hf_config, **kwargs)
    else:
        dataset = load_dataset(config.hf_dataset, **kwargs)
    for row in dataset:
        yield dict(row)


def _convert_trajectory(
    *,
    trajectory: list[dict[str, Any]],
    source_row: dict[str, Any],
    workflow_id: str,
    task_id: str,
    domain: str,
    user_id: str,
    workflow_index: int,
    workflow_start: datetime,
    config: TauBenchImportConfig,
    rng: random.Random,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]] | None:
    attacks: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    cumulative: list[dict[str, Any]] = []
    tool_schemas = _tool_schemas(source_row, trajectory)
    max_turns = config.max_turns_per_workflow or 10_000
    request_turn = 0
    for event_index, event in enumerate(trajectory, start=1):
        message = _message_from_event(event)
        if message is None:
            continue
        role = message["role"]
        if role in {"assistant", "agent"}:
            if cumulative and request_turn < max_turns:
                request_turn += 1
                request_id = f"tau_req_{workflow_index:06d}_{request_turn:03d}"
                timestamp = workflow_start + timedelta(
                    seconds=config.inter_turn_seconds * (request_turn - 1)
                    + rng.randint(0, max(1, config.inter_turn_seconds // 3))
                )
                messages = [_system_message(domain, source_row), *cumulative]
                attack_row = {
                    "request_id": request_id,
                    "timestamp": _format_timestamp(timestamp),
                    "model": str(source_row.get("model") or "tau_bench_trace_agent"),
                    "messages": messages,
                    "tool_schemas": tool_schemas,
                    "token_count": _token_count(messages),
                    "cache_bucket": _cache_bucket(domain, source_row),
                    "provider_metadata": {
                        "api_surface": "chat_completions",
                        "brokered": True,
                        "stream": False,
                    },
                }
                attacks.append(attack_row)
                entity_ids = sorted(_entity_ids(source_row, cumulative))
                truth_rows.append(
                    {
                        "request_id": request_id,
                        "org_id": domain,
                        "user_id": user_id,
                        "project_id": f"{domain}:{_primary_entity(entity_ids, task_id)}",
                        "workflow_id": workflow_id,
                        "turn_id": request_turn,
                        "task_type": f"tau_bench_{domain}",
                        "profile_truth": {
                            "domains": [domain],
                            "business_entities": entity_ids[:8],
                            "tool_names": _schema_names(tool_schemas),
                            "policy_markers": _policy_markers(source_row),
                        },
                    }
                )
                provenance_rows.append(
                    {
                        "request_id": request_id,
                        "source": "tau_bench",
                        "source_task_id": task_id,
                        "source_domain": domain,
                        "source_event_index": event_index,
                        "source_workflow_id": workflow_id,
                        "conversion": "cumulative_provider_view_before_agent_turn",
                    }
                )
        cumulative.append(message)
    if not attacks:
        return None
    return attacks, truth_rows, provenance_rows


def _extract_trajectory(row: dict[str, Any]) -> list[dict[str, Any]]:
    for key in [
        "trajectory",
        "traj",
        "trajectories",
        "messages",
        "conversation",
        "turns",
        "history",
        "log",
    ]:
        value = row.get(key)
        if isinstance(value, str):
            value = _parse_jsonish(value)
        if isinstance(value, list):
            events = [_event_dict(item) for item in value]
            return [event for event in events if event]
    prompt = row.get("prompt") or row.get("instruction") or row.get("task")
    if prompt:
        return [{"role": "user", "content": str(prompt)}, {"role": "assistant", "content": ""}]
    return []


def _event_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return {"role": "user", "content": value}
    return {}


def _message_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    role = _role(event)
    content = _content(event)
    name = event.get("name") or event.get("tool_name") or event.get("function")
    if role in {"tool", "function"} and name:
        return {"role": "tool", "name": str(name), "content": content}
    if not content and role != "assistant":
        return None
    return {"role": "assistant" if role == "agent" else role, "content": content}


def _role(event: dict[str, Any]) -> str:
    raw = str(
        event.get("role")
        or event.get("speaker")
        or event.get("from")
        or event.get("type")
        or event.get("kind")
        or "user"
    ).lower()
    if raw in {"assistant", "agent", "model"}:
        return "assistant"
    if raw in {"tool", "function", "action", "observation"}:
        return "tool"
    if raw in {"system", "developer"}:
        return "system"
    return "user"


def _content(event: dict[str, Any]) -> str:
    for key in ["content", "message", "text", "utterance", "observation", "result", "response"]:
        value = event.get(key)
        if value is not None:
            return _stringify(value)
    if event.get("tool_call") is not None:
        return _stringify(event["tool_call"])
    if event.get("action") is not None:
        return _stringify(event["action"])
    return ""


def _tool_schemas(row: dict[str, Any], trajectory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for key in ["tool_schemas", "tools", "functions", "apis"]:
        value = row.get(key)
        if isinstance(value, str):
            value = _parse_jsonish(value)
        if isinstance(value, list) and value:
            return [_schema_from_value(item) for item in value]
    names = []
    for event in trajectory:
        name = event.get("tool_name") or event.get("name") or event.get("function")
        if name:
            names.append(str(name))
    return [{"name": name, "parameters": []} for name in sorted(set(names))]


def _schema_from_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        name = str(value.get("name") or value.get("tool_name") or value.get("function") or "tool")
        params = value.get("parameters") or value.get("args") or value.get("properties") or []
        if isinstance(params, dict):
            params = sorted(str(key) for key in params)
        elif not isinstance(params, list):
            params = []
        return {"name": name, "parameters": [str(item) for item in params]}
    return {"name": str(value), "parameters": []}


def _schema_names(schemas: list[dict[str, Any]]) -> list[str]:
    return sorted({str(schema.get("name")) for schema in schemas if schema.get("name")})


def _system_message(domain: str, row: dict[str, Any]) -> dict[str, str]:
    policy = row.get("policy") or row.get("policies") or row.get("instruction") or row.get("task")
    content = f"You are a tool-using customer-service agent for the {domain} domain."
    if policy:
        content += f"\nPolicy context: {_stringify(policy)[:3000]}"
    return {"role": "system", "content": content}


def _entity_ids(row: dict[str, Any], messages: list[dict[str, Any]]) -> set[str]:
    text = _stringify(row)
    text += "\n" + "\n".join(str(message.get("content", "")) for message in messages)
    return {match.group(0).lower() for match in ENTITY_RE.finditer(text)}


def _policy_markers(row: dict[str, Any]) -> list[str]:
    text = _stringify(row.get("policy") or row.get("policies") or row.get("instruction") or "")
    markers = []
    for word in ["refund", "cancel", "exchange", "address", "payment", "flight", "order"]:
        if word in text.lower():
            markers.append(word)
    return markers


def _primary_entity(entity_ids: list[str], fallback: str) -> str:
    return entity_ids[0] if entity_ids else fallback


def _domain(row: dict[str, Any], row_idx: int) -> str:
    source_file = str(row.get("_source_file") or "").lower()
    value = (
        row.get("domain")
        or row.get("environment")
        or row.get("env")
        or row.get("category")
        or row.get("task_type")
        or ("airline" if "airline" in source_file else None)
        or ("retail" if "retail" in source_file else None)
        or "tau_domain"
    )
    domain = str(value).lower().strip().replace("/", "_").replace(" ", "_")
    return domain or f"tau_domain_{row_idx:03d}"


def _task_id(row: dict[str, Any], row_idx: int) -> str:
    value = row.get("task_id") or row.get("id") or row.get("episode_id") or row.get("trajectory_id")
    task_id = str(value).strip() if value is not None else ""
    source_file = Path(str(row.get("_source_file") or "source")).stem
    prefix = _safe_id(source_file)
    trial = row.get("trial")
    suffix = f":trial_{_safe_id(str(trial))}" if trial is not None else ""
    return f"{prefix}:{_safe_id(task_id)}{suffix}" if task_id else f"{prefix}:task_{row_idx:07d}{suffix}"


def _user_id(row: dict[str, Any], task_id: str) -> str:
    info = row.get("info") if isinstance(row.get("info"), dict) else {}
    task = info.get("task") if isinstance(info.get("task"), dict) else {}
    value = (
        row.get("user_id")
        or row.get("customer_id")
        or row.get("account_id")
        or task.get("user_id")
    )
    if value is not None and str(value).strip():
        return _safe_id(str(value))
    entities = sorted(_entity_ids(row, []))
    for entity in entities:
        if entity.startswith(("user", "customer", "account")):
            return _safe_id(entity)
    return f"tau_user_{task_id}"


def _cache_bucket(domain: str, row: dict[str, Any]) -> str:
    source_file = _safe_id(Path(str(row.get("_source_file") or domain)).stem)
    tenant = row.get("tenant") or row.get("organization") or source_file or domain
    return f"tau:{domain}:{_safe_id(str(tenant))}"


def _token_count(messages: list[dict[str, Any]]) -> int:
    return sum(len(str(message.get("content", "")).split()) for message in messages)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_id(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.:-]+", "_", value.strip())
    return value[:120] or "unknown"


def _parse_jsonish(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert tau-bench trajectories to provider-view rows.")
    parser.add_argument("--input-path", type=str)
    parser.add_argument("--output-dir", type=str, default="artifacts/datasets/tau_bench_adapted")
    parser.add_argument("--use-hf", action="store_true")
    parser.add_argument("--hf-dataset", type=str, default="sierra-research/tau-bench")
    parser.add_argument("--hf-config", type=str)
    parser.add_argument("--hf-split", type=str, default="train")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--timestamp-start", type=str, default="2026-02-01T09:00:00Z")
    parser.add_argument("--inter-turn-seconds", type=int, default=45)
    parser.add_argument("--workflow-spacing-minutes", type=int, default=5)
    parser.add_argument("--max-turns-per-workflow", type=int)
    args = parser.parse_args()
    config = TauBenchImportConfig(
        input_path=args.input_path,
        output_dir=args.output_dir,
        hf_dataset=args.hf_dataset,
        hf_config=args.hf_config,
        hf_split=args.hf_split,
        use_hf=args.use_hf,
        limit=args.limit,
        seed=args.seed,
        timestamp_start=args.timestamp_start,
        inter_turn_seconds=args.inter_turn_seconds,
        workflow_spacing_minutes=args.workflow_spacing_minutes,
        max_turns_per_workflow=args.max_turns_per_workflow,
    )
    print(json.dumps(import_tau_bench(config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
