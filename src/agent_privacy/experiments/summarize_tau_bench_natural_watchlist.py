from __future__ import annotations

import argparse
import hashlib
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from agent_privacy.attacks.cluster import UnionFind
from agent_privacy.experiments.bootstrap_ci import _quantile
from agent_privacy.experiments.semantic_linkage import encode_documents, write_markdown
from agent_privacy.experiments.summarize_tau_bench_temporal_stress import _semantic_document
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET_DIR = Path("artifacts/datasets/tau_bench_historical_sample200")
DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "tau_bench_natural_user_watchlist"
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
USER_TOKEN_RE = re.compile(r"\b[a-z]+_[a-z]+_\d{4}\b", re.IGNORECASE)
NAME_ZIP_RE = re.compile(
    r"(?:my name is|name is)\s+([a-z]+)\s+([a-z]+).{0,180}?"
    r"(?:zip code(?: is)?|zip)\s+(?:is\s+)?(\d{5})",
    re.IGNORECASE | re.DOTALL,
)
TRIAL_SUFFIX_RE = re.compile(r":trial_[^:]+$")


def summarize_natural_watchlist(
    *,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    seed: int = 7,
    bootstrap_iterations: int = 500,
) -> dict[str, str]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    attack_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    provenance_rows = read_jsonl(dataset_dir / "request_provenance.jsonl")
    truth_by_id = {str(row["request_id"]): row for row in truth_rows}
    attacks_by_workflow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    truth_by_workflow: dict[str, dict[str, Any]] = {}
    for row in attack_rows:
        truth = truth_by_id[str(row["request_id"])]
        workflow = str(truth["workflow_id"])
        attacks_by_workflow[workflow].append(row)
        truth_by_workflow[workflow] = truth
    workflows = sorted(
        attacks_by_workflow,
        key=lambda workflow: min(
            _request_index(str(row["request_id"])) for row in attacks_by_workflow[workflow]
        ),
    )
    split = len(workflows) // 2
    early_workflows = workflows[:split]
    later_workflows = workflows[split:]
    anchors = {
        workflow: _workflow_anchors(attacks_by_workflow[workflow]) for workflow in workflows
    }
    base_task_by_workflow = _base_tasks_by_workflow(
        provenance_rows=provenance_rows,
        truth_by_id=truth_by_id,
    )

    rows = []
    for condition, early_types, later_types in (
        ("all_identity_anchors", {"uid", "email", "namezip"}, {"uid", "email", "namezip"}),
        ("uid_only", {"uid"}, {"uid"}),
        ("cross_alias_no_later_uid", {"uid", "email", "namezip"}, {"email", "namezip"}),
        ("cross_alias_namezip_only", {"uid", "email", "namezip"}, {"namezip"}),
    ):
        rows.append(
            _score_condition(
                condition=condition,
                early_workflows=early_workflows,
                later_workflows=later_workflows,
                anchors=anchors,
                truth_by_workflow=truth_by_workflow,
                early_types=early_types,
                later_types=later_types,
                seed=seed,
                bootstrap_iterations=bootstrap_iterations,
            )
        )
    rows.append(
        _semantic_watchlist_row(
            condition="strict_later_semantic_intent",
            early_workflows=early_workflows,
            later_workflows=later_workflows,
            anchors=anchors,
            attacks_by_workflow=attacks_by_workflow,
            truth_by_workflow=truth_by_workflow,
            seed=seed,
            bootstrap_iterations=bootstrap_iterations,
        )
    )
    task_disjoint_early, task_disjoint_later = _base_task_disjoint_split(
        workflows,
        base_task_by_workflow,
        seed=seed,
    )
    rows.append(
        _semantic_watchlist_row(
            condition="strict_semantic_base_task_disjoint",
            early_workflows=task_disjoint_early,
            later_workflows=task_disjoint_later,
            anchors=anchors,
            attacks_by_workflow=attacks_by_workflow,
            truth_by_workflow=truth_by_workflow,
            seed=seed,
            bootstrap_iterations=bootstrap_iterations,
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
    write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path)}


def _score_condition(
    *,
    condition: str,
    early_workflows: list[str],
    later_workflows: list[str],
    anchors: dict[str, set[str]],
    truth_by_workflow: dict[str, dict[str, Any]],
    early_types: set[str],
    later_types: set[str],
    seed: int,
    bootstrap_iterations: int,
) -> dict[str, Any]:
    early_filtered = {
        workflow: _select_types(anchors[workflow], early_types) for workflow in early_workflows
    }
    union_find = UnionFind(early_workflows)
    workflows_by_anchor: dict[str, list[str]] = defaultdict(list)
    for workflow, values in early_filtered.items():
        for value in values:
            workflows_by_anchor[value].append(workflow)
    for members in workflows_by_anchor.values():
        for workflow in members[1:]:
            union_find.union(members[0], workflow)
    component_by_workflow = {
        workflow: union_find.find(workflow) for workflow in early_workflows
    }
    components_by_anchor: dict[str, set[str]] = defaultdict(set)
    for workflow, values in early_filtered.items():
        for value in values:
            components_by_anchor[value].add(component_by_workflow[workflow])
    watchlist = {
        anchor: next(iter(components))
        for anchor, components in components_by_anchor.items()
        if len(components) == 1
    }
    users_by_component: dict[str, set[str]] = defaultdict(set)
    for workflow, component in component_by_workflow.items():
        users_by_component[component].add(str(truth_by_workflow[workflow]["user_id"]))
    seen_users = {
        str(truth_by_workflow[workflow]["user_id"]) for workflow in early_workflows
    }
    eligible = [
        workflow
        for workflow in later_workflows
        if str(truth_by_workflow[workflow]["user_id"]) in seen_users
    ]
    assignments: dict[str, str] = {}
    ambiguous = 0
    for workflow in later_workflows:
        votes = {
            watchlist[anchor]
            for anchor in _select_types(anchors[workflow], later_types)
            if anchor in watchlist
        }
        if len(votes) == 1:
            assignments[workflow] = next(iter(votes))
        elif len(votes) > 1:
            ambiguous += 1
    scores = _assignment_scores(
        later_workflows=later_workflows,
        eligible=set(eligible),
        assignments=assignments,
        users_by_component=users_by_component,
        truth_by_workflow=truth_by_workflow,
        seed=seed,
        bootstrap_iterations=bootstrap_iterations,
    )
    pure_components = sum(len(users) == 1 for users in users_by_component.values())
    return {
        "condition": condition,
        "early_workflows": len(early_workflows),
        "later_workflows": len(later_workflows),
        "early_users": len(seen_users),
        "later_seen_user_workflows": len(eligible),
        "assigned_later_workflows": scores["assigned"],
        "matched_eligible_workflows": scores["matched_eligible"],
        "correct_assignments": scores["correct"],
        "ambiguous_later_workflows": ambiguous,
        "watchlist_anchors": len(watchlist),
        "early_components": len(users_by_component),
        "pure_component_rate": pure_components / len(users_by_component)
        if users_by_component
        else 0.0,
        "precision": scores["precision"],
        "recall": scores["recall"],
        "f1": scores["f1"],
        "f1_ci_low": scores["f1_ci_low"],
        "f1_ci_high": scores["f1_ci_high"],
    }


def _workflow_anchors(rows: list[dict[str, Any]]) -> set[str]:
    longest = max(rows, key=lambda row: len(row.get("messages", [])))
    text = "\n".join(
        str(message.get("content", "")) for message in longest.get("messages", [])
    ).lower()
    anchors = {f"uid:{value.lower()}" for value in USER_TOKEN_RE.findall(text)}
    anchors.update(f"email:{value.lower()}" for value in EMAIL_RE.findall(text))
    anchors.update(
        f"namezip:{first.lower()}:{last.lower()}:{zipcode}"
        for first, last, zipcode in NAME_ZIP_RE.findall(text)
    )
    return anchors


def _semantic_watchlist_row(
    *,
    condition: str,
    early_workflows: list[str],
    later_workflows: list[str],
    anchors: dict[str, set[str]],
    attacks_by_workflow: dict[str, list[dict[str, Any]]],
    truth_by_workflow: dict[str, dict[str, Any]],
    seed: int,
    bootstrap_iterations: int,
) -> dict[str, Any]:
    component_by_workflow, users_by_component, watchlist = _early_components(
        early_workflows, anchors
    )
    for workflow, component in component_by_workflow.items():
        users_by_component[component].add(str(truth_by_workflow[workflow]["user_id"]))
    documents = {
        workflow: _identity_masked_semantic_document(
            min(
                attacks_by_workflow[workflow],
                key=lambda row: len(row.get("messages", [])),
            )
        )
        for workflow in early_workflows + later_workflows
    }
    workflow_ids, vectors = encode_documents(documents)
    vector_by_workflow = {
        workflow: vectors[index] for index, workflow in enumerate(workflow_ids)
    }
    threshold = _calibrate_semantic_threshold(
        early_workflows,
        component_by_workflow,
        vector_by_workflow,
    )
    seen_users = {
        str(truth_by_workflow[workflow]["user_id"]) for workflow in early_workflows
    }
    eligible = [
        workflow
        for workflow in later_workflows
        if str(truth_by_workflow[workflow]["user_id"]) in seen_users
    ]
    assignments = _semantic_assignments(
        later_workflows,
        early_workflows,
        component_by_workflow,
        vector_by_workflow,
        threshold=threshold,
    )
    scores = _assignment_scores(
        later_workflows=later_workflows,
        eligible=set(eligible),
        assignments=assignments,
        users_by_component=users_by_component,
        truth_by_workflow=truth_by_workflow,
        seed=seed,
        bootstrap_iterations=bootstrap_iterations,
    )
    pure_components = sum(len(users) == 1 for users in users_by_component.values())
    return {
        "condition": condition,
        "early_workflows": len(early_workflows),
        "later_workflows": len(later_workflows),
        "early_users": len(seen_users),
        "later_seen_user_workflows": len(eligible),
        "assigned_later_workflows": scores["assigned"],
        "matched_eligible_workflows": scores["matched_eligible"],
        "correct_assignments": scores["correct"],
        "ambiguous_later_workflows": 0,
        "watchlist_anchors": len(watchlist),
        "early_components": len(users_by_component),
        "pure_component_rate": pure_components / len(users_by_component),
        "precision": scores["precision"],
        "recall": scores["recall"],
        "f1": scores["f1"],
        "f1_ci_low": scores["f1_ci_low"],
        "f1_ci_high": scores["f1_ci_high"],
        "semantic_threshold": threshold,
    }


def _identity_masked_semantic_document(row: dict[str, Any]) -> str:
    text = "\n".join(
        str(message.get("content", "")) for message in row.get("messages", [])
    )
    identity_names = {
        name.lower()
        for first, last, _ in NAME_ZIP_RE.findall(text)
        for name in (first, last)
    }
    document = _semantic_document(row)
    document = EMAIL_RE.sub(" email_address ", document)
    document = USER_TOKEN_RE.sub(" user_identifier ", document)
    for name in sorted(identity_names, key=len, reverse=True):
        document = re.sub(
            rf"\b{re.escape(name)}\b",
            " person_name ",
            document,
            flags=re.IGNORECASE,
        )
    return " ".join(document.split())


def _base_tasks_by_workflow(
    *,
    provenance_rows: list[dict[str, Any]],
    truth_by_id: dict[str, dict[str, Any]],
) -> dict[str, str]:
    base_tasks: dict[str, str] = {}
    for row in provenance_rows:
        request_id = str(row.get("request_id", ""))
        truth = truth_by_id.get(request_id)
        if truth is None:
            continue
        workflow = str(truth["workflow_id"])
        task = TRIAL_SUFFIX_RE.sub("", str(row.get("source_task_id", workflow)))
        previous = base_tasks.setdefault(workflow, task)
        if previous != task:
            raise ValueError(f"workflow {workflow} maps to multiple base tasks")
    return base_tasks


def _base_task_disjoint_split(
    workflows: list[str],
    base_task_by_workflow: dict[str, str],
    *,
    seed: int,
) -> tuple[list[str], list[str]]:
    by_task: dict[str, list[str]] = defaultdict(list)
    for workflow in workflows:
        by_task[base_task_by_workflow.get(workflow, workflow)].append(workflow)
    ordered_tasks = sorted(
        by_task,
        key=lambda task: (
            hashlib.sha256(f"{seed}:{task}".encode()).hexdigest(),
            task,
        ),
    )
    sides: tuple[list[str], list[str]] = ([], [])
    for task in ordered_tasks:
        side = 0 if len(sides[0]) <= len(sides[1]) else 1
        sides[side].extend(sorted(by_task[task]))
    return sides


def _assignment_scores(
    *,
    later_workflows: list[str],
    eligible: set[str],
    assignments: dict[str, str],
    users_by_component: dict[str, set[str]],
    truth_by_workflow: dict[str, dict[str, Any]],
    seed: int,
    bootstrap_iterations: int,
) -> dict[str, float | int]:
    def counts(sample: list[str]) -> tuple[int, int, int, int]:
        multiplicity = Counter(sample)
        assigned = sum(multiplicity[workflow] for workflow in assignments)
        matched_eligible = sum(
            multiplicity[workflow] for workflow in assignments if workflow in eligible
        )
        correct = sum(
            multiplicity[workflow]
            for workflow, component in assignments.items()
            if str(truth_by_workflow[workflow]["user_id"])
            in users_by_component[component]
        )
        eligible_count = sum(multiplicity[workflow] for workflow in eligible)
        return assigned, matched_eligible, correct, eligible_count

    def metrics(sample: list[str]) -> tuple[float, float, float, tuple[int, int, int, int]]:
        sample_counts = counts(sample)
        assigned, _, correct, eligible_count = sample_counts
        precision = correct / assigned if assigned else 0.0
        recall = correct / eligible_count if eligible_count else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return precision, recall, f1, sample_counts

    precision, recall, f1, observed = metrics(later_workflows)
    rng = random.Random(seed)
    samples = [
        metrics(rng.choices(later_workflows, k=len(later_workflows)))[2]
        for _ in range(bootstrap_iterations)
    ]
    assigned, matched_eligible, correct, _ = observed
    return {
        "assigned": assigned,
        "matched_eligible": matched_eligible,
        "correct": correct,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "f1_ci_low": _quantile(samples, 0.025),
        "f1_ci_high": _quantile(samples, 0.975),
    }


def _early_components(
    early_workflows: list[str], anchors: dict[str, set[str]]
) -> tuple[dict[str, str], dict[str, set[str]], dict[str, str]]:
    union_find = UnionFind(early_workflows)
    workflows_by_anchor: dict[str, list[str]] = defaultdict(list)
    for workflow in early_workflows:
        for anchor in anchors[workflow]:
            workflows_by_anchor[anchor].append(workflow)
    for members in workflows_by_anchor.values():
        for workflow in members[1:]:
            union_find.union(members[0], workflow)
    components = {workflow: union_find.find(workflow) for workflow in early_workflows}
    users: dict[str, set[str]] = defaultdict(set)
    anchor_components: dict[str, set[str]] = defaultdict(set)
    for workflow, component in components.items():
        for anchor in anchors[workflow]:
            anchor_components[anchor].add(component)
    watchlist = {
        anchor: next(iter(values))
        for anchor, values in anchor_components.items()
        if len(values) == 1
    }
    return components, users, watchlist


def _calibrate_semantic_threshold(
    workflows: list[str],
    components: dict[str, str],
    vectors: dict[str, np.ndarray],
) -> float:
    component_sizes = Counter(components.values())
    eligible = {
        workflow
        for workflow in workflows
        if component_sizes[components[workflow]] > 1
    }
    rows = []
    for threshold in (value / 100 for value in range(60, 100, 2)):
        assignments = _semantic_assignments(
            workflows,
            workflows,
            components,
            vectors,
            threshold=threshold,
            exclude_self=True,
        )
        correct = sum(
            workflow in eligible and components[workflow] == component
            for workflow, component in assignments.items()
        )
        precision = correct / len(assignments) if assignments else 0.0
        recall = correct / len(eligible) if eligible else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append((threshold, precision, recall, f1))
    eligible_rows = [row for row in rows if row[1] >= 0.8]
    return max(eligible_rows or rows, key=lambda row: (row[3], row[1], row[0]))[0]


def _semantic_assignments(
    queries: list[str],
    early_workflows: list[str],
    components: dict[str, str],
    vectors: dict[str, np.ndarray],
    *,
    threshold: float,
    exclude_self: bool = False,
) -> dict[str, str]:
    assignments = {}
    for query in queries:
        scores: dict[str, float] = defaultdict(lambda: -1.0)
        for early in early_workflows:
            if exclude_self and query == early:
                continue
            component = components[early]
            score = float(vectors[query] @ vectors[early])
            scores[component] = max(scores[component], score)
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if not ranked or ranked[0][1] < threshold:
            continue
        if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < 0.02:
            continue
        assignments[query] = ranked[0][0]
    return assignments


def _select_types(anchors: set[str], types: set[str]) -> set[str]:
    return {anchor for anchor in anchors if anchor.split(":", 1)[0] in types}


def _request_index(request_id: str) -> int:
    return int(request_id.split("_")[2])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--bootstrap-iterations", type=int, default=500)
    args = parser.parse_args()
    print(
        summarize_natural_watchlist(
            dataset_dir=args.dataset_dir,
            output_dir=args.output_dir,
            seed=args.seed,
            bootstrap_iterations=args.bootstrap_iterations,
        )
    )


if __name__ == "__main__":
    main()
