from __future__ import annotations

import argparse
import json
import random
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from agent_privacy.io import write_json, write_jsonl


@dataclass(frozen=True)
class SWEWorkflowImportConfig:
    input_path: str | None = None
    output_dir: str = "artifacts/datasets/swe_repaired_sample"
    hf_dataset: str = "princeton-nlp/SWE-bench_Lite"
    hf_config: str | None = None
    hf_split: str = "test"
    use_hf: bool = False
    limit: int = 1000
    max_per_repo: int | None = None
    max_source_rows: int | None = None
    seed: int = 7
    timestamp_start: str = "2026-01-05T09:00:00Z"
    timestamp_jitter_minutes: int = 120
    repair_workspace: bool = False
    repair_context_mode: str = "repository"


def import_swe_workflows(config: SWEWorkflowImportConfig) -> dict[str, Any]:
    rng = random.Random(config.seed)
    base_time = datetime.fromisoformat(config.timestamp_start.replace("Z", "+00:00"))
    output_dir = Path(config.output_dir)
    attack_rows: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    source_rows = 0
    used_rows = 0
    repo_counts: dict[str, int] = {}

    source_scan_limit = _source_scan_limit(config)
    for row_idx, row in enumerate(_iter_rows(config)):
        if source_scan_limit is not None and source_rows >= source_scan_limit:
            break
        source_rows += 1
        if used_rows >= config.limit:
            break
        repo = _repo(row, row_idx)
        if config.max_per_repo is not None and repo_counts.get(repo, 0) >= config.max_per_repo:
            continue
        converted = _convert_row(row, row_idx, config, rng, base_time)
        if converted is None:
            continue
        repo_counts[repo] = repo_counts.get(repo, 0) + 1
        attack, truth, provenance = converted
        attack_rows.extend(attack)
        truth_rows.extend(truth)
        provenance_rows.extend(provenance)
        used_rows += 1

    joined = list(zip(attack_rows, truth_rows, provenance_rows, strict=True))
    joined.sort(key=lambda pair: (pair[0]["timestamp"], pair[0]["request_id"]))
    attack_rows = [pair[0] for pair in joined]
    truth_rows = [pair[1] for pair in joined]
    provenance_rows = [pair[2] for pair in joined]

    write_jsonl(output_dir / "attack_view.jsonl", attack_rows)
    write_jsonl(output_dir / "ground_truth.jsonl", truth_rows)
    write_jsonl(output_dir / "request_provenance.jsonl", provenance_rows)
    manifest = {
        "source": "swe_style_repaired_workflows",
        "config": asdict(config),
        "source_rows_seen": source_rows,
        "workflows_used": used_rows,
        "repos_used": len(repo_counts),
        "max_per_repo": config.max_per_repo,
        "max_source_rows": source_scan_limit,
        "requests": len(attack_rows),
        "truth": len(truth_rows),
        "provenance": len(provenance_rows),
        "notes": [
            "This importer builds repaired agent-like workflows from real issue/patch rows.",
            "It is not a raw agent trajectory dataset.",
            "Use it as independent real-repo validation, not as raw provider evidence.",
            "repair_context_mode controls whether explicit repository/workspace context is added.",
        ],
    }
    write_json(output_dir / "source_manifest.json", manifest)
    return {
        "source_rows_seen": source_rows,
        "workflows_used": used_rows,
        "repos_used": len(repo_counts),
        "requests": len(attack_rows),
        "truth": len(truth_rows),
        "output_dir": str(output_dir),
    }


def _source_scan_limit(config: SWEWorkflowImportConfig) -> int | None:
    if config.max_source_rows is not None:
        return config.max_source_rows
    if config.max_per_repo is not None:
        return config.limit * 20
    return config.limit


def _iter_rows(config: SWEWorkflowImportConfig) -> Iterator[dict[str, Any]]:
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
                yield from _iter_local_rows(child)
        return
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)
        return
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            for item in raw:
                yield item
        elif isinstance(raw, dict) and isinstance(raw.get("rows"), list):
            for item in raw["rows"]:
                yield item
        elif isinstance(raw, dict):
            yield raw
        return
    raise ValueError(f"Unsupported input file: {path}")


def _iter_huggingface(config: SWEWorkflowImportConfig) -> Iterator[dict[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError:
        yield from _iter_huggingface_rows_api(config)
        return
    kwargs: dict[str, Any] = {"split": config.hf_split, "streaming": True}
    if config.hf_config:
        dataset = load_dataset(config.hf_dataset, config.hf_config, **kwargs)
    else:
        dataset = load_dataset(config.hf_dataset, **kwargs)
    for row in dataset:
        yield dict(row)


def _iter_huggingface_rows_api(config: SWEWorkflowImportConfig) -> Iterator[dict[str, Any]]:
    source_scan_limit = _source_scan_limit(config)
    if source_scan_limit is None:
        raise ValueError("Hugging Face rows API requires a finite source scan limit.")
    offset = 0
    page_size = min(100, max(1, source_scan_limit))
    yielded = 0
    while yielded < source_scan_limit:
        params = {
            "dataset": config.hf_dataset,
            "split": config.hf_split,
            "offset": offset,
            "length": min(page_size, source_scan_limit - yielded),
        }
        if config.hf_config:
            params["config"] = config.hf_config
        query = urllib.parse.urlencode(params)
        url = f"https://datasets-server.huggingface.co/rows?{query}"
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = payload.get("rows", [])
        if not rows:
            break
        for wrapped in rows:
            row = wrapped.get("row", wrapped)
            if isinstance(row, dict):
                yielded += 1
                yield row
                if yielded >= source_scan_limit:
                    break
        offset += len(rows)


def _convert_row(
    row: dict[str, Any],
    row_idx: int,
    config: SWEWorkflowImportConfig,
    rng: random.Random,
    base_time: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]] | None:
    repo = _repo(row, row_idx)
    owner, repo_name = repo.split("/", 1) if "/" in repo else ("unknown_owner", repo)
    workflow_id = _string(row.get("instance_id") or row.get("id") or row.get("problem_id"))
    if not workflow_id:
        workflow_id = f"swe_workflow_{row_idx:07d}"
    problem = _string(
        row.get("problem_statement") or row.get("issue") or row.get("prompt") or row.get("task")
    )
    patch = _string(row.get("patch") or row.get("model_patch") or row.get("gold_patch"))
    test_patch = _string(row.get("test_patch") or row.get("tests_patch"))
    fail_to_pass = _list_text(row.get("FAIL_TO_PASS") or row.get("fail_to_pass"))
    pass_to_pass = _list_text(row.get("PASS_TO_PASS") or row.get("pass_to_pass"))
    if not any([problem, patch, test_patch, fail_to_pass, pass_to_pass]):
        return None

    messages_by_turn = _workflow_messages(
        repo=repo,
        problem=problem,
        patch=patch,
        test_patch=test_patch,
        fail_to_pass=fail_to_pass,
        pass_to_pass=pass_to_pass,
        repair_context_mode=_repair_context_mode(config),
    )
    start = base_time + timedelta(minutes=row_idx * 13 + rng.randint(0, config.timestamp_jitter_minutes))
    profile_truth = _profile_truth(row, repo_name)
    attack_rows: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    cumulative: list[dict[str, str]] = []
    for turn_id, turn_messages in enumerate(messages_by_turn, start=1):
        cumulative.extend(turn_messages)
        request_id = f"swe_req_{row_idx:07d}_{turn_id:03d}"
        timestamp = start + timedelta(minutes=turn_id * rng.randint(3, 12))
        attack_rows.append(
            {
                "request_id": request_id,
                "timestamp": _iso(timestamp),
                "model": "swe-repaired-agent",
                "messages": list(cumulative),
                "tool_schemas": [{"name": "shell", "parameters": ["cmd", "cwd"]}],
                "token_count": _token_count(cumulative),
                "cache_bucket": None,
                "provider_metadata": {
                    "api_surface": "chat_completions",
                    "brokered": True,
                },
            }
        )
        truth_rows.append(
            {
                "request_id": request_id,
                "org_id": owner,
                "user_id": None,
                "project_id": repo,
                "workflow_id": workflow_id,
                "turn_id": turn_id,
                "task_type": "swe_issue_repair",
                "profile_truth": profile_truth,
            }
        )
        provenance_rows.append(
            {
                "request_id": request_id,
                "source": "swe_style_repaired_workflows",
                "source_row_idx": row_idx,
                "repo": repo,
                "workflow_id": workflow_id,
                "turn_id": turn_id,
                "repair_workspace": config.repair_workspace,
                "repair_context_mode": _repair_context_mode(config),
                "source_view": "swe_repaired_workflow",
            }
        )
    return attack_rows, truth_rows, provenance_rows


def _workflow_messages(
    repo: str,
    problem: str,
    patch: str,
    test_patch: str,
    fail_to_pass: str,
    pass_to_pass: str,
    repair_context_mode: str,
) -> list[list[dict[str, str]]]:
    workspace = f"/workspace/{repo.replace('/', '__')}"
    context = ""
    if repair_context_mode == "repository":
        context = f"\n\n[repair_context] repository={repo}"
    elif repair_context_mode == "workspace":
        context = f"\n\n[repair_context] workspace={workspace}"
    elif repair_context_mode == "repository_workspace":
        context = f"\n\n[repair_context] repository={repo}; workspace={workspace}"
    elif repair_context_mode == "natural":
        context = ""
    else:
        raise ValueError(f"unknown repair_context_mode: {repair_context_mode}")
    problem_text = (problem or "Repair the failing issue in this repository.") + context
    test_text = "\n".join(part for part in [fail_to_pass, pass_to_pass] if part) or "Run focused tests."
    patch_text = patch or "No patch text was provided in the source row."
    test_patch_text = test_patch or "No test patch was provided in the source row."
    return [
        [
            {"role": "system", "content": "You are an LLM coding agent. Keep changes scoped."},
            {"role": "user", "content": problem_text},
        ],
        [
            {
                "role": "assistant",
                "content": "I will inspect the failing tests and relevant files before editing.",
            },
            {"role": "tool", "name": "shell", "content": f"$ pytest\n{test_text}"},
        ],
        [
            {"role": "assistant", "content": "I found the likely fix and will apply a minimal patch."},
            {"role": "tool", "name": "patch", "content": patch_text[:20_000]},
        ],
        [
            {"role": "assistant", "content": "I will update or verify regression tests."},
            {"role": "tool", "name": "patch", "content": test_patch_text[:20_000]},
        ],
    ]


def _repo(row: dict[str, Any], row_idx: int) -> str:
    value = _string(row.get("repo") or row.get("repository") or row.get("repo_name"))
    if value:
        return value
    instance = _string(row.get("instance_id"))
    if "__" in instance:
        owner, repo = instance.split("__", 1)
        return f"{owner}/{repo.split('-', 1)[0]}"
    return f"unknown_owner/unknown_repo_{row_idx:07d}"


def _repair_context_mode(config: SWEWorkflowImportConfig) -> str:
    if config.repair_workspace and config.repair_context_mode == "repository":
        return "repository_workspace"
    return config.repair_context_mode


def _profile_truth(row: dict[str, Any], repo_name: str) -> dict[str, list[str]]:
    truth: dict[str, list[str]] = {
        "repo_names": [repo_name],
        "service_names": [repo_name],
    }
    language = _string(row.get("language"))
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


def _string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _list_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(_string(item) for item in value if _string(item))
    return _string(value)


def _token_count(messages: list[dict[str, Any]]) -> int:
    return sum(len(str(message.get("content", "")).split()) for message in messages)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import SWE-style rows as repaired workflows.")
    parser.add_argument("--input-path")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--use-hf", action="store_true")
    parser.add_argument("--hf-dataset", default="princeton-nlp/SWE-bench_Lite")
    parser.add_argument("--hf-config")
    parser.add_argument("--hf-split", default="test")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--max-per-repo", type=int)
    parser.add_argument("--max-source-rows", type=int)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--repair-workspace", action="store_true")
    parser.add_argument(
        "--repair-context-mode",
        choices=["repository", "workspace", "repository_workspace", "natural"],
        default="repository",
    )
    args = parser.parse_args()
    summary = import_swe_workflows(
        SWEWorkflowImportConfig(
            input_path=args.input_path,
            output_dir=args.output_dir,
            hf_dataset=args.hf_dataset,
            hf_config=args.hf_config,
            hf_split=args.hf_split,
            use_hf=args.use_hf,
            limit=args.limit,
            max_per_repo=args.max_per_repo,
            max_source_rows=args.max_source_rows,
            seed=args.seed,
            repair_workspace=args.repair_workspace,
            repair_context_mode=args.repair_context_mode,
        )
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
