from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_privacy.data.swe_workflows import SWEWorkflowImportConfig, import_swe_workflows
from agent_privacy.io import read_jsonl


class SWEWorkflowsImportTest(unittest.TestCase):
    def test_import_local_swe_style_rows(self) -> None:
        rows = [
            {
                "instance_id": "owner__repo-123",
                "repo": "owner/repo",
                "language": "python",
                "problem_statement": "Fix failing auth behavior.",
                "patch": "diff --git a/app.py b/app.py\n+fixed = True",
                "test_patch": "diff --git a/test_app.py b/test_app.py\n+def test_auth(): pass",
                "FAIL_TO_PASS": ["tests/test_auth.py::test_auth"],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "rows.jsonl"
            source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            output = root / "out"

            summary = import_swe_workflows(
                SWEWorkflowImportConfig(
                    input_path=str(source),
                    output_dir=str(output),
                    repair_workspace=True,
                )
            )

            attack_rows = read_jsonl(output / "attack_view.jsonl")
            truth_rows = read_jsonl(output / "ground_truth.jsonl")
            provenance_rows = read_jsonl(output / "request_provenance.jsonl")

            self.assertEqual(summary["workflows_used"], 1)
            self.assertEqual(len(attack_rows), 4)
            self.assertEqual(len(attack_rows), len(truth_rows))
            self.assertEqual(len(attack_rows), len(provenance_rows))
            self.assertEqual(truth_rows[0]["org_id"], "owner")
            self.assertEqual(truth_rows[0]["project_id"], "owner/repo")
            self.assertNotIn("repo", attack_rows[0])
            self.assertIn("provider_metadata", attack_rows[0])
            self.assertIn("workspace=/workspace/owner__repo", attack_rows[0]["messages"][1]["content"])

    def test_max_per_repo_scans_beyond_output_limit(self) -> None:
        rows = [
            {
                "instance_id": f"owner__repo-{idx}",
                "repo": "owner/repo",
                "problem_statement": f"Fix issue {idx}.",
                "patch": "diff --git a/app.py b/app.py\n+fixed = True",
            }
            for idx in range(3)
        ]
        rows.extend(
            [
                {
                    "instance_id": "other__repo-1",
                    "repo": "other/repo",
                    "problem_statement": "Fix other issue.",
                    "patch": "diff --git a/app.py b/app.py\n+other = True",
                },
                {
                    "instance_id": "third__repo-1",
                    "repo": "third/repo",
                    "problem_statement": "Fix third issue.",
                    "patch": "diff --git a/app.py b/app.py\n+third = True",
                },
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "rows.jsonl"
            source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            output = root / "out"

            summary = import_swe_workflows(
                SWEWorkflowImportConfig(
                    input_path=str(source),
                    output_dir=str(output),
                    limit=3,
                    max_per_repo=1,
                )
            )

            truth_rows = read_jsonl(output / "ground_truth.jsonl")
            projects = {row["project_id"] for row in truth_rows}

            self.assertEqual(summary["workflows_used"], 3)
            self.assertEqual(summary["repos_used"], 3)
            self.assertEqual(projects, {"owner/repo", "other/repo", "third/repo"})

    def test_natural_repair_context_does_not_inject_repository_field(self) -> None:
        rows = [
            {
                "instance_id": "owner__repo-123",
                "repo": "owner/repo",
                "problem_statement": "Fix failing behavior in src/app.py.",
                "patch": "diff --git a/src/app.py b/src/app.py\n+fixed = True",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "rows.jsonl"
            source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            output = root / "out"

            import_swe_workflows(
                SWEWorkflowImportConfig(
                    input_path=str(source),
                    output_dir=str(output),
                    repair_context_mode="natural",
                )
            )

            attack_text = "\n".join(
                message.get("content", "")
                for row in read_jsonl(output / "attack_view.jsonl")
                for message in row["messages"]
            )
            provenance_rows = read_jsonl(output / "request_provenance.jsonl")

            self.assertNotIn("[repair_context]", attack_text)
            self.assertNotIn("repository=owner/repo", attack_text)
            self.assertEqual(provenance_rows[0]["repair_context_mode"], "natural")


if __name__ == "__main__":
    unittest.main()
