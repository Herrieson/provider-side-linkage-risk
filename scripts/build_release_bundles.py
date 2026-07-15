from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RESULT_MANIFEST = ROOT / "results" / "result-manifest.json"
DATASET_MANIFEST = ROOT / "artifacts" / "dataset-manifest.json"
FIXED_ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def result_bundle_members() -> list[Path]:
    manifest = load_json(RESULT_MANIFEST)
    members = {
        RESULT_MANIFEST,
        ROOT / "docs" / "artifact-manifest.json",
        ROOT / "LICENSE",
        ROOT / "THIRD_PARTY.md",
    }
    policy = manifest["bundle_policy"]
    include_patterns = tuple(policy["include"])
    exclude_patterns = tuple(policy["exclude"])

    for run in manifest["curated_runs"]:
        if not run.get("bundle", False):
            continue
        run_dir = ROOT / run["local_path"]
        if not run_dir.is_dir():
            raise FileNotFoundError(f"missing curated result directory: {run_dir}")
        for path in run_dir.rglob("*"):
            if path.is_file() and include_result_file(
                path.relative_to(run_dir), include_patterns, exclude_patterns
            ):
                members.add(path)
        for table in run.get("tables", []):
            table_path = ROOT / table
            if not table_path.is_file():
                raise FileNotFoundError(f"missing paper table: {table_path}")
            members.add(table_path)
            csv_peer = table_path.with_suffix(".csv")
            if csv_peer.is_file():
                members.add(csv_peer)
    return sorted(members, key=lambda path: path.relative_to(ROOT).as_posix())


def include_result_file(
    relative_path: Path,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
) -> bool:
    relative = relative_path.as_posix()
    name = relative_path.name
    if "dataset" in relative_path.parts:
        return False
    if any(fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(name, pattern) for pattern in exclude_patterns):
        return False
    return any(
        fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(name, pattern)
        for pattern in include_patterns
    )


def synthetic_a_members() -> list[Path]:
    manifest = load_json(DATASET_MANIFEST)
    entry = next(item for item in manifest["datasets"] if item["id"] == "synthetic_a")
    dataset_dir = ROOT / entry["local_path"]
    if not dataset_dir.is_dir():
        raise FileNotFoundError(
            f"missing Synthetic Dataset A at {dataset_dir}; generate it from {entry['config']} first"
        )
    members = {
        DATASET_MANIFEST,
        ROOT / entry["config"],
        ROOT / entry["dataset_card"],
        ROOT / "docs" / "data-schema.md",
        ROOT / "LICENSE",
        ROOT / "THIRD_PARTY.md",
    }
    members.update(path for path in dataset_dir.rglob("*") if path.is_file())
    return sorted(members, key=lambda path: path.relative_to(ROOT).as_posix())


def write_deterministic_zip(output_path: Path, members: list[Path]) -> dict[str, int | str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in members:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(relative, FIXED_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return {
        "path": str(output_path),
        "files": len(members),
        "bytes": output_path.stat().st_size,
        "sha256": sha256(output_path),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(output_dir: Path, bundle_paths: list[Path]) -> Path:
    checksum_path = output_dir / "SHA256SUMS"
    lines = [f"{sha256(path)}  {path.name}" for path in sorted(bundle_paths)]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return checksum_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic GitHub Release assets from the local paper workspace."
    )
    parser.add_argument(
        "--bundle",
        choices=("all", "results", "synthetic-a"),
        default="all",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    built: list[dict[str, int | str]] = []
    paths: list[Path] = []
    if args.bundle in {"all", "results"}:
        path = output_dir / "agent-privacy-paper-results.zip"
        built.append(write_deterministic_zip(path, result_bundle_members()))
        paths.append(path)
    if args.bundle in {"all", "synthetic-a"}:
        path = output_dir / "agent-privacy-synthetic-a.zip"
        built.append(write_deterministic_zip(path, synthetic_a_members()))
        paths.append(path)
    checksum_path = write_checksums(output_dir, paths)
    print(json.dumps({"bundles": built, "checksums": str(checksum_path)}, indent=2))


if __name__ == "__main__":
    main()
