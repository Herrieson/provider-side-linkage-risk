from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from agent_privacy.features.extract import request_text
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


LEVELS = ["user", "project", "org"]
TRUTH_FIELDS = {
    "user": "user_id",
    "project": "project_id",
    "org": "org_id",
}
OVERLAYS = [
    {
        "overlay_level": "U3",
        "dataset_base": Path("artifacts/datasets/open_swe_user_overlay_u3_mixed_1000"),
        "snapshot_base": Path("artifacts/datasets/open_swe_user_overlay_u3_mixed_1000_snapshots"),
        "result_prefix": Path("results/open_swe_user_overlay_u3"),
    },
    {
        "overlay_level": "U4",
        "dataset_base": Path("artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000"),
        "snapshot_base": Path("artifacts/datasets/open_swe_user_overlay_u4_hard_shared_1000_snapshots"),
        "result_prefix": Path("results/open_swe_user_overlay_u4"),
    },
]

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/@-]{2,}")
HOME_RE = re.compile(r"/(?:home|users)/[A-Za-z0-9_.-]+", re.IGNORECASE)
PATH_RE = re.compile(r"/(?:home|users|workspace|tmp|srv|opt)/[A-Za-z0-9_./-]+", re.IGNORECASE)
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:internal|local|prod|corp)\b", re.IGNORECASE)
COMMAND_RE = re.compile(r"\b(?:pytest|npm|pnpm|yarn|go|mvn|cargo|ruff|tox|gradle)\b[^\n;|&]{0,80}")
SERVICE_RE = re.compile(r"\b[a-z][a-z0-9-]+-(?:api|svc|engine|worker|service|backend|frontend)\b")
MAX_TEXT_HEAD_CHARS = 6_000
MAX_TEXT_TAIL_CHARS = 18_000
MAX_TOKENS_PER_ROW = 700
MAX_TOKENS_PER_TARGET = 32
MIN_TRAIN_REQUESTS = 2
TOP_K = 50
STOP_TOKENS = {
    "assistant",
    "content",
    "false",
    "function",
    "github",
    "messages",
    "method",
    "model",
    "none",
    "openhands",
    "parameters",
    "request",
    "role",
    "system",
    "true",
    "user",
    "workspace",
}
MARKER_TERMS = (
    "environment summary:",
    "command trace:",
    "service context:",
    "cwd=",
    "cache_root=",
    "runner_home=",
    "shell_history=",
    "preferred_check=",
    "package_manager=",
    "service=",
    "domain=",
    "build=",
    ".corp.local",
    ".prod.internal",
    "/workspace/",
    "/home/",
    "/users/",
)


def summarize_warm_start_retrieval(
    output_dir: Path,
    snapshot_pairs: list[tuple[int, int]] | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    snapshot_pairs = snapshot_pairs or [(1000, 4000)]
    for overlay in OVERLAYS:
        for train_count, test_count in snapshot_pairs:
            train_dataset = overlay["snapshot_base"] / f"first_{train_count}_requests"
            test_dataset = overlay["snapshot_base"] / f"first_{test_count}_requests"
            train_result = Path(
                f"{overlay['result_prefix']}_first_{train_count}_provider_lowcost_streamed"
            )
            predictions_path = train_result / "M0" / "predictions.json"
            if not train_dataset.exists() or not test_dataset.exists():
                continue
            rows.extend(
                _summarize_pair(
                    overlay_level=str(overlay["overlay_level"]),
                    train_count=train_count,
                    test_count=test_count,
                    train_dataset=train_dataset,
                    test_dataset=test_dataset,
                    dataset_base=overlay["dataset_base"],
                    predictions_path=predictions_path if predictions_path.exists() else None,
                )
            )
    csv_path = output_dir / "open_swe_user_overlay_warm_start_retrieval.csv"
    md_path = output_dir / "open_swe_user_overlay_warm_start_retrieval.md"
    headers = [
        "overlay_level",
        "train_snapshot",
        "test_snapshot",
        "truth_level",
        "watchlist_source",
        "train_requests",
        "new_requests",
        "targets",
        "targets_with_future",
        "watch_tokens",
        "scored_pairs",
        "pair_candidate_reduction",
        "retrieved_at_50",
        "correct_at_50",
        "precision_at_50",
        "recall_at_50",
        "hit_at_50",
        "mean_tokens_per_target",
    ]
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows, headers)
    return {"warm_start_retrieval": str(csv_path), "rows": str(len(rows))}


def _summarize_pair(
    *,
    overlay_level: str,
    train_count: int,
    test_count: int,
    train_dataset: Path,
    test_dataset: Path,
    dataset_base: Path,
    predictions_path: Path | None,
) -> list[dict[str, Any]]:
    train_rows = read_jsonl(train_dataset / "attack_view.jsonl")
    train_truth = read_jsonl(train_dataset / "ground_truth.jsonl")
    test_rows_all = read_jsonl(test_dataset / "attack_view.jsonl")
    test_truth_all = read_jsonl(test_dataset / "ground_truth.jsonl")
    train_ids = {row["request_id"] for row in train_rows}
    test_rows = [row for row in test_rows_all if row["request_id"] not in train_ids]
    test_truth = [row for row in test_truth_all if row["request_id"] not in train_ids]
    train_tokens = _row_tokens(train_rows)
    test_tokens = _row_tokens(test_rows)
    profiles = _read_profiles(dataset_base)
    predictions = _read_predictions(predictions_path)

    out: list[dict[str, Any]] = []
    for level in LEVELS:
        truth_field = TRUTH_FIELDS[level]
        watchlists = {
            "truth_text": _truth_text_watchlist(
                train_rows, train_truth, truth_field, train_tokens
            ),
            "profile_truth": _profile_truth_watchlist(level, profiles),
        }
        predicted_labels = predictions.get(level, {})
        if predicted_labels:
            watchlists["predicted_cluster"] = _predicted_cluster_watchlist(
                train_rows,
                train_truth,
                truth_field,
                train_tokens,
                predicted_labels,
            )
        for source, watchlist in watchlists.items():
            result = _score_retrieval(watchlist, test_rows, test_truth, truth_field, test_tokens)
            out.append(
                {
                    "overlay_level": overlay_level,
                    "train_snapshot": f"first_{train_count}_requests",
                    "test_snapshot": f"first_{test_count}_requests",
                    "truth_level": level,
                    "watchlist_source": source,
                    "train_requests": len(train_rows),
                    "new_requests": len(test_rows),
                    **result,
                }
            )
    return out


def _truth_text_watchlist(
    rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    truth_field: str,
    row_tokens: dict[str, set[str]],
) -> dict[str, dict[str, Any]]:
    truth_by_id = {row["request_id"]: row for row in truth_rows}
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        value = truth_by_id.get(row["request_id"], {}).get(truth_field)
        if value is not None:
            groups[str(value)].append(row["request_id"])
    return _build_group_watchlist(groups, row_tokens, len(rows))


def _predicted_cluster_watchlist(
    rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
    truth_field: str,
    row_tokens: dict[str, set[str]],
    labels: dict[str, str],
) -> dict[str, dict[str, Any]]:
    truth_by_id = {row["request_id"]: row for row in truth_rows}
    request_ids = {row["request_id"] for row in rows}
    cluster_requests: dict[str, list[str]] = defaultdict(list)
    cluster_truth_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for request_id, cluster_id in labels.items():
        if request_id not in request_ids:
            continue
        cluster_requests[cluster_id].append(request_id)
        value = truth_by_id.get(request_id, {}).get(truth_field)
        if value is not None:
            cluster_truth_counts[cluster_id][str(value)] += 1

    groups: dict[str, list[str]] = {}
    for cluster_id, request_ids_in_cluster in cluster_requests.items():
        counter = cluster_truth_counts.get(cluster_id)
        if not counter:
            continue
        target = counter.most_common(1)[0][0]
        key = f"{target}@@cluster:{cluster_id}"
        groups[key] = request_ids_in_cluster

    watchlist = _build_group_watchlist(groups, row_tokens, len(rows))
    collapsed: dict[str, dict[str, Any]] = {}
    for key, item in watchlist.items():
        target = key.split("@@cluster:", 1)[0]
        existing = collapsed.get(target)
        if existing is None or item["train_requests"] > existing["train_requests"]:
            item = dict(item)
            item["target_id"] = target
            collapsed[target] = item
    return collapsed


def _profile_truth_watchlist(level: str, profiles: dict[str, Any]) -> dict[str, dict[str, Any]]:
    section = {"user": "users", "project": "projects", "org": "orgs"}[level]
    out: dict[str, dict[str, Any]] = {}
    for target_id, profile in profiles.get(section, {}).items():
        tokens = _profile_tokens(profile)
        if not tokens:
            continue
        out[str(target_id)] = {
            "target_id": str(target_id),
            "tokens": [
                {"token": token, "score": 10.0, "cluster_count": 1, "global_df": 1}
                for token in sorted(tokens)[:MAX_TOKENS_PER_TARGET]
            ],
            "train_requests": 0,
        }
    return out


def _build_group_watchlist(
    groups: dict[str, list[str]],
    row_tokens: dict[str, set[str]],
    train_size: int,
) -> dict[str, dict[str, Any]]:
    token_docs: dict[str, set[str]] = defaultdict(set)
    for request_id, tokens in row_tokens.items():
        for token in tokens:
            token_docs[token].add(request_id)

    watchlist: dict[str, dict[str, Any]] = {}
    for target_id, request_ids in groups.items():
        if len(request_ids) < MIN_TRAIN_REQUESTS:
            continue
        counts: Counter[str] = Counter()
        for request_id in request_ids:
            counts.update(row_tokens.get(request_id, set()))
        scored = []
        group_size = max(1, len(request_ids))
        for token, count in counts.items():
            df = len(token_docs.get(token, set()))
            if not df:
                continue
            min_count = 1 if group_size <= 3 else 2
            if count < min_count:
                continue
            score = (count / group_size) * (train_size / df)
            scored.append((score, count, df, token))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
        tokens = [
            {"token": token, "score": round(score, 6), "cluster_count": count, "global_df": df}
            for score, count, df, token in scored[:MAX_TOKENS_PER_TARGET]
        ]
        if tokens:
            watchlist[target_id] = {
                "target_id": target_id,
                "tokens": tokens,
                "train_requests": group_size,
            }
    return watchlist


def _score_retrieval(
    watchlist: dict[str, dict[str, Any]],
    test_rows: list[dict[str, Any]],
    test_truth: list[dict[str, Any]],
    truth_field: str,
    test_tokens: dict[str, set[str]],
) -> dict[str, Any]:
    truth_by_id = {row["request_id"]: row for row in test_truth}
    test_request_ids = [row["request_id"] for row in test_rows]
    token_to_requests: dict[str, set[str]] = defaultdict(set)
    for request_id, tokens in test_tokens.items():
        for token in tokens:
            token_to_requests[token].add(request_id)

    targets = sorted(watchlist)
    targets_with_future = 0
    future_positives = 0
    scored_pairs = 0
    retrieved_at_k = 0
    correct_at_k = 0
    hits = 0

    for target_id in targets:
        positives = {
            request_id
            for request_id in test_request_ids
            if str(truth_by_id.get(request_id, {}).get(truth_field)) == target_id
        }
        if positives:
            targets_with_future += 1
            future_positives += len(positives)
        scores: Counter[str] = Counter()
        for token_info in watchlist[target_id].get("tokens", []):
            token = token_info["token"]
            score = float(token_info["score"])
            for request_id in token_to_requests.get(token, set()):
                scores[request_id] += score
        scored_pairs += len(scores)
        ranked = [
            request_id
            for request_id, _score in sorted(
                scores.items(), key=lambda item: (-item[1], item[0])
            )[:TOP_K]
        ]
        retrieved_at_k += len(ranked)
        correct = sum(1 for request_id in ranked if request_id in positives)
        correct_at_k += correct
        if correct:
            hits += 1

    total_pairs = len(targets) * len(test_rows)
    precision = correct_at_k / retrieved_at_k if retrieved_at_k else 0.0
    recall = correct_at_k / future_positives if future_positives else 0.0
    return {
        "targets": len(targets),
        "targets_with_future": targets_with_future,
        "watch_tokens": sum(len(item.get("tokens", [])) for item in watchlist.values()),
        "scored_pairs": scored_pairs,
        "pair_candidate_reduction": round(total_pairs / scored_pairs, 3) if scored_pairs else 0.0,
        "retrieved_at_50": retrieved_at_k,
        "correct_at_50": correct_at_k,
        "precision_at_50": round(precision, 3),
        "recall_at_50": round(recall, 3),
        "hit_at_50": round(hits / targets_with_future, 3) if targets_with_future else 0.0,
        "mean_tokens_per_target": round(
            sum(len(item.get("tokens", [])) for item in watchlist.values()) / len(targets), 2
        )
        if targets
        else 0.0,
    }


def _row_tokens(rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    return {row["request_id"]: _provider_tokens(row) for row in rows}


def _provider_tokens(row: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    text = request_text(row)
    scoped_text = text[:MAX_TEXT_HEAD_CHARS] + "\n" + text[-MAX_TEXT_TAIL_CHARS:]
    lower = scoped_text.lower()
    for regex in [HOME_RE, PATH_RE, DOMAIN_RE, COMMAND_RE, SERVICE_RE]:
        for match in regex.findall(lower):
            tokens.update(_expand_token(match))
    tokens.update(_key_value_anchor_tokens(lower))
    cache_bucket = row.get("cache_bucket")
    if cache_bucket:
        tokens.add(f"cache:{_normalize_token(cache_bucket)}")
    for token in _tool_schema_tokens(row.get("tool_schemas", [])):
        tokens.add(token)
    return {token for token in tokens if token}


def _anchor_lines(text: str) -> Iterable[str]:
    for line in text.splitlines():
        if any(term in line for term in MARKER_TERMS):
            yield line


def _key_value_anchor_tokens(text: str) -> set[str]:
    out: set[str] = set()
    for line in _anchor_lines(text):
        for key in [
            "cwd",
            "cache_root",
            "runner_home",
            "shell_history",
            "preferred_check",
            "package_manager",
            "service",
            "domain",
            "build",
        ]:
            marker = f"{key}="
            if marker not in line:
                continue
            value = line.split(marker, 1)[1].split(";", 1)[0].strip()
            out.update(_expand_token(value[:180]))
    return out


def _profile_tokens(value: Any) -> set[str]:
    tokens: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key.endswith("_id") or key == "projects":
                continue
            if key == "tool_schema":
                tokens.update(_tool_schema_tokens(child))
            else:
                tokens.update(_profile_tokens(child))
    elif isinstance(value, list):
        for child in value:
            tokens.update(_profile_tokens(child))
    elif value is not None:
        tokens.update(_expand_token(str(value)))
    return tokens


def _tool_schema_tokens(schemas: Any) -> set[str]:
    tokens: set[str] = set()
    for node in _walk(schemas):
        if isinstance(node, dict):
            for key in ["name", "tool", "function", "description"]:
                if key in node and isinstance(node[key], str):
                    for token in _expand_token(node[key]):
                        tokens.add(f"schema:{token}")
            params = node.get("parameters")
            if isinstance(params, list):
                for param in params:
                    for token in _expand_token(str(param)):
                        tokens.add(f"schema:{token}")
    return tokens


def _walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _expand_token(value: Any) -> set[str]:
    token = _normalize_token(value)
    if not token:
        return set()
    out = {token}
    if "/" in token:
        out.add(token.rsplit("/", 1)[-1])
    if "__" in token:
        out.add(token.rsplit("__", 1)[-1])
    if "." in token:
        out.add(token.split(".", 1)[0])
    if token.startswith(("preferred_check=", "cache_root=", "runner_home=", "cwd=")):
        out.add(token.split("=", 1)[1])
    normalized: set[str] = set()
    for item in out:
        normalized_item = _normalize_token(item)
        if normalized_item:
            normalized.add(normalized_item)
    return normalized


def _normalize_token(value: Any) -> str:
    token = str(value).lower().strip().strip("._-/:@;,'\"`()[]{}")
    if len(token) < 3 or len(token) > 180 or token in STOP_TOKENS or token.isdigit():
        return ""
    return token


def _read_profiles(dataset_base: Path) -> dict[str, Any]:
    path = dataset_base / "profiles.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_predictions(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    predictions = data.get("provider_lowcost", {})
    return predictions if isinstance(predictions, dict) else {}


def _write_markdown(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format(row.get(header, "")) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize target-centric warm-start retrieval on user-overlay snapshots."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    parser.add_argument(
        "--pairs",
        nargs="*",
        default=["1000:4000"],
        help="Train:test snapshot pairs. Default runs the fast diagnostic pair only.",
    )
    args = parser.parse_args()
    pairs = [_parse_pair(value) for value in args.pairs]
    print(summarize_warm_start_retrieval(args.output_dir, snapshot_pairs=pairs))


def _parse_pair(value: str) -> tuple[int, int]:
    left, right = value.split(":", 1)
    return int(left), int(right)


if __name__ == "__main__":
    main()
