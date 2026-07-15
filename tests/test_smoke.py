from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_privacy.attacks.pipeline import run_attacks
from agent_privacy.data.generator import generate_dataset
from agent_privacy.data.schemas import DatasetConfig
from agent_privacy.defenses.transforms import apply_defense
from agent_privacy.evaluation.clustering import evaluate_all
from agent_privacy.io import read_jsonl


class SmokeTest(unittest.TestCase):
    def test_generation_attack_and_metrics_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = DatasetConfig(
                seed=1,
                num_orgs=2,
                users_per_org=2,
                projects_per_org=2,
                workflows_per_user=2,
                turns_per_workflow=4,
                noise_rate=0.1,
            )
            generate_dataset(config, tmp_path)
            attack_rows = read_jsonl(tmp_path / "attack_view.jsonl")
            truth_rows = read_jsonl(tmp_path / "ground_truth.jsonl")

            defended = apply_defense(attack_rows, "M1", seed=1)
            predictions = run_attacks(defended)
            metrics = evaluate_all(predictions, truth_rows)

            self.assertTrue(attack_rows)
            self.assertEqual(len(defended), len(attack_rows))
            self.assertIn("hybrid", predictions)
            self.assertTrue(
                any(row["method"] == "hybrid" and row["level"] == "session" for row in metrics)
            )


if __name__ == "__main__":
    unittest.main()
