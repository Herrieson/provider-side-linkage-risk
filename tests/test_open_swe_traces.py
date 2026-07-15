from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_privacy.data.open_swe_traces import OpenSWEImportConfig, import_open_swe_traces
from agent_privacy.io import read_jsonl


class OpenSWETracesImportTest(unittest.TestCase):
    def test_import_local_jsonl(self) -> None:
        rows = [
            {
                "repo": "owner_alpha/project_api",
                "language": "python",
                "trajectory_id": "traj_alpha_1",
                "trajectory": [
                    {"role": "system", "content": "You are a coding agent."},
                    {"role": "user", "content": "Fix failing auth test."},
                    {"role": "assistant", "content": "I will inspect the test."},
                    {"role": "tool", "name": "shell", "content": "pytest tests/test_auth.py"},
                ],
            },
            {
                "repo": "owner_beta/service_core",
                "language": "go",
                "trajectory_id": "traj_beta_1",
                "trajectory": json.dumps(
                    [
                        {"role": "user", "content": "Investigate panic in router."},
                        {"thought": "Need logs", "observation": "go test ./... failed"},
                    ]
                ),
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.jsonl"
            source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            output = root / "imported"

            summary = import_open_swe_traces(
                OpenSWEImportConfig(
                    input_path=str(source),
                    output_dir=str(output),
                    limit=10,
                    repair_mode="repository_workspace",
                )
            )

            attack_rows = read_jsonl(output / "attack_view.jsonl")
            truth_rows = read_jsonl(output / "ground_truth.jsonl")
            provenance_rows = read_jsonl(output / "request_provenance.jsonl")

            self.assertEqual(summary["trajectories_used"], 2)
            self.assertEqual(len(attack_rows), len(truth_rows))
            self.assertEqual(len(attack_rows), len(provenance_rows))
            self.assertGreaterEqual(len(attack_rows), 2)
            self.assertIn("workspace=/workspace/owner_alpha__project_api", attack_rows[0]["messages"][1]["content"])
            self.assertNotIn("repair_mode", attack_rows[0])
            self.assertEqual(provenance_rows[0]["repair_mode"], "repository_workspace")
            self.assertIsNone(truth_rows[0]["user_id"])

    def test_reservoir_sampling_scans_beyond_limit(self) -> None:
        rows = [
            {
                "repo": f"owner/project_{idx}",
                "trajectory_id": f"traj_{idx}",
                "trajectory": [
                    {"role": "user", "content": f"Fix issue {idx}."},
                    {"role": "assistant", "content": "I will inspect it."},
                    {"role": "tool", "name": "shell", "content": "pytest"},
                ],
            }
            for idx in range(8)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.jsonl"
            source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            output = root / "imported"

            summary = import_open_swe_traces(
                OpenSWEImportConfig(
                    input_path=str(source),
                    output_dir=str(output),
                    limit=3,
                    sample_mode="reservoir",
                    seed=3,
                )
            )

            manifest = json.loads((output / "source_manifest.json").read_text(encoding="utf-8"))
            truth_rows = read_jsonl(output / "ground_truth.jsonl")
            projects = {row["project_id"] for row in truth_rows}

            self.assertEqual(summary["source_rows_seen"], 8)
            self.assertEqual(summary["eligible_trajectories"], 8)
            self.assertEqual(summary["trajectories_used"], 3)
            self.assertEqual(manifest["sample_mode"], "reservoir")
            self.assertEqual(manifest["eligible_trajectories"], 8)
            self.assertEqual(len(projects), 3)


if __name__ == "__main__":
    unittest.main()
