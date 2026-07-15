from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
MAX_GIT_FILE_BYTES = 95 * 1024 * 1024
TEXT_SCAN_LIMIT = 5 * 1024 * 1024
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{20,}\b"),
    "Hugging Face token": re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    "OpenAI-style token": re.compile(r"\bsk-(?!test-)[A-Za-z0-9_-]{20,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
FORBIDDEN_GIT_PREFIXES = (
    "artifacts/datasets/",
    "results/_archive/",
)
ALLOWED_RESULT_FILES = {
    "results/README.md",
    "results/result-manifest.json",
}


def git_candidates() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / value.decode() for value in completed.stdout.split(b"\0") if value]


def validate_json(path: Path, errors: list[str]) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
        return None


def validate_catalogs(errors: list[str]) -> None:
    dataset_path = ROOT / "artifacts" / "dataset-manifest.json"
    result_path = ROOT / "results" / "result-manifest.json"
    artifact_path = ROOT / "docs" / "artifact-manifest.json"
    dataset_manifest = validate_json(dataset_path, errors)
    result_manifest = validate_json(result_path, errors)
    artifact_manifest = validate_json(artifact_path, errors)
    if not all(
        isinstance(manifest, dict)
        for manifest in (dataset_manifest, result_manifest, artifact_manifest)
    ):
        return

    example = ROOT / dataset_manifest["bundled_example"]["path"]
    if not example.is_dir():
        errors.append(f"bundled example is missing: {example.relative_to(ROOT)}")
    for entry in dataset_manifest["datasets"]:
        for field in ("config", "dataset_card", "reproduction"):
            value = entry.get(field)
            if value and not (ROOT / value).is_file():
                errors.append(f"dataset {entry['id']} references missing {field}: {value}")
    for run in result_manifest["curated_runs"]:
        for table in run.get("tables", []):
            if not (ROOT / table).is_file():
                errors.append(f"result {run['id']} references missing table: {table}")
    for label, value in artifact_manifest["release"].items():
        if isinstance(value, str) and not (ROOT / value).exists():
            errors.append(f"artifact release entry {label} references missing path: {value}")


def scan_candidate(path: Path, errors: list[str]) -> None:
    relative = path.relative_to(ROOT).as_posix()
    if not path.is_file():
        return
    size = path.stat().st_size
    if size > MAX_GIT_FILE_BYTES:
        errors.append(f"Git candidate exceeds 95 MiB: {relative} ({size} bytes)")
    if relative.startswith(FORBIDDEN_GIT_PREFIXES):
        errors.append(f"raw dataset/archive must not be committed: {relative}")
    if relative.startswith("results/") and relative not in ALLOWED_RESULT_FILES:
        errors.append(f"raw result must be a release asset, not a Git blob: {relative}")
    if path.suffix == ".json":
        validate_json(path, errors)
    if size > TEXT_SCAN_LIMIT or path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".zip"}:
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    if str(ROOT) in text:
        errors.append(f"workspace-specific absolute path in {relative}: {ROOT}")
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"possible {label} in {relative}")


def ignored(path: str) -> bool:
    return subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=ROOT,
        check=False,
    ).returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the GitHub release boundary.")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable summary.")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    candidates = git_candidates()
    for path in candidates:
        scan_candidate(path, errors)
    validate_catalogs(errors)

    for representative in (
        "artifacts/datasets/open_swe_traces_raw_1000/attack_view.jsonl",
        "results/open_swe_traces_raw_1000_m0/M0/attack_view.jsonl",
        "dist/agent-privacy-paper-results.zip",
        "docs/overleaf/API.zip",
    ):
        if not ignored(representative):
            errors.append(f"large/generated path is not ignored: {representative}")
    if not (ROOT / "LICENSE").is_file():
        errors.append("MIT LICENSE file is missing")
    if not (ROOT / "THIRD_PARTY.md").is_file():
        errors.append("THIRD_PARTY.md is missing")

    summary = {
        "status": "failed" if errors else "passed",
        "git_candidate_files": len(candidates),
        "git_candidate_bytes": sum(path.stat().st_size for path in candidates if path.is_file()),
        "errors": errors,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"release check: {summary['status']}")
        print(
            f"Git candidates: {summary['git_candidate_files']} files, "
            f"{summary['git_candidate_bytes']} bytes"
        )
        for warning in warnings:
            print(f"WARNING: {warning}")
        for error in errors:
            print(f"ERROR: {error}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
