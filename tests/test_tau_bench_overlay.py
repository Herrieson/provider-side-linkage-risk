from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_privacy.data.audit import audit_dataset
from agent_privacy.data.tau_bench_overlay import build_tau_bench_overlay
from agent_privacy.io import read_jsonl, write_jsonl


class TauBenchOverlayTest(unittest.TestCase):
    def test_build_tau_bench_three_layer_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            config_path = root / "config.json"
            output = root / "overlay"
            snapshots = root / "snapshots"
            write_jsonl(
                source / "attack_view.jsonl",
                [
                    _attack("r1", 1, "alice_smith_1234", "order_abc123"),
                    _attack("r2", 2, "alice_smith_1234", "order_abc123"),
                    _attack("r3", 1, "bob_jones_5678", "reservation_xyz"),
                    _attack("r4", 2, "bob_jones_5678", "reservation_xyz"),
                ],
            )
            write_jsonl(
                source / "ground_truth.jsonl",
                [
                    _truth("r1", "wf1", 1, "alice_smith_1234", "retail"),
                    _truth("r2", "wf1", 2, "alice_smith_1234", "retail"),
                    _truth("r3", "wf2", 1, "bob_jones_5678", "airline"),
                    _truth("r4", "wf2", 2, "bob_jones_5678", "airline"),
                ],
            )
            config_path.write_text(
                json.dumps(
                    {
                        "seed": 3,
                        "source_dataset_dir": str(source),
                        "output_dir": str(output),
                        "snapshot_output_dir": str(snapshots),
                        "overlay_level": "T3_TEST",
                        "max_source_workflows": 2,
                        "label_overlay": {
                            "num_orgs": 2,
                            "domains": ["airline", "retail"],
                            "min_users_per_org": 2,
                            "max_users_per_org": 2,
                            "min_projects_per_org": 1,
                            "max_projects_per_org": 1,
                            "user_alias_collision_rate": 0.0,
                        },
                        "time_overlay": {
                            "start_time": "2026-02-01T09:00:00Z",
                            "time_span_days": 3,
                            "active_hour_spread_hours": 2,
                            "workflow_start_jitter_minutes": 1,
                            "inter_turn_delay_seconds_min": 1,
                            "inter_turn_delay_seconds_max": 2,
                        },
                        "signal_overlay": {
                            "signal_dropout_rate": 0.0,
                            "cache_noise_rate": 0.0,
                            "user_cache_bucket_rate": 1.0,
                            "inject_account_context_rate": 1.0,
                            "inject_case_context_rate": 1.0,
                            "inject_overlay_tool_schema_rate": 1.0,
                        },
                        "snapshots": {"request_counts": [2, 4]},
                    }
                ),
                encoding="utf-8",
            )

            summary = build_tau_bench_overlay(config_path)
            audit = audit_dataset(output)
            attack_rows = read_jsonl(output / "attack_view.jsonl")
            truth_rows = read_jsonl(output / "ground_truth.jsonl")
            provenance_rows = read_jsonl(output / "request_provenance.jsonl")

            self.assertEqual(summary["requests"], 4)
            self.assertEqual(summary["orgs"], 2)
            self.assertEqual(audit["non_provider_attack_view_fields"], [])
            self.assertEqual(len({row["org_id"] for row in truth_rows}), 2)
            self.assertEqual(len({row["user_id"] for row in truth_rows}), 2)
            self.assertEqual(len({row["project_id"] for row in truth_rows}), 2)
            self.assertTrue(any("Account context:" in _text(row) for row in attack_rows))
            self.assertTrue(any("Case context:" in _text(row) for row in attack_rows))
            self.assertNotIn("alice_smith_1234", _text(attack_rows[0]))
            self.assertEqual(provenance_rows[0]["overlay_level"], "T3_TEST")
            self.assertTrue((snapshots / "first_2_requests" / "attack_view.jsonl").exists())


def _attack(request_id: str, turn_id: int, user_id: str, entity: str) -> dict:
    return {
        "request_id": request_id,
        "timestamp": f"2026-02-01T09:00:0{turn_id}Z",
        "model": "test",
        "messages": [
            {"role": "system", "content": "Policy."},
            {"role": "user", "content": f"Help {user_id} with {entity}."},
        ],
        "tool_schemas": [{"name": "get_order", "parameters": ["order_id"]}],
        "token_count": 5,
        "cache_bucket": "source",
        "provider_metadata": {"api_surface": "chat_completions", "brokered": True},
    }


def _truth(request_id: str, workflow_id: str, turn_id: int, user_id: str, domain: str) -> dict:
    return {
        "request_id": request_id,
        "org_id": domain,
        "user_id": user_id,
        "project_id": f"{domain}:entity",
        "workflow_id": workflow_id,
        "turn_id": turn_id,
        "task_type": f"tau_bench_{domain}",
        "profile_truth": {},
    }


def _text(row: dict) -> str:
    return "\n".join(str(message.get("content", "")) for message in row.get("messages", []))


if __name__ == "__main__":
    unittest.main()
