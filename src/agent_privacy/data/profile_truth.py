from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from agent_privacy.features.extract import REPOSITORY_FIELD_RE, request_text
from agent_privacy.io import read_jsonl, write_jsonl


WORKSPACE_REPO_RE = re.compile(r"/workspace/([A-Za-z0-9_.-]+)__([A-Za-z0-9_.-]+)")


def enrich_profile_truth(dataset_dir: Path) -> dict[str, Any]:
    attack_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    attack_by_id = {row["request_id"]: row for row in attack_rows}
    updated = []
    fields_added: dict[str, int] = {}
    for row in truth_rows:
        attack_row = attack_by_id.get(row["request_id"])
        out = dict(row)
        profile_truth = dict(out.get("profile_truth") or {})
        if attack_row is not None:
            before = {field: set(values) for field, values in profile_truth.items()}
            _merge_truth(profile_truth, _technical_truth_from_attack_row(attack_row))
            for field, values in profile_truth.items():
                added = len(set(values) - before.get(field, set()))
                fields_added[field] = fields_added.get(field, 0) + added
        out["profile_truth"] = {field: sorted(set(values)) for field, values in profile_truth.items()}
        updated.append(out)
    write_jsonl(dataset_dir / "ground_truth.jsonl", updated)
    return {
        "dataset_dir": str(dataset_dir),
        "truth_rows": len(updated),
        "fields_added": fields_added,
    }


def _technical_truth_from_attack_row(row: dict[str, Any]) -> dict[str, list[str]]:
    text = request_text(row).lower()
    truth: dict[str, list[str]] = {}
    repo_values = _repo_values(text)
    if repo_values:
        truth["repo_names"] = sorted(repo_values)
        truth["service_names"] = sorted(repo_values)
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
                truth.setdefault(field, []).append(value)
    return truth


def _repo_values(text: str) -> set[str]:
    values = {repo.lower() for _, repo in REPOSITORY_FIELD_RE.findall(text)}
    values.update(repo.lower() for _, repo in WORKSPACE_REPO_RE.findall(text))
    return values


def _merge_truth(target: dict[str, Any], source: dict[str, list[str]]) -> None:
    for field, values in source.items():
        current = list(target.get(field) or [])
        current.extend(values)
        target[field] = current


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich ground_truth.jsonl with provider-visible technical profile truth."
    )
    parser.add_argument("--dataset-dir", type=Path, required=True)
    args = parser.parse_args()
    print(enrich_profile_truth(args.dataset_dir))


if __name__ == "__main__":
    main()
