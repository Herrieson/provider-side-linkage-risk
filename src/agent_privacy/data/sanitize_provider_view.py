from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from agent_privacy.io import read_jsonl, write_jsonl


ALLOWED_PROVIDER_FIELDS = {
    "request_id",
    "timestamp",
    "model",
    "messages",
    "tool_schemas",
    "token_count",
    "cache_bucket",
    "provider_metadata",
}
ALLOWED_PROVIDER_METADATA_FIELDS = {"api_surface", "brokered", "stream"}


def sanitize_dataset(dataset_dir: Path) -> dict[str, Any]:
    attack_path = dataset_dir / "attack_view.jsonl"
    rows = read_jsonl(attack_path)
    sanitized = []
    removed_fields: dict[str, int] = {}
    removed_metadata_fields: dict[str, int] = {}
    for row in rows:
        clean = {}
        for key, value in row.items():
            if key not in ALLOWED_PROVIDER_FIELDS:
                removed_fields[key] = removed_fields.get(key, 0) + 1
                continue
            clean[key] = value
        provider_metadata = clean.get("provider_metadata")
        if isinstance(provider_metadata, dict):
            clean_metadata = {}
            for key, value in provider_metadata.items():
                if key not in ALLOWED_PROVIDER_METADATA_FIELDS:
                    removed_metadata_fields[key] = removed_metadata_fields.get(key, 0) + 1
                    continue
                clean_metadata[key] = value
            clean["provider_metadata"] = clean_metadata
        sanitized.append(clean)
    write_jsonl(attack_path, sanitized)
    return {
        "dataset_dir": str(dataset_dir),
        "rows": len(rows),
        "removed_fields": sorted(removed_fields.items()),
        "removed_provider_metadata_fields": sorted(removed_metadata_fields.items()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove non-provider fields from attack_view.jsonl.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    args = parser.parse_args()
    print(sanitize_dataset(args.dataset_dir))


if __name__ == "__main__":
    main()
