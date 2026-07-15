from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_privacy.data.audit import audit_dataset
from agent_privacy.data.generator import generate_dataset
from agent_privacy.data.schemas import DatasetConfig
from agent_privacy.data.swe_workflows import SWEWorkflowImportConfig, import_swe_workflows
from agent_privacy.data.tau_bench import TauBenchImportConfig, import_tau_bench
from agent_privacy.data.time_snapshots import build_time_snapshots
from agent_privacy.io import read_jsonl, write_jsonl


class ProviderViewAndSnapshotsTest(unittest.TestCase):
    def test_synthetic_attack_view_has_only_provider_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generate_dataset(
                DatasetConfig(
                    num_orgs=1,
                    users_per_org=1,
                    projects_per_org=1,
                    workflows_per_user=1,
                    turns_per_workflow=2,
                    noise_rate=0,
                ),
                root,
            )

            row = read_jsonl(root / "attack_view.jsonl")[0]
            audit = audit_dataset(root)

            self.assertNotIn("defense", row)
            self.assertEqual(audit["non_provider_attack_view_fields"], [])

    def test_swe_provider_metadata_excludes_source_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "rows.jsonl"
            write_jsonl(
                source,
                [
                    {
                        "instance_id": "owner__repo-1",
                        "repo": "owner/repo",
                        "problem_statement": "Fix failing behavior in src/app.py.",
                        "patch": "diff --git a/src/app.py b/src/app.py\n+fixed = True",
                    }
                ],
            )
            output = root / "dataset"

            import_swe_workflows(
                SWEWorkflowImportConfig(input_path=str(source), output_dir=str(output), limit=1)
            )
            row = read_jsonl(output / "attack_view.jsonl")[0]
            provenance = read_jsonl(output / "request_provenance.jsonl")[0]
            audit = audit_dataset(output)

            self.assertNotIn("source_view", row["provider_metadata"])
            self.assertEqual(provenance["source_view"], "swe_repaired_workflow")
            self.assertEqual(audit["non_provider_provider_metadata_fields"], [])

    def test_build_time_snapshots_by_request_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            attack_rows = [
                _attack("r3", "2026-01-01T00:03:00Z"),
                _attack("r1", "2026-01-01T00:01:00Z"),
                _attack("r2", "2026-01-01T00:02:00Z"),
            ]
            truth_rows = [_truth(row["request_id"]) for row in attack_rows]
            write_jsonl(source / "attack_view.jsonl", attack_rows)
            write_jsonl(source / "ground_truth.jsonl", truth_rows)

            output = root / "snapshots"
            manifest = build_time_snapshots(source, output, request_counts=[2])
            snapshot_rows = read_jsonl(output / "first_2_requests" / "attack_view.jsonl")

            self.assertEqual(manifest["snapshots"][0]["requests"], 2)
            self.assertEqual([row["request_id"] for row in snapshot_rows], ["r1", "r2"])

    def test_tau_bench_importer_writes_provider_view_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "tau.jsonl"
            write_jsonl(
                source,
                [
                    {
                        "id": "retail_case_1",
                        "domain": "retail",
                        "customer_id": "customer_abc123",
                        "policy": "Refund orders only after checking order status.",
                        "tools": [
                            {"name": "get_order", "parameters": ["order_id"]},
                            {"name": "issue_refund", "parameters": ["order_id", "amount"]},
                        ],
                        "trajectory": [
                            {
                                "role": "user",
                                "content": "Please refund order_778899 for customer_abc123.",
                            },
                            {
                                "role": "assistant",
                                "content": "I will check the order before refunding.",
                            },
                            {
                                "role": "tool",
                                "name": "get_order",
                                "content": '{"order_id": "order_778899", "status": "delivered"}',
                            },
                            {
                                "role": "assistant",
                                "content": "The order is delivered, so I can continue.",
                            },
                        ],
                    }
                ],
            )
            output = root / "dataset"

            summary = import_tau_bench(
                TauBenchImportConfig(
                    input_path=str(source),
                    output_dir=str(output),
                    limit=1,
                )
            )
            audit = audit_dataset(output)
            attack_rows = read_jsonl(output / "attack_view.jsonl")
            truth_rows = read_jsonl(output / "ground_truth.jsonl")

            self.assertEqual(summary["workflows_used"], 1)
            self.assertEqual(summary["requests"], 2)
            self.assertEqual(audit["non_provider_attack_view_fields"], [])
            self.assertEqual(truth_rows[0]["org_id"], "retail")
            self.assertEqual(truth_rows[0]["user_id"], "customer_abc123")
            self.assertNotIn("customer_id", attack_rows[0])
            self.assertEqual(attack_rows[0]["tool_schemas"][0]["name"], "get_order")


def _attack(request_id: str, timestamp: str) -> dict:
    return {
        "request_id": request_id,
        "timestamp": timestamp,
        "model": "test",
        "messages": [{"role": "user", "content": request_id}],
        "tool_schemas": [],
        "token_count": 1,
        "cache_bucket": None,
        "provider_metadata": {"api_surface": "chat_completions", "brokered": True},
    }


def _truth(request_id: str) -> dict:
    return {
        "request_id": request_id,
        "org_id": "org",
        "user_id": "user",
        "project_id": "project",
        "workflow_id": "workflow",
        "turn_id": 1,
        "task_type": "unit",
        "profile_truth": {},
    }


if __name__ == "__main__":
    unittest.main()
