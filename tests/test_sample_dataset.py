from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_privacy.data.sample_dataset import sample_dataset_by_workflow
from agent_privacy.io import read_jsonl, write_jsonl


class SampleDatasetTest(unittest.TestCase):
    def test_reservoir_sample_by_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            attack_rows = []
            truth_rows = []
            for workflow_idx in range(5):
                for turn_id in range(1, 3):
                    request_id = f"req_{workflow_idx}_{turn_id}"
                    attack_rows.append(
                        {
                            "request_id": request_id,
                            "timestamp": "2026-01-01T00:00:00Z",
                            "messages": [{"role": "user", "content": request_id}],
                        }
                    )
                    truth_rows.append(
                        {
                            "request_id": request_id,
                            "workflow_id": f"workflow_{workflow_idx}",
                            "turn_id": turn_id,
                        }
                    )
            write_jsonl(source / "attack_view.jsonl", attack_rows)
            write_jsonl(source / "ground_truth.jsonl", truth_rows)

            output = root / "sampled"
            summary = sample_dataset_by_workflow(
                source,
                output,
                limit_workflows=3,
                sample_mode="reservoir",
                seed=2,
            )

            sampled_truth = read_jsonl(output / "ground_truth.jsonl")
            sampled_workflows = {row["workflow_id"] for row in sampled_truth}

            self.assertEqual(summary["sample_mode"], "reservoir")
            self.assertEqual(summary["source_workflows"], 5)
            self.assertEqual(summary["workflows"], 3)
            self.assertEqual(len(sampled_truth), 6)
            self.assertEqual(len(sampled_workflows), 3)


if __name__ == "__main__":
    unittest.main()
