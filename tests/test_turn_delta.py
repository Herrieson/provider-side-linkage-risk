from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_privacy.data.turn_delta import build_turn_delta_dataset
from agent_privacy.io import read_jsonl, write_jsonl


class TurnDeltaTest(unittest.TestCase):
    def test_build_turn_delta_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            output = root / "delta"
            attack_rows = [
                _attack("r1", ["system", "user", "assistant"]),
                _attack("r2", ["system", "user", "assistant", "tool", "assistant"]),
            ]
            truth_rows = [
                _truth("r1", turn_id=1),
                _truth("r2", turn_id=2),
            ]
            provenance_rows = [
                {"request_id": "r1", "source": "unit"},
                {"request_id": "r2", "source": "unit"},
            ]
            write_jsonl(source / "attack_view.jsonl", attack_rows)
            write_jsonl(source / "ground_truth.jsonl", truth_rows)
            write_jsonl(source / "request_provenance.jsonl", provenance_rows)

            summary = build_turn_delta_dataset(source, output, [1, 2])
            delta_attack = read_jsonl(output / "attack_view.jsonl")
            delta_provenance = read_jsonl(output / "request_provenance.jsonl")

            self.assertEqual(summary["requests"], 2)
            self.assertEqual(len(delta_attack[0]["messages"]), 3)
            self.assertEqual(len(delta_attack[1]["messages"]), 2)
            self.assertNotIn("view", delta_attack[0])
            self.assertNotIn("delta_from_message_index", delta_attack[0])
            self.assertEqual(delta_provenance[1]["delta_from_message_index"], 3)
            self.assertEqual(delta_provenance[1]["delta_to_message_index"], 5)


def _attack(request_id: str, roles: list[str]) -> dict:
    return {
        "request_id": request_id,
        "timestamp": f"2026-01-05T09:0{request_id[-1]}:00Z",
        "model": "test",
        "messages": [
            {"role": role, "content": f"{role} content {idx}"} for idx, role in enumerate(roles)
        ],
        "tool_schemas": [],
        "token_count": 1,
        "cache_bucket": None,
    }


def _truth(request_id: str, turn_id: int) -> dict:
    return {
        "request_id": request_id,
        "org_id": "org",
        "user_id": None,
        "project_id": "org/repo",
        "workflow_id": "workflow",
        "turn_id": turn_id,
        "task_type": "unit",
        "profile_truth": {},
    }


if __name__ == "__main__":
    unittest.main()
