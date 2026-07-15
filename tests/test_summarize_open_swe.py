from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_privacy.experiments.summarize_open_swe import OpenSWESweepCell, summarize_sample_size_sweep


class SummarizeOpenSWETest(unittest.TestCase):
    def test_summarize_sample_size_sweep_reads_manifest_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset_dir = root / "dataset"
            dataset_dir.mkdir()
            (dataset_dir / "source_manifest.json").write_text(
                json.dumps(
                    {
                        "sample_mode": "reservoir",
                        "source_rows_seen": 50,
                        "eligible_trajectories": 40,
                        "max_source_rows": 50,
                        "requests": 120,
                        "config": {"seed": 7},
                    }
                ),
                encoding="utf-8",
            )
            result_dirs = {}
            for name in ("raw", "no_workspace", "delta", "delta_no_workspace"):
                result_dir = root / name
                result_dir.mkdir()
                (result_dir / "clustering_metrics_all.csv").write_text(
                    "\n".join(
                        [
                            "method,level,pairwise_precision,pairwise_recall,pairwise_f1",
                            "hybrid,session,1.0,0.8,0.9",
                            "hybrid,project,1.0,0.6,0.75",
                            "hybrid,org,1.0,0.5,0.667",
                            "rare,project,1.0,0.4,0.571",
                            "temporal,session,0.2,0.2,0.2",
                            "tool,session,0.1,0.1,0.1",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
                result_dirs[name] = result_dir

            rows = summarize_sample_size_sweep(
                [
                    OpenSWESweepCell(
                        sample_label="test",
                        sample_size=10,
                        scaffold="openhands",
                        split="minimax_m25",
                        dataset_dir=str(dataset_dir),
                        cumulative_raw=str(result_dirs["raw"]),
                        cumulative_no_workspace=str(result_dirs["no_workspace"]),
                        turn_delta_raw=str(result_dirs["delta"]),
                        turn_delta_no_workspace=str(result_dirs["delta_no_workspace"]),
                    )
                ]
            )

            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["sample_mode"], "reservoir")
            self.assertEqual(rows[0]["source_rows_seen"], 50)
            self.assertEqual(rows[0]["eligible_trajectories"], 40)
            self.assertEqual(rows[0]["hybrid_session_f1"], 0.9)
            self.assertEqual(rows[0]["hybrid_project_f1"], 0.75)
            self.assertEqual(rows[0]["rare_project_f1"], 0.571)


if __name__ == "__main__":
    unittest.main()
